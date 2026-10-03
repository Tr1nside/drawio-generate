"""Отрисовка уложенных страниц в SVG для предпросмотра."""

from ..layout import Cell, Edge, PageLayout, route_edge, wrap_lines

FONT_SIZE = 12
LINE_HEIGHT = 20
PAD = 24

KIND_STYLE = {
    "terminator": ("#ffffff", "#333333"),
    "process": ("#ffffff", "#333333"),
    "input": ("#ffffff", "#333333"),
    "output": ("#ffffff", "#333333"),
    "rhombus": ("#ffffff", "#333333"),
    "hexagon": ("#ffffff", "#333333"),
    "other": ("#ffffff", "#333333"),
}


def _esc(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _wrap(text: str, width: float) -> list[str]:
    return wrap_lines(text, max(4.0, width))


def _text_svg(cell: Cell) -> str:
    factor = {"rhombus": 0.5, "hexagon": 0.72}.get(cell.kind, 1.0)
    lines = _wrap(cell.text, (cell.w - 16) * factor)
    cx = cell.x + cell.w / 2
    cy = cell.y + cell.h / 2
    start = cy - (len(lines) - 1) * LINE_HEIGHT / 2 + FONT_SIZE * 0.35
    spans = "".join(
        f'<tspan x="{cx:.1f}" y="{start + i * LINE_HEIGHT:.1f}">{_esc(line)}</tspan>'
        for i, line in enumerate(lines)
    )
    return f'<text text-anchor="middle" font-size="{FONT_SIZE}" fill="#1f2733">{spans}</text>'


def _shape_svg(cell: Cell, link_map: dict) -> str:
    if cell.kind == "junction":
        return ""
    fill, stroke = KIND_STYLE.get(cell.kind, KIND_STYLE["process"])
    x, y, w, h = cell.x, cell.y, cell.w, cell.h
    if cell.kind == "terminator":
        body = f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{h / 2:.1f}" ry="{h / 2:.1f}"/>'
    elif cell.kind == "rhombus":
        body = (
            f'<polygon points="{x + w / 2:.1f},{y:.1f} {x + w:.1f},{y + h / 2:.1f} '
            f'{x + w / 2:.1f},{y + h:.1f} {x:.1f},{y + h / 2:.1f}"/>'
        )
    elif cell.kind in ("input", "output"):
        sk = min(18.0, w * 0.15)
        body = (
            f'<polygon points="{x + sk:.1f},{y:.1f} {x + w:.1f},{y:.1f} '
            f'{x + w - sk:.1f},{y + h:.1f} {x:.1f},{y + h:.1f}"/>'
        )
    elif cell.kind == "hexagon":
        ins = w * 0.15
        body = (
            f'<polygon points="{x + ins:.1f},{y:.1f} {x + w - ins:.1f},{y:.1f} '
            f'{x + w:.1f},{y + h / 2:.1f} {x + w - ins:.1f},{y + h:.1f} '
            f'{x + ins:.1f},{y + h:.1f} {x:.1f},{y + h / 2:.1f}"/>'
        )
    else:
        body = f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}"/>'
    target = link_map.get(cell.link_name) if cell.link_name else None
    attrs = f' class="linkable" data-page="{_esc(target)}"' if target else ""
    return (
        f'<g{attrs} fill="{fill}" stroke="{stroke}" stroke-width="1.5">'
        f"{body}{_text_svg(cell)}</g>"
    )


def _edge_svg(edge: Edge, cells: dict[int, Cell], marker_id: str, arrow: bool) -> str:
    points = route_edge(edge, cells)
    path = " ".join(
        ("M" if i == 0 else "L") + f"{px:.1f} {py:.1f}" for i, (px, py) in enumerate(points)
    )
    marker = f' marker-end="url(#{marker_id})"' if arrow else ""
    parts = [
        f'<path d="{path}" fill="none" stroke="#666" stroke-width="1.5"{marker}/>'
    ]
    if edge.label:
        mid = points[len(points) // 2]
        parts.append(
            f'<text x="{mid[0]:.1f}" y="{mid[1] - 4:.1f}" text-anchor="middle" '
            f'font-size="{FONT_SIZE - 1}" fill="#444">{_esc(edge.label)}</text>'
        )
    return "".join(parts)


def page_svg(page: PageLayout, index: int, link_map: dict) -> str:
    width = page.width + PAD * 2
    height = page.height + PAD * 2
    marker_id = f"arrow-{index}"
    cells = {cell.cid: cell for cell in page.cells}
    junction_ids = {cell.cid for cell in page.cells if cell.kind == "junction"}
    edges = "".join(
        _edge_svg(edge, cells, marker_id, edge.target not in junction_ids)
        for edge in page.edges
    )
    shapes = "".join(_shape_svg(cell, link_map) for cell in page.cells)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" '
        f'role="img" aria-label="Схема {_esc(page.name)}">'
        f"<defs><marker id=\"{marker_id}\" markerWidth=\"10\" markerHeight=\"10\" "
        f'refX="8" refY="3" orient="auto" markerUnits="strokeWidth">'
        f'<path d="M0,0 L8,3 L0,6 z" fill="#666"/></marker></defs>'
        f'<g transform="translate({PAD},{PAD})">{edges}{shapes}</g>'
        f"</svg>"
    )


def build_previews(pages: list[PageLayout]) -> list[dict[str, str]]:
    """Собрать SVG-предпросмотр для каждой страницы.

    Args:
        pages: Список уложенных страниц.

    Returns:
        Список словарей ``{"name": ..., "svg": ...}``.
    """
    link_map: dict[str, str] = {}
    for page in pages:
        if page.func_name:
            link_map[page.func_name] = page.name
    return [
        {"name": page.name, "svg": page_svg(page, i, link_map)}
        for i, page in enumerate(pages)
    ]
