"""Сборка геометрии страниц: от IR-страницы к PageLayout."""

from ..ir import Page
from ..optimizer import coalesce_pages
from .engine import LayoutEngine
from .geometry import GAP, J, LANE_W, TERM_H, TERM_W, PageLayout


def layout_page(page: Page) -> PageLayout:
    """Уложить одну страницу IR в геометрию.

    Args:
        page: Страница IR.

    Returns:
        :class:`PageLayout` с размещёнными ячейками и рёбрами.
    """
    engine = LayoutEngine()
    body_w, body_h = engine.measure(page.body)
    content_w = max(body_w, TERM_W)

    start = engine._add_cell(
        "terminator", page.start_label, (content_w - TERM_W) / 2, 0.0, TERM_W, TERM_H
    )

    body_x = (content_w - body_w) / 2 if body_w else 0.0
    body_y = TERM_H + GAP
    block = engine.place(page.body, body_x, body_y) if page.body.items else None
    body_bottom = body_y + body_h if body_h else TERM_H

    merge = engine._add_junction(content_w / 2, body_bottom + GAP)
    end = engine._add_cell(
        "terminator", "Конец", (content_w - TERM_W) / 2, merge.y + J + GAP, TERM_W, TERM_H
    )

    if block is None or block.entry is None:
        engine._add_edge(start.cid, merge.cid, exit_side="b", entry_side="t")
    else:
        engine._add_edge(start.cid, block.entry.cid, exit_side="b", entry_side="t")
        for conn in block.exits:
            engine._connect(conn, merge, "t")
    engine._add_edge(merge.cid, end.cid, exit_side="b", entry_side="t")

    width = max(content_w, TERM_W)
    merge_cy = merge.y + J / 2
    left_extent = 0.0
    right_extent = width
    for rid in engine.return_ids:
        cell = next(c for c in engine.cells if c.cid == rid)
        cy = cell.y + cell.h / 2
        cx = cell.x + cell.w / 2
        side = "r" if cx >= content_w / 2 else "l"
        x_base = width if side == "r" else 0.0
        lane = engine._alloc_return_lane(side, x_base, min(cy, merge_cy), max(cy, merge_cy))
        engine._add_edge(
            rid, merge.cid, "",
            [(lane, cy), (lane, merge_cy)],
            exit_side=side, entry_side=side,
        )
        if side == "l":
            left_extent = min(left_extent, lane - LANE_W)
        else:
            right_extent = max(right_extent, lane + LANE_W)

    offset = -left_extent if left_extent < 0 else 0.0
    if offset:
        for cell in engine.cells:
            cell.x += offset
        for edge in engine.edges:
            edge.waypoints = [(x + offset, y) for x, y in edge.waypoints]
    width = right_extent + offset

    height = end.y + end.h
    return PageLayout(page.name, engine.cells, engine.edges, width, height, page.func_name)


def layout_pages(pages: list[Page]) -> list[PageLayout]:
    """Уложить список страниц IR.

    Перед укладкой соседние однотипные простые операторы объединяются
    (:func:`drawio_gen.optimizer.coalesce_pages`) для компактности схемы.

    Args:
        pages: Страницы IR.

    Returns:
        Список :class:`PageLayout` в том же порядке.
    """
    coalesce_pages(pages)
    return [layout_page(page) for page in pages]
