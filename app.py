import argparse
import traceback

import gradio as gr

from ace_step_runner import PROJECT_ROOT, generate_track


def on_generate(
    song_title: str,
    tags: str,
    duration_mode: str,
    duration_sec: float,
    lyrics: str,
    instrumental: bool,
    progress=gr.Progress(track_tqdm=True),
):
    if not (tags or "").strip():
        yield None, "Enter **Tags** (song description)."
        return

    try:
        d = -1.0 if duration_mode == "Auto" else duration_sec

        path, msg = generate_track(
            song_title=song_title or "untitled",
            caption=tags,
            lyrics=lyrics or "",
            duration_sec=d,
            instrumental=instrumental,
            progress=progress,
        )
        if path is None:
            yield None, msg
        else:
            yield str(path), msg
    except Exception:
        yield None, f"```\n{traceback.format_exc()}\n```"


def build_ui():
    with gr.Blocks(title="ACE-Step — simple generator") as demo:
        gr.Markdown("## Music Generation", elem_id="app_title")
        with gr.Row():
            song_title = gr.Textbox(
                label="Song Title",
                placeholder="My track",
                lines=1,
                elem_id="song_title",
            )
        tags = gr.Textbox(
            label="Tags",
            lines=3,
            placeholder="Genre, mood, instruments, vibe…",
            elem_id="tags",
        )
        with gr.Row():
            duration_mode = gr.Radio(
                choices=["Auto", "Fixed length (seconds)"],
                value="Auto",
                label="Duration",
            )
            duration_sec = gr.Slider(
                minimum=10,
                maximum=240,
                value=60,
                step=1,
                label="Seconds",
                visible=False,
            )

        def _toggle_dur(mode: str):
            return gr.update(visible=(mode == "Fixed length (seconds)"))

        duration_mode.change(_toggle_dur, inputs=[duration_mode], outputs=[duration_sec])

        lyrics = gr.Textbox(
            label="Lyrics (optional)",
            lines=6,
            placeholder="Leave empty for vibe-only or use with instrumental off.",
        )
        instrumental = gr.Checkbox(label="Instrumental", value=False)

        with gr.Row():
            go = gr.Button("Generate", variant="primary")
        out_audio = gr.Audio(
            label="Output",
            type="filepath",
            interactive=False,
            elem_id="out_audio",
        )
        status = gr.Markdown(elem_id="status_line", padding=False, container=False)

        go.click(
            on_generate,
            inputs=[song_title, tags, duration_mode, duration_sec, lyrics, instrumental],
            outputs=[out_audio, status],
            show_progress="minimal",
            show_progress_on=out_audio,
        )
    return demo


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Minimal ACE-Step 1.5 Gradio UI (XPU).")
    parser.add_argument("--server-name", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--share", action="store_true")
    args = parser.parse_args()

    demo = build_ui()
    demo.launch(
        server_name=args.server_name,
        server_port=args.port,
        share=args.share,
        # [] is ignored by Gradio (empty list is falsy → default footer); hidden in app.css
        footer_links=[],
        css_paths=PROJECT_ROOT / "app.css",
    )
