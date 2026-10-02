"""Отрисовка уложенных страниц в SVG для предпросмотра."""

from layout import Cell, Edge, PageLayout

FONT_SIZE = 12
LINE_HEIGHT = 16
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
    max_chars = max(4, int(width / (FONT_SIZE * 0.62)))
    lines: list[str] = []
    for raw in (text or "").splitlines() or [""]:
        words = raw.split()
        if not words:
            lines.append("")
            continue
        cur = ""
        for word in words:
            if not cur:
                cur = word
            elif len(cur) + 1 + len(word) <= max_chars:
                cur += " " + word
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def _text_svg(cell: Cell) -> str:
    lines = _wrap(cell.text, cell.w - 16)
    cx = cell.x + cell.w / 2
    cy = cell.y + cell.h / 2
    start = cy - (len(lines) - 1) * LINE_HEIGHT / 2 + FONT_SIZE * 0.35
    spans = "".join(
        f'<tspan x="{cx:.1f}" y="{start + i * LINE_HEIGHT:.1f}">{_esc(line)}</tspan>'
        for i, line in enumerate(lines)
    )
    return f'<text text-anchor="middle" font-size="{FONT_SIZE}" fill="#1f2733">{spans}</text>'


def _shape_svg(cell: Cell) -> str:
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
    return (
        f'<g fill="{fill}" stroke="{stroke}" stroke-width="1.5">'
        f"{body}{_text_svg(cell)}</g>"
    )


def _anchor(rect: Cell, side: str) -> tuple[float, float]:
    cx = rect.x + rect.w / 2
    cy = rect.y + rect.h / 2
    if side == "l":
        return rect.x, cy
    if side == "r":
        return rect.x + rect.w, cy
    if side == "t":
        return cx, rect.y
    return cx, rect.y + rect.h


def _dedupe(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for point in points:
        if not out or abs(point[0] - out[-1][0]) > 0.5 or abs(point[1] - out[-1][1]) > 0.5:
            out.append(point)
    return out


def _orthogonalize(raw: list, start_side: str) -> list:
    result = [raw[0]]
    first = True
    for q in raw[1:]:
        p = result[-1]
        if abs(p[0] - q[0]) < 0.5 or abs(p[1] - q[1]) < 0.5:
            result.append(q)
        else:
            if first and start_side in ("l", "r"):
                result.append((q[0], p[1]))
            else:
                result.append((p[0], q[1]))
            result.append(q)
        first = False
    return _dedupe(result)


def _points_for(edge: Edge, cells: dict[int, Cell]) -> list[tuple[float, float]]:
    source = cells[edge.source]
    target = cells[edge.target]
    start = _anchor(source, edge.exit_side)
    end = _anchor(target, edge.entry_side)
    raw = [start, *edge.waypoints, end]
    return _orthogonalize(raw, edge.exit_side)


def _edge_svg(edge: Edge, cells: dict[int, Cell], marker_id: str) -> str:
    points = _points_for(edge, cells)
    path = " ".join(
        ("M" if i == 0 else "L") + f"{px:.1f} {py:.1f}" for i, (px, py) in enumerate(points)
    )
    parts = [
        f'<path d="{path}" fill="none" stroke="#666" stroke-width="1.5" '
        f'marker-end="url(#{marker_id})"/>'
    ]
    if edge.label:
        mid = points[len(points) // 2]
        parts.append(
            f'<text x="{mid[0]:.1f}" y="{mid[1] - 4:.1f}" text-anchor="middle" '
            f'font-size="{FONT_SIZE - 1}" fill="#444">{_esc(edge.label)}</text>'
        )
    return "".join(parts)


def page_svg(page: PageLayout, index: int) -> str:
    width = page.width + PAD * 2
    height = page.height + PAD * 2
    marker_id = f"arrow-{index}"
    cells = {cell.cid: cell for cell in page.cells}
    edges = "".join(_edge_svg(edge, cells, marker_id) for edge in page.edges)
    shapes = "".join(_shape_svg(cell) for cell in page.cells)
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
    return [{"name": page.name, "svg": page_svg(page, i)} for i, page in enumerate(pages)]
