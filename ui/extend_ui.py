"""Extend (complete) tab: layout, enable logic, and on_extend handler."""

import gradio as gr

from ace_step_runner import generate_extend_complete, gradio_traceback_markdown
from ui.generate_ui import (
    DURATION_AUTO,
    DURATION_FIXED,
    gr_update_interactive_if_title_and_audio,
)


def on_extend(
    extend_song_title: str,
    src_audio,
    lyrics: str,
    instrumental: bool,
    caption: str,
    extend_duration_mode: str,
    extend_duration_sec: float,
    progress=gr.Progress(track_tqdm=True),
):
    try:
        d = -1.0 if extend_duration_mode == DURATION_AUTO else extend_duration_sec
        path, msg = generate_extend_complete(
            song_title=(extend_song_title or "").strip(),
            src_audio=(src_audio or "").strip(),
            lyrics=lyrics or "",
            instrumental=instrumental,
            caption=(caption or "").strip(),
            duration_sec=d,
            progress=progress,
        )
        if path is None:
            yield None, msg
        else:
            yield str(path), msg
    except Exception:
        yield None, gradio_traceback_markdown()


def build_extend_tab() -> None:
    """Build `extend` tab."""
    with gr.Tab("Extend"):
        gr.Markdown(
            "**Extend** continues or completes an **uploaded** clip with your lyrics and settings."
        )
        extend_song_title = gr.Textbox(
            label="Song Title *",
            lines=1,
            placeholder="Name for this export (e.g. Without Me Extension)",
            elem_id="extend_song_title",
        )
        extend_src = gr.Audio(
            label="Source audio *",
            type="filepath",
            sources=["upload"],
        )
        with gr.Row(elem_classes=["tight-inline-row"]):
            extend_duration_mode = gr.Radio(
                choices=[DURATION_AUTO, DURATION_FIXED],
                value=DURATION_AUTO,
                label="Duration",
                scale=1,
            )
            extend_duration_sec = gr.Slider(
                minimum=10,
                maximum=240,
                value=60,
                step=1,
                label="Seconds",
                visible=False,
                scale=2,
            )

        def _toggle_extend_dur(mode: str):
            return gr.update(visible=(mode == DURATION_FIXED))

        extend_duration_mode.change(
            _toggle_extend_dur,
            inputs=[extend_duration_mode],
            outputs=[extend_duration_sec],
        )
        extend_caption = gr.Textbox(
            label="Caption",
            lines=2,
            placeholder="Style hints — leave empty for model default",
        )
        extend_lyrics = gr.Textbox(
            label="Lyrics",
            lines=6,
            placeholder="Leave empty for vibe-only or use with instrumental off.",
        )
        extend_instrumental = gr.Checkbox(label="Instrumental", value=False)
        extend_btn = gr.Button("Extend", variant="primary", interactive=False)

        _extend_ready_inputs = [extend_song_title, extend_src]
        extend_song_title.change(
            gr_update_interactive_if_title_and_audio, inputs=_extend_ready_inputs, outputs=[extend_btn]
        )
        extend_src.change(
            gr_update_interactive_if_title_and_audio, inputs=_extend_ready_inputs, outputs=[extend_btn]
        )
        extend_audio = gr.Audio(
            label="Extend generated audio",
            type="filepath",
            interactive=False,
            elem_id="extend_audio",
        )
        extend_status = gr.Markdown()

        extend_btn.click(
            on_extend,
            inputs=[
                extend_song_title,
                extend_src,
                extend_lyrics,
                extend_instrumental,
                extend_caption,
                extend_duration_mode,
                extend_duration_sec,
            ],
            outputs=[extend_audio, extend_status],
            show_progress="minimal",
            show_progress_on=extend_audio,
        )
