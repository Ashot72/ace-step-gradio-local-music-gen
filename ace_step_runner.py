"""ACE-Step 1.5 inference for the minimal Gradio UI (Intel XPU)."""

from __future__ import annotations

import logging
import re
import shutil
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from acestep.inference import GenerationConfig, GenerationParams, generate_music

PROJECT_ROOT = Path(__file__).resolve().parent


def gradio_traceback_markdown() -> str:
    """Markdown code block with current exception traceback (for Gradio status)."""
    return f"```\n{traceback.format_exc()}\n```"

# Pipeline defaults
_PIPELINE_DEFAULTS: dict[str, str] = {
    "ACESTEP_CONFIG_PATH": "acestep-v15-turbo",
    "ACESTEP_LM_MODEL_PATH": "acestep-5Hz-lm-1.7B",
    "ACESTEP_DEVICE": "xpu",
    "ACESTEP_LM_BACKEND": "pt",
    "ACESTEP_OFFLOAD_TO_CPU": "true",
    "ACESTEP_COMPILE_MODEL": "false",
    "ACESTEP_OFFLOAD_DIT_TO_CPU": "false",
    "ACESTEP_AUDIO_FORMAT": "wav",
    "ACESTEP_MP3_BITRATE": "192k",
    "ACESTEP_QUANTIZATION": "",
    "ACESTEP_VOCAL_LANGUAGE": "unknown",
    "ACESTEP_DOWNLOAD_SOURCE": "",
}

_dit_handler: Any = None
_llm_handler: Any = None

_log = logging.getLogger(__name__)


def _cfg(name: str) -> str:
    return _PIPELINE_DEFAULTS[name]


def _cfg_bool(name: str) -> bool:
    return _PIPELINE_DEFAULTS[name].lower() == "true"


def _safe_filename(name: str, fallback: str = "track") -> str:
    name = (name or "").strip() or fallback
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    return name[:120] if len(name) > 120 else name


def _wav_to_mp3(wav: Path, bitrate: str) -> Optional[Path]:
    import static_ffmpeg
    from pydub import AudioSegment

    static_ffmpeg.add_paths()
    mp3 = wav.with_suffix(".mp3")
    try:
        AudioSegment.from_file(str(wav)).export(str(mp3), format="mp3", bitrate=bitrate)
    except Exception:
        return None
    try:
        wav.unlink(missing_ok=True)
    except OSError:
        pass
    return mp3


def _text2music_lyrics_and_flags(lyrics: str, instrumental: bool) -> tuple[str, str, bool]:
    """(lyrics_for_params, vocal_language, instrumental_flag) for text2music / complete."""
    if instrumental:
        return "[Instrumental]", "unknown", True
    return (lyrics or "").strip(), _cfg("ACESTEP_VOCAL_LANGUAGE"), False


def _generation_config(
    *,
    use_random_seed: bool,
    seeds: Optional[list[int]] = None,
) -> GenerationConfig:
    return GenerationConfig(
        batch_size=1,
        use_random_seed=use_random_seed,
        seeds=seeds,
        audio_format=_cfg("ACESTEP_AUDIO_FORMAT"),
    )


def _require_source_audio_path(src_audio: str) -> Path:
    p = Path(src_audio)
    if not p.is_file():
        raise ValueError("Source audio file is required.")
    return p


