import argparse
import traceback

import gradio as gr

from ace_step_runner import PROJECT_ROOT, generate_track


def _reference_audio_path(value) -> str | None:
    """Resolve Gradio Audio (filepath) to a non-empty path string if present."""
    if value is None:
        return None
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, dict) and value.get("path"):
        p = str(value["path"]).strip()
        return p or None
    return None


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
    progress=gr.Progress(track_tqdm=True),
):
    if not (song_title or "").strip():
        yield None, "Enter **Song title**."
        return
    if not (tags or "").strip():
        yield None, "Enter **Tags** (song description)."
        return

    ref = _reference_audio_path(reference_audio) if audio2audio else None
    if audio2audio and not ref:
        yield None, "Enable **Audio2Audio**: upload or record **Reference audio**."
        return

    try:
        d = -1.0 if duration_mode == "Auto" else duration_sec

        path, msg = generate_track(
            song_title=(song_title or "").strip(),
            caption=tags,
            lyrics=lyrics or "",
            duration_sec=d,
            instrumental=instrumental,
            reference_audio=ref,
            audio_cover_strength=refer_audio_strength if ref else 1.0,
            progress=progress,
        )
        if path is None:
            yield None, msg
        else:
            yield str(path), msg
    except Exception:
        yield None, f"```\n{traceback.format_exc()}\n```"


def build_ui():
    with gr.Blocks(title="Music Generator") as demo:
        gr.Markdown("## Music Generation", elem_id="app_title")
        with gr.Row():
            song_title = gr.Textbox(
                label="Song Title",
                placeholder="My track",
                lines=1,
                elem_id="song_title",
            )
        audio2audio = gr.Checkbox(label="Enable Audio2Audio", value=False)
        with gr.Group(visible=False) as audio2audio_group:
            reference_audio = gr.Audio(
                label="Reference audio (for Audio2Audio)",
                type="filepath",
                sources=["upload", "microphone"],
                elem_id="reference_audio",
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
            """Hide section when off; clear reference + reset strength so UI matches plain text2music."""
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

        def _generate_enabled(song_title_val: str, tags_val: str):
            ok = bool((song_title_val or "").strip()) and bool((tags_val or "").strip())
            return gr.update(interactive=ok)

        with gr.Row():
            go = gr.Button("Generate", variant="primary", interactive=False)
        out_audio = gr.Audio(
            label="Output",
            type="filepath",
            interactive=False,
            elem_id="out_audio",
        )
        status = gr.Markdown(elem_id="status_line", padding=False, container=False)

        song_title.change(_generate_enabled, inputs=[song_title, tags], outputs=[go])
        tags.change(_generate_enabled, inputs=[song_title, tags], outputs=[go])
        demo.load(_generate_enabled, inputs=[song_title, tags], outputs=[go])

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
            ],
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
