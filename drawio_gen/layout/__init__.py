"""Укладка IR в геометрию: модели, измерение и маршрутизация рёбер."""

from .engine import LayoutEngine
from .geometry import (
    GAP,
    J,
    LANE_W,
    LINE_H,
    TERM_H,
    TERM_W,
    Block,
    Cell,
    Conn,
    Edge,
    PageLayout,
    anchor_point,
    fit_width,
    line_count,
    wrap_lines,
)
from .page import layout_page, layout_pages
from .routing import route_edge

__all__ = [
    "Block",
    "Cell",
    "Conn",
    "Edge",
    "GAP",
    "J",
    "LANE_W",
    "LINE_H",
    "LayoutEngine",
    "PageLayout",
    "TERM_H",
    "TERM_W",
    "anchor_point",
    "fit_width",
    "layout_page",
    "layout_pages",
    "line_count",
    "route_edge",
    "wrap_lines",
]
