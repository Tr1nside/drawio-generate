"""Сериализация уложенных страниц в формат mxfile (drawio)."""

from layout import PageLayout

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
}

ANCHORS = {
    "l": (0.0, 0.5),
    "r": (1.0, 0.5),
    "t": (0.5, 0.0),
    "b": (0.5, 1.0),
}

EDGE_STYLE = "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;"


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


def _cell_xml(cell) -> str:
    style = STYLES.get(cell.kind, STYLES["process"])
    return (
        f'        <mxCell id="{cell.cid}" value="{_esc(cell.text)}" style="{style}" '
        f'vertex="1" parent="1">\n'
        f'          <mxGeometry x="{_num(cell.x)}" y="{_num(cell.y)}" '
        f'width="{_num(cell.w)}" height="{_num(cell.h)}" as="geometry"/>\n'
        f"        </mxCell>"
    )


def _edge_xml(edge, index: int) -> str:
    if edge.waypoints:
        points = "".join(
            f'\n            <mxPoint x="{_num(px)}" y="{_num(py)}"/>'
            for px, py in edge.waypoints
        )
        geometry = (
            '          <mxGeometry relative="1" as="geometry">\n'
            f'            <Array as="points">{points}\n            </Array>\n'
            "          </mxGeometry>"
        )
    else:
        geometry = '          <mxGeometry relative="1" as="geometry"/>'
    style = EDGE_STYLE + _anchor_style(edge.exit_side, edge.entry_side)
    return (
        f'        <mxCell id="e{index}" value="{_esc(edge.label)}" '
        f'style="{style}" edge="1" parent="1" source="{edge.source}" '
        f'target="{edge.target}">\n{geometry}\n        </mxCell>'
    )


def _diagram_xml(page: PageLayout, index: int) -> str:
    cells = "\n".join(_cell_xml(cell) for cell in page.cells)
    base = index * 100000
    edges = "\n".join(_edge_xml(edge, base + i) for i, edge in enumerate(page.edges))
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
    diagrams = "\n".join(_diagram_xml(page, i) for i, page in enumerate(pages))
    return (
        '<mxfile host="app.diagrams.net" agent="drawio-gen" type="device">\n'
        f"{diagrams}\n"
        "</mxfile>"
    )
