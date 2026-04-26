"""UI package: Gradio layouts and handlers (barrel re-exports)."""

from ui.cover_ui import build_cover_tab
from ui.extend_ui import build_extend_tab
from ui.generate_ui import build_generate_section
from ui.repaint_ui import build_repaint_tab

__all__ = [
    "build_cover_tab",
    "build_extend_tab",
    "build_generate_section",
    "build_repaint_tab",
]
