"""Main Music Generation section: text2music / Audio2Audio layout and on_generate handler."""

import gradio as gr

from ace_step_runner import generate_track, gradio_traceback_markdown

# Shared with extend tab (duration mode).
DURATION_AUTO = "Auto"
DURATION_FIXED = "Fixed Length (seconds)"
_GEN_SEED_RANDOM = "random"
_GEN_SEED_FIXED = "fixed"


def gr_update_interactive_if_title_and_audio(song_title: str, src_audio):
    """Enable primary action when a non-empty title and source audio are present."""
    ok = bool((song_title or "").strip()) and src_audio is not None
    return gr.update(interactive=ok)


def on_generate(
    song_title: str,
    audio2audio: bool,
    reference_audio,
    refer_audio_strength: float,
    tags: str,
    duration_mode: str,
    duration_sec: float,
    lyrics: str,
    instrumental: bool,
    seed_mode: str,
    seed_value: float | int | None,
    progress=gr.Progress(track_tqdm=True),
):
    ref = (reference_audio or "").strip() if audio2audio else None
    if audio2audio and not ref:
        yield None, ""
        return

    try:
        d = -1.0 if duration_mode == DURATION_AUTO else duration_sec

        seed: int | None = None
        if (seed_mode or "").strip() == _GEN_SEED_FIXED:
            if seed_value is None:
                yield None, "Enter a **Seed value** when using fixed seed."
                return
            seed = int(seed_value)

        path, msg = generate_track(
            song_title=(song_title or "").strip(),
            caption=(tags or "").strip(),
            lyrics=lyrics or "",
            duration_sec=d,
            instrumental=instrumental,
            reference_audio=ref,
            audio_cover_strength=refer_audio_strength if ref else 1.0,
            seed=seed,
            progress=progress,
        )
        if path is None:
            yield None, msg
        else:
            p = str(path)
            yield p, msg
    except Exception:
        yield None, gradio_traceback_markdown()


def build_generate_section(
    demo: gr.Blocks,
) -> None:
    """Build main generate tab; pass parent Blocks from `app.build_ui`."""
    gr.Markdown("## Generate Music", elem_id="app_title")
    with gr.Row():
        song_title = gr.Textbox(
            label="Song Title *",
            placeholder="My track",
            lines=1,
            elem_id="song_title",
        )
    audio2audio = gr.Checkbox(
        label="Enable Audio2Audio",
        value=False,
    )
    with gr.Group(visible=False) as audio2audio_group:
        reference_audio = gr.Audio(
            label="Reference audio",
            type="filepath",
            sources=["upload"],
            elem_id="reference_audio",
            elem_classes=["req-field"],
        )
        refer_audio_strength = gr.Slider(
            minimum=0.0,
            maximum=1.0,
            value=0.5,
            step=0.01,
            label="Refer audio strength",
            info="Higher = closer to the reference clip; lower = follow tags/lyrics more.",
        )

    def _toggle_a2a(enabled: bool):
        if enabled:
            return gr.update(visible=True), gr.update(), gr.update()
        return (
            gr.update(visible=False),
            gr.update(value=None),
            gr.update(value=0.5),
        )

    audio2audio.change(
        _toggle_a2a,
        inputs=[audio2audio],
        outputs=[audio2audio_group, reference_audio, refer_audio_strength],
    )

    tags = gr.Textbox(
        label="Tags *",
        lines=3,
        placeholder="Genre, mood, instruments, vibe…",
        elem_id="tags",
    )
    with gr.Row(elem_classes=["tight-inline-row"]):
        duration_mode = gr.Radio(
            choices=[DURATION_AUTO, DURATION_FIXED],
            value=DURATION_AUTO,
            label="Duration",
            scale=1,
        )
        duration_sec = gr.Slider(
            minimum=10,
            maximum=240,
            value=60,
            step=1,
            label="Seconds",
            visible=False,
            scale=2,
        )

    def _toggle_dur(mode: str):
        return gr.update(visible=(mode == DURATION_FIXED))

    duration_mode.change(_toggle_dur, inputs=[duration_mode], outputs=[duration_sec])

    lyrics = gr.Textbox(
        label="Lyrics",
        lines=6,
        placeholder="Leave empty for vibe-only or use with instrumental off.",
    )
    instrumental = gr.Checkbox(label="Instrumental", value=False)
    with gr.Row(elem_classes=["tight-inline-row"]):
        seed_mode = gr.Radio(
            choices=[
                ("Random", _GEN_SEED_RANDOM),
                ("Fixed Seed", _GEN_SEED_FIXED),
            ],
            value=_GEN_SEED_RANDOM,
            label="Seed",
            scale=1,
        )
        seed_value = gr.Slider(
            minimum=0,
            maximum=1_000_000,
            value=42,
            step=1,
            precision=0,
            label="Seed value",
            visible=False,
            scale=2,
        )

    def _toggle_gen_seed(mode: str):
        return gr.update(visible=(mode == _GEN_SEED_FIXED))

    seed_mode.change(_toggle_gen_seed, inputs=[seed_mode], outputs=[seed_value])

    with gr.Row():
        go = gr.Button("Generate", variant="primary", interactive=False)
    out_audio = gr.Audio(
        label="Output",
        type="filepath",
        interactive=False,
        elem_id="out_audio",
    )
    status = gr.Markdown(elem_id="status_line", padding=False, container=False)

    def _main_generate_enabled(
        song_title_val: str, tags_val: str, audio2audio_val: bool, reference_audio_val
    ):
        ok = bool((song_title_val or "").strip()) and bool((tags_val or "").strip())
        if audio2audio_val:
            ok = ok and bool((reference_audio_val or "").strip())
        return gr.update(interactive=ok)

    _gen_ready_inputs = [song_title, tags, audio2audio, reference_audio]
    song_title.change(_main_generate_enabled, inputs=_gen_ready_inputs, outputs=[go])
    tags.change(_main_generate_enabled, inputs=_gen_ready_inputs, outputs=[go])
    audio2audio.change(_main_generate_enabled, inputs=_gen_ready_inputs, outputs=[go])
    reference_audio.change(_main_generate_enabled, inputs=_gen_ready_inputs, outputs=[go])
    demo.load(_main_generate_enabled, inputs=_gen_ready_inputs, outputs=[go])

    go.click(
        on_generate,
        inputs=[
            song_title,
            audio2audio,
            reference_audio,
            refer_audio_strength,
            tags,
            duration_mode,
            duration_sec,
            lyrics,
            instrumental,
            seed_mode,
            seed_value,
        ],
        outputs=[out_audio, status],
        show_progress="minimal",
        show_progress_on=out_audio,
    )