def load_pipeline() -> None:
    """Initialize DiT + 5Hz LM once (matches upstream acestep_v15_pipeline init_service path)."""
    global _dit_handler, _llm_handler

    if _dit_handler is not None:
        return

    try:
        from acestep.handler import AceStepHandler
        from acestep.llm_inference import LLMHandler
        from acestep.model_downloader import ensure_lm_model, get_checkpoints_dir, get_project_root

        ace_root = get_project_root()
        checkpoint_dir = get_checkpoints_dir()

        config_path = _cfg("ACESTEP_CONFIG_PATH")
        lm_model_path = _cfg("ACESTEP_LM_MODEL_PATH")
        device = _cfg("ACESTEP_DEVICE")
        backend = _cfg("ACESTEP_LM_BACKEND")
        offload_to_cpu = _cfg_bool("ACESTEP_OFFLOAD_TO_CPU")
        compile_model = _cfg_bool("ACESTEP_COMPILE_MODEL")

        dit_handler = AceStepHandler()
        llm_handler = LLMHandler()

        use_flash = dit_handler.is_flash_attention_available(device)
        prefer_source = _cfg("ACESTEP_DOWNLOAD_SOURCE") or None
        if prefer_source == "auto":
            prefer_source = None

        init_status, ok = dit_handler.initialize_service(
            project_root=str(ace_root),
            config_path=config_path,
            device=device,
            use_flash_attention=use_flash,
            compile_model=compile_model,
            offload_to_cpu=offload_to_cpu,
            offload_dit_to_cpu=_cfg_bool("ACESTEP_OFFLOAD_DIT_TO_CPU"),
            quantization=_cfg("ACESTEP_QUANTIZATION") or None,
            prefer_source=prefer_source,
        )
        if not ok:
            raise RuntimeError(f"DiT init failed: {init_status}")

        dl_ok, dl_msg = ensure_lm_model(
            model_name=lm_model_path,
            checkpoints_dir=checkpoint_dir,
            prefer_source=prefer_source,
        )
        if not dl_ok:
            raise RuntimeError(f"LM model download failed: {dl_msg}")

        lm_status, lm_ok = llm_handler.initialize(
            checkpoint_dir=str(checkpoint_dir),
            lm_model_path=lm_model_path,
            backend=backend,
            device=device,
            offload_to_cpu=offload_to_cpu,
            dtype=None,
        )
        if not lm_ok:
            raise RuntimeError(f"LM init failed: {lm_status}")

        _dit_handler = dit_handler
        _llm_handler = llm_handler
    except Exception:
        _dit_handler = None
        _llm_handler = None
        raise


def _run_generation(
    *,
    params: GenerationParams,
    config: GenerationConfig,
    filename_prefix: str,
    progress=None,
) -> tuple[Optional[Path], str]:
    """Shared path: generate_music, rename output, return (path, markdown status)."""
    load_pipeline()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_dir = PROJECT_ROOT / "output"
    save_dir.mkdir(parents=True, exist_ok=True)

    result = generate_music(
        _dit_handler,
        _llm_handler,
        params=params,
        config=config,
        save_dir=str(save_dir),
        progress=progress,
    )

    if not result.success or not result.audios:
        err = result.error or result.status_message or "Generation failed."
        return None, f"```\n{err}\n```"

    raw_path = result.audios[0].get("path") or ""
    raw = Path(raw_path)
    if not raw_path or not raw.is_file():
        return None, "```\nNo audio file was written.\n```"

    base = _safe_filename(filename_prefix, fallback=f"track_{stamp}")
    dest = save_dir / f"{base}_{stamp}{raw.suffix}"
    try:
        shutil.copy2(raw, dest)
        raw.unlink(missing_ok=True)
    except OSError:
        dest = raw

    out = dest
    if dest.is_file():
        mp3 = _wav_to_mp3(dest, _cfg("ACESTEP_MP3_BITRATE"))
        if mp3 is not None:
            out = mp3

    return out, result.status_message or "Done."


def generate_track(
    *,
    song_title: str,
    caption: str,
    lyrics: str,
    duration_sec: float,
    instrumental: bool,
    reference_audio: Optional[str] = None,
    audio_cover_strength: float = 1.0,
    seed: Optional[int] = None,
    progress=None,
) -> tuple[Optional[Path], str]:
    """
    Returns (path_to_first_audio_file_or_none, status_markdown).

    Uses acestep.inference.generate_music with GenerationParams defaults for advanced knobs.
    ``seed=None`` uses random seed; otherwise fixed RNG.
    """
    lyrics_final, vocal_language, inst_flag = _text2music_lyrics_and_flags(lyrics, instrumental)

    dur = duration_sec if duration_sec > 0 else -1.0

    ref_path: Optional[str] = None
    if reference_audio:
        p = Path(reference_audio)
        if p.is_file():
            ref_path = str(p)

    params = GenerationParams(
        task_type="text2music",
        caption=caption,
        lyrics=lyrics_final,
        instrumental=inst_flag,
        vocal_language=vocal_language,
        duration=dur,
        reference_audio=ref_path,
        audio_cover_strength=audio_cover_strength if ref_path else 1.0,
    )

    if seed is not None:
        use_random = False
        seed_list = [int(seed)]
    else:
        use_random = True
        seed_list = None
    config = _generation_config(use_random_seed=use_random, seeds=seed_list)

    return _run_generation(
        params=params,
        config=config,
        filename_prefix=song_title,
        progress=progress,
    )


