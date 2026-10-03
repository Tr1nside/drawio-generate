"""Сериализация уложенных страниц в формат mxfile (drawio)."""

from layout import PageLayout, route_edge

NEUTRAL = "fillColor=#ffffff;strokeColor=#333333;"

STYLES = {
    "terminator": f"rounded=1;arcSize=50;whiteSpace=wrap;html=1;{NEUTRAL}",
    "process": f"rounded=0;whiteSpace=wrap;html=1;{NEUTRAL}",
    "input": (
        "shape=parallelogram;perimeter=parallelogramPerimeter;whiteSpace=wrap;"
        f"html=1;fixedSize=1;{NEUTRAL}"
    ),
    "output": (
        "shape=parallelogram;perimeter=parallelogramPerimeter;whiteSpace=wrap;"
        f"html=1;fixedSize=1;{NEUTRAL}"
    ),
    "rhombus": f"rhombus;whiteSpace=wrap;html=1;{NEUTRAL}",
    "hexagon": (
        f"shape=hexagon;perimeter=hexagonPerimeter2;whiteSpace=wrap;html=1;fixedSize=1;{NEUTRAL}"
    ),
    "other": f"rounded=0;whiteSpace=wrap;html=1;{NEUTRAL}",
    "junction": (
        "ellipse;fillColor=none;strokeColor=none;html=1;"
        "pointerEvents=0;resizable=0;movable=0;"
    ),
}

ANCHORS = {
    "l": (0.0, 0.5),
    "r": (1.0, 0.5),
    "t": (0.5, 0.0),
    "b": (0.5, 1.0),
}

EDGE_STYLE = "rounded=0;html=1;endArrow=block;"


def _anchor_style(exit_side: str, entry_side: str) -> str:
    ex, ey = ANCHORS.get(exit_side, ANCHORS["b"])
    ix, iy = ANCHORS.get(entry_side, ANCHORS["t"])
    return (
        f"exitX={ex};exitY={ey};exitDx=0;exitDy=0;"
        f"entryX={ix};entryY={iy};entryDx=0;entryDy=0;"
    )


def _esc(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
        .replace("\n", "&#10;")
    )


def _num(value: float) -> str:
    return str(int(round(value)))


def _cell_xml(cell, link_map: dict) -> str:
    style = STYLES.get(cell.kind, STYLES["process"])
    if cell.kind == "junction":
        style += "opacity=0;"
    link = ""
    target = link_map.get(cell.link_name) if cell.link_name else None
    if target is not None:
        link = f' link="data:page/id,page-{target}"'
    return (
        f'        <mxCell id="{cell.cid}" value="{_esc(cell.text)}" style="{style}" '
        f'vertex="1" parent="1"{link}>\n'
        f'          <mxGeometry x="{_num(cell.x)}" y="{_num(cell.y)}" '
        f'width="{_num(cell.w)}" height="{_num(cell.h)}" as="geometry"/>\n'
        f"        </mxCell>"
    )


def _edge_xml(edge, index: int, cells: dict, junction_ids: set) -> str:
    points = route_edge(edge, cells)
    middle = points[1:-1]
    if middle:
        pts = "".join(
            f'\n            <mxPoint x="{_num(px)}" y="{_num(py)}"/>'
            for px, py in middle
        )
        geometry = (
            '          <mxGeometry relative="1" as="geometry">\n'
            f'            <Array as="points">{pts}\n            </Array>\n'
            "          </mxGeometry>"
        )
    else:
        geometry = '          <mxGeometry relative="1" as="geometry"/>'
    style = EDGE_STYLE + _anchor_style(edge.exit_side, edge.entry_side)
    if edge.target in junction_ids:
        style = style.replace("endArrow=block;", "endArrow=none;")
    return (
        f'        <mxCell id="e{index}" value="{_esc(edge.label)}" '
        f'style="{style}" edge="1" parent="1" source="{edge.source}" '
        f'target="{edge.target}">\n{geometry}\n        </mxCell>'
    )


def _diagram_xml(page: PageLayout, index: int, link_map: dict) -> str:
    cells = "\n".join(_cell_xml(cell, link_map) for cell in page.cells)
    cell_map = {cell.cid: cell for cell in page.cells}
    junction_ids = {cell.cid for cell in page.cells if cell.kind == "junction"}
    base = index * 100000
    edges = "\n".join(
        _edge_xml(edge, base + i, cell_map, junction_ids)
        for i, edge in enumerate(page.edges)
    )
    body = "\n".join(part for part in (cells, edges) if part)
    return (
        f'  <diagram id="page-{index}" name="{_esc(page.name)}">\n'
        f'    <mxGraphModel dx="800" dy="600" grid="1" gridSize="10" guides="1" '
        f'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
        f'pageWidth="850" pageHeight="1100" math="0" shadow="0">\n'
        f"      <root>\n"
        f'        <mxCell id="0"/>\n'
        f'        <mxCell id="1" parent="0"/>\n'
        f"{body}\n"
        f"      </root>\n"
        f"    </mxGraphModel>\n"
        f"  </diagram>"
    )


def build_mxfile(pages: list[PageLayout]) -> str:
    """Сериализовать уложенные страницы в XML формата mxfile.

    Args:
        pages: Список уложенных страниц.

    Returns:
        Строка XML, готовая к сохранению в файл ``.drawio``.
    """
    link_map: dict[str, int] = {}
    for i, page in enumerate(pages):
        if page.func_name:
            link_map[page.func_name] = i
    diagrams = "\n".join(_diagram_xml(page, i, link_map) for i, page in enumerate(pages))
    return (
        '<mxfile host="app.diagrams.net" agent="drawio-gen" type="device">\n'
        f"{diagrams}\n"
        "</mxfile>"
    )
