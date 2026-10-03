"""Рендеринг уложенных страниц: .drawio (mxfile) и SVG-предпросмотр."""

from .drawio import build_mxfile
from .preview import build_previews

__all__ = ["build_mxfile", "build_previews"]