def generate_repaint(
    *,
    song_title: str,
    src_audio: str,
    repainting_start: float,
    repainting_end: float,
    caption: str,
    lyrics: str = "",
    instrumental: bool = False,
    audio_cover_strength: float = 1.0,
    progress=None,
) -> tuple[Optional[Path], str]:
    lyrics_final, vocal_language, inst_flag = _text2music_lyrics_and_flags(lyrics, instrumental)

    p = _require_source_audio_path(src_audio)

    if repainting_end >= 0.0 and repainting_end <= repainting_start:
        raise ValueError("Repainting end must be greater than start (or use -1 for end of file).")

    params = GenerationParams(
        task_type="repaint",
        src_audio=str(p),
        repainting_start=repainting_start,
        repainting_end=repainting_end,
        caption=caption,
        lyrics=lyrics_final,
        instrumental=inst_flag,
        vocal_language=vocal_language,
        audio_cover_strength=audio_cover_strength,
    )

    _log.info(
        "[music-gen repaint] lyrics_final=%r | vocal_language=%r instrumental=%s | caption=%r | "
        "repainting [%.2fs, %.2fs] audio_cover_strength=%s | params (subset): %s",
        lyrics_final,
        vocal_language,
        inst_flag,
        (caption or "").strip()[:200],
        repainting_start,
        repainting_end,
        audio_cover_strength,
        {
            "task_type": params.task_type,
            "lyrics": params.lyrics,
            "caption": (params.caption or "")[:200] if params.caption else params.caption,
            "instrumental": params.instrumental,
            "vocal_language": params.vocal_language,
            "repainting_start": params.repainting_start,
            "repainting_end": params.repainting_end,
            "audio_cover_strength": params.audio_cover_strength,
        },
    )

    config = _generation_config(use_random_seed=True)

    return _run_generation(
        params=params,
        config=config,
        filename_prefix=f"{song_title}_repaint",
        progress=progress,
    )


def generate_cover_edit(
    *,
    song_title: str,
    src_audio: str,
    caption: str,
    lyrics: str = "",
    instrumental: bool = False,
    audio_cover_strength: float,
    progress=None,
) -> tuple[Optional[Path], str]:
    lyrics_final, vocal_language, inst_flag = _text2music_lyrics_and_flags(lyrics, instrumental)

    p = _require_source_audio_path(src_audio)

    params = GenerationParams(
        task_type="cover",
        src_audio=str(p),
        caption=caption,
        lyrics=lyrics_final,
        instrumental=inst_flag,
        vocal_language=vocal_language,
        audio_cover_strength=audio_cover_strength,
    )

    config = _generation_config(use_random_seed=True)

    return _run_generation(
        params=params,
        config=config,
        filename_prefix=f"{song_title}_cover",
        progress=progress,
    )


def generate_extend_complete(
    *,
    song_title: str,
    src_audio: str,
    lyrics: str,
    instrumental: bool,
    caption: str,
    duration_sec: float,
    progress=None,
) -> tuple[Optional[Path], str]:
    lyrics_final, vocal_language, inst_flag = _text2music_lyrics_and_flags(lyrics, instrumental)

    p = _require_source_audio_path(src_audio)

    dur = duration_sec if duration_sec > 0 else -1.0

    params = GenerationParams(
        task_type="complete",
        src_audio=str(p),
        caption=caption,
        lyrics=lyrics_final,
        instrumental=inst_flag,
        vocal_language=vocal_language,
        duration=dur,
    )

    config = _generation_config(use_random_seed=True)

    return _run_generation(
        params=params,
        config=config,
        filename_prefix=f"{song_title}_extend",
        progress=progress,
    )

