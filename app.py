import argparse

import gradio as gr

from ace_step_runner import PROJECT_ROOT
from ui import (
    build_cover_tab,
    build_extend_tab,
    build_generate_section,
    build_repaint_tab,
)


def build_ui():
    with gr.Blocks(title="Music Generator") as demo:
        last_output_path = gr.State(value=None)

        with gr.Tabs(elem_id="main_tabs"):
            with gr.Tab("Generate Music"):
                build_generate_section(last_output_path, demo)
            with gr.Tab("Refine Output"):
                gr.Markdown("## Refine Output", elem_id="refine_heading")
                with gr.Tabs(elem_id="refine_tabs"):
                    build_repaint_tab()
                    build_cover_tab()
                    build_extend_tab()

    return demo


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

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
        ssr_mode=False,
        max_file_size="1gb",
        footer_links=[],
        css_paths=PROJECT_ROOT / "app.css",
    )
