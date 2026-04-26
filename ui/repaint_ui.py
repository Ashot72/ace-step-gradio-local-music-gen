"""Repainting tab: layout and on_repaint handler."""

import gradio as gr

from ace_step_runner import generate_repaint, gradio_traceback_markdown
from ui.generate_ui import gr_update_interactive_if_title_and_audio


_REPAINT_END_TO_EOF = "To End of File"
_REPAINT_END_FIXED = "Fixed End (seconds)"


def on_repaint(
    repaint_song_title: str,
    src_audio,
    repainting_start: float,
    repaint_end_mode: str,
    repainting_end: float,
    caption: str,
    lyrics: str,
    instrumental: bool,
    cover_strength: float,
    progress=gr.Progress(track_tqdm=True),
):
    end = -1.0 if (repaint_end_mode or "").strip() == _REPAINT_END_TO_EOF else repainting_end
    try:
        path, msg = generate_repaint(
            song_title=(repaint_song_title or "").strip(),
            src_audio=(src_audio or "").strip(),
            repainting_start=repainting_start,
            repainting_end=end,
            caption=(caption or "").strip(),
            lyrics=lyrics or "",
            instrumental=bool(instrumental),
            audio_cover_strength=cover_strength,
            progress=progress,
        )
        if path is None:
            yield None, msg
        else:
            yield str(path), msg
    except Exception:
        yield None, gradio_traceback_markdown()


def build_repaint_tab() -> None:
    """Build `repainting` tab."""
    with gr.Tab("Repainting"):
        gr.Markdown(
            "**Repainting** redoes only the time range you set."
        )
        repaint_song_title = gr.Textbox(
            label="Song Title *",
            lines=1,
            placeholder="Name for this export (e.g. Without Me Repaint)",
            elem_id="repaint_song_title",
        )
        repaint_src = gr.Audio(
            label="Source audio *",
            type="filepath",
            sources=["upload"],
        )
        repaint_start_sec = gr.Slider(
            minimum=0,
            maximum=600,
            value=0,
            step=0.5,
            label="Repainting Start (seconds)",
        )
        with gr.Row(elem_classes=["tight-inline-row"]):
            repaint_end_mode = gr.Radio(
                choices=[_REPAINT_END_TO_EOF, _REPAINT_END_FIXED],
                value=_REPAINT_END_TO_EOF,
                label="Repainting End",
                scale=1,
            )
            repaint_end_sec = gr.Slider(
                minimum=0.5,
                maximum=600,
                value=30,
                step=0.5,
                label="End (seconds)",
                visible=False,
                scale=2,
            )

        def _toggle_repaint_end(mode: str):
            return gr.update(visible=(mode == _REPAINT_END_FIXED))

        repaint_end_mode.change(
            _toggle_repaint_end,
            inputs=[repaint_end_mode],
            outputs=[repaint_end_sec],
        )
        repaint_caption = gr.Textbox(
            label="Caption",
            lines=2,
            placeholder="Describe the replacement — leave empty for model default",
        )
        repaint_lyrics = gr.Textbox(
            label="Lyrics",
            lines=6,
            placeholder="Optional: words / structure for the repainted region; leave empty for caption-only.",
        )
        repaint_instrumental = gr.Checkbox(label="Instrumental", value=False)
        repaint_cover_strength = gr.Slider(
            minimum=0.0,
            maximum=1.0,
            value=0.7,
            step=0.01,
            label="Cover Strength",
        )
        repaint_btn = gr.Button("Repaint", variant="primary", interactive=False)

        _repaint_ready_inputs = [repaint_song_title, repaint_src]
        repaint_song_title.change(
            gr_update_interactive_if_title_and_audio, inputs=_repaint_ready_inputs, outputs=[repaint_btn]
        )
        repaint_src.change(
            gr_update_interactive_if_title_and_audio, inputs=_repaint_ready_inputs, outputs=[repaint_btn]
        )
        repaint_audio = gr.Audio(
            label="Repainting generated audio",
            type="filepath",
            interactive=False,
            elem_id="repaint_audio",
        )
        repaint_status = gr.Markdown()

        repaint_btn.click(
            on_repaint,
            inputs=[
                repaint_song_title,
                repaint_src,
                repaint_start_sec,
                repaint_end_mode,
                repaint_end_sec,
                repaint_caption,
                repaint_lyrics,
                repaint_instrumental,
                repaint_cover_strength,
            ],
            outputs=[repaint_audio, repaint_status],
            show_progress="minimal",
            show_progress_on=repaint_audio,
        )
