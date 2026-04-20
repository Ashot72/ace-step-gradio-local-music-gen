"""Verify Intel XPU PyTorch (used by setup.bat)."""

from __future__ import annotations

import sys


def main() -> int:
    import torch

    print("torch", torch.__version__)
    if not hasattr(torch, "xpu") or not torch.xpu.is_available():
        print("XPU not available", file=sys.stderr)
        return 1
    print("torch.xpu.is_available():", torch.xpu.is_available())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
