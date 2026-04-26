"""Edit (cover) tab: layout and on_cover handler."""

import gradio as gr

from ace_step_runner import generate_cover_edit, gradio_traceback_markdown
from ui.generate_ui import gr_update_interactive_if_title_and_audio


def on_cover(
    cover_song_title: str,
    src_audio,
    caption: str,
    lyrics: str,
    instrumental: bool,
    strength: float,
    progress=gr.Progress(track_tqdm=True),
):
    try:
        path, msg = generate_cover_edit(
            song_title=(cover_song_title or "").strip(),
            src_audio=(src_audio or "").strip(),
            caption=(caption or "").strip(),
            lyrics=lyrics or "",
            instrumental=bool(instrumental),
            audio_cover_strength=strength,
            progress=progress,
        )
        if path is None:
            yield None, msg
        else:
            yield str(path), msg
    except Exception:
        yield None, gradio_traceback_markdown()


def build_cover_tab() -> None:
    """Build `edit` tab."""
    with gr.Tab("Edit"):
        gr.Markdown(
            "**Edit (cover)** remakes an **uploaded** track using your caption and optional lyrics."
        )
        cover_song_title = gr.Textbox(
            label="Song Title *",
            lines=1,
            placeholder="Name for this export (e.g. Without Me Cover)",
            elem_id="cover_song_title",
        )
        cover_src = gr.Audio(
            label="Source audio *",
            type="filepath",
            sources=["upload"],
        )
        cover_caption = gr.Textbox(
            label="Caption",
            lines=2,
            placeholder="Style / arrangement — leave empty for model default",
        )
        cover_lyrics = gr.Textbox(
            label="Lyrics",
            lines=6,
            placeholder="Optional: new or same words; leave empty for caption-only.",
        )
        cover_instrumental = gr.Checkbox(label="Instrumental", value=False)
        cover_strength = gr.Slider(
            minimum=0.0,
            maximum=1.0,
            value=0.7,
            step=0.01,
            label="Cover Strength",
        )
        cover_btn = gr.Button("Edit (Cover)", variant="primary", interactive=False)

        _cover_ready_inputs = [cover_song_title, cover_src]
        cover_song_title.change(
            gr_update_interactive_if_title_and_audio, inputs=_cover_ready_inputs, outputs=[cover_btn]
        )
        cover_src.change(
            gr_update_interactive_if_title_and_audio, inputs=_cover_ready_inputs, outputs=[cover_btn]
        )
        cover_audio = gr.Audio(
            label="Edit generated audio",
            type="filepath",
            interactive=False,
            elem_id="cover_audio",
        )
        cover_status = gr.Markdown()

        cover_btn.click(
            on_cover,
            inputs=[
                cover_song_title,
                cover_src,
                cover_caption,
                cover_lyrics,
                cover_instrumental,
                cover_strength,
            ],
            outputs=[cover_audio, cover_status],
            show_progress="minimal",
            show_progress_on=cover_audio,
        )
