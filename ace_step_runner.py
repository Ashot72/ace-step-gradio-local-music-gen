"""Lazy-loaded ACE-Step 1.5 inference for the minimal Gradio UI (Intel XPU)."""

import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent

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
    "ACESTEP_QUANTIZATION": "",
    "ACESTEP_VOCAL_LANGUAGE": "unknown",
    "ACESTEP_DOWNLOAD_SOURCE": "",
}

_dit_handler: Any = None
_llm_handler: Any = None


def _cfg(name: str) -> str:
    return _PIPELINE_DEFAULTS[name]


def _cfg_bool(name: str) -> bool:
    return _PIPELINE_DEFAULTS[name].strip().lower() == "true"


def _safe_filename(name: str, fallback: str = "track") -> str:
    name = (name or "").strip() or fallback
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    return name[:120] if len(name) > 120 else name


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
        prefer_source = _cfg("ACESTEP_DOWNLOAD_SOURCE").strip() or None
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
            quantization=_cfg("ACESTEP_QUANTIZATION").strip() or None,
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


def generate_track(
    *,
    song_title: str,
    caption: str,
    lyrics: str,
    duration_sec: float,
    instrumental: bool,
    reference_audio: Optional[str] = None,
    audio_cover_strength: float = 1.0,
    progress=None,
) -> tuple[Optional[Path], str]:
    """
    Returns (path_to_first_audio_file_or_none, status_markdown).

    Uses acestep.inference.generate_music with GenerationParams defaults for advanced knobs.
    """
    from acestep.inference import GenerationConfig, GenerationParams, generate_music

    load_pipeline()
    caption = (caption or "").strip()
    if not caption:
        raise ValueError("Prompt (caption) is required.")

    lyrics_in = (lyrics or "").strip()
    if instrumental:
        lyrics_final = "[Instrumental]"
        vocal_language = "unknown"
        inst_flag = True
    else:
        lyrics_final = lyrics_in
        vocal_language = _cfg("ACESTEP_VOCAL_LANGUAGE")
        inst_flag = False

    dur = duration_sec if duration_sec > 0 else -1.0

    ref_path: Optional[str] = None
    if reference_audio:
        p = Path(reference_audio.strip())
        if p.is_file():
            ref_path = str(p)

    strength = float(audio_cover_strength) if ref_path else 1.0

    params = GenerationParams(
        task_type="text2music",
        caption=caption,
        lyrics=lyrics_final,
        instrumental=inst_flag,
        vocal_language=vocal_language,
        duration=dur,
        reference_audio=ref_path,
        audio_cover_strength=strength,
    )

    config = GenerationConfig(
        batch_size=1,
        use_random_seed=True,
        audio_format=_cfg("ACESTEP_AUDIO_FORMAT"),
    )

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

    base = _safe_filename(song_title, fallback=f"track_{stamp}")
    ext = raw.suffix or ".wav"
    # Upstream writes a UUID filename; keep one file: {title}_{timestamp}.wav and delete the UUID file.
    dest = save_dir / f"{base}_{stamp}{ext}"
    try:
        shutil.copy2(raw, dest)
        raw.unlink(missing_ok=True)
    except OSError:
        dest = raw

    return dest, result.status_message or "Done."


if __name__ == "__main__":
    # CLI warmup: venv active; optional upstream XPU env (see ACE-Step start_gradio_ui_xpu.bat).
    load_pipeline()
    print("Pipeline ready.")
