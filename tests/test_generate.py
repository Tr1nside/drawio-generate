"""Проверка генерации .drawio на примерах Python и C#."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import xml.etree.ElementTree as ET

from drawio_gen.render import build_mxfile
from drawio_gen.layout import layout_pages, route_edge
from drawio_gen.parsers import get_parser

FIX_DIR = Path(__file__).parent / "fixtures"
OUT_DIR = Path(__file__).parent / "out"

CASES = {
    "python/LAB3/17.py": {
        "language": "python",
        "pages": {"main", "main_2", "_input_data", "_check_triangle", "_check_equilateralism"},
        "rhombus": 3,
        "io": 7,
        "max_crossings": 0,
    },
    "python/LAB4/22.py": {
        "language": "python",
        "pages": {"main"},
        "rhombus": 2,
        "io": 2,
        "max_crossings": 0,
    },
    "python/LAB5/66.py": {
        "language": "python",
        "pages": {"main"},
        "rhombus": 1,
        "hexagon": 1,
        "io": 2,
        "max_crossings": 0,
    },
    "csharp/basic.cs": {
        "language": "csharp",
        "pages": {"main"},
        "rhombus": 2,
        "io": 5,
        "max_crossings": 0,
    },
    "csharp/loops.cs": {
        "language": "csharp",
        "pages": {"main"},
        "rhombus": 4,
        "hexagon": 2,
        "io": 2,
        "max_crossings": 0,
    },
    "csharp/switch_try.cs": {
        "language": "csharp",
        "pages": {"main", "Divide"},
        "rhombus": 3,
        "io": 5,
        "max_crossings": 0,
    },
}


def classify(style):
    if "pointerEvents=0" in style or "opacity=0" in style:
        return "junction"
    if "arcSize=50" in style:
        return "terminator"
    if style.startswith("rhombus"):
        return "rhombus"
    if "shape=hexagon" in style:
        return "hexagon"
    if "shape=parallelogram" in style:
        return "io"
    return "process"


def analyse(xml):
    root = ET.fromstring(xml)
    diagrams = {}
    for diagram in root.findall("diagram"):
        counts = {}
        for cell in diagram.iter("mxCell"):
            if cell.get("vertex") != "1":
                continue
            kind = classify(cell.get("style", ""))
            if kind == "junction":
                continue
            counts[kind] = counts.get(kind, 0) + 1
        diagrams[diagram.get("name")] = counts
    return diagrams


def _cross(p1, p2, p3, p4):
    def orient(a, b, c):
        v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(v) < 1e-9:
            return 0
        return 1 if v > 0 else -1

    o1, o2 = orient(p1, p2, p3), orient(p1, p2, p4)
    o3, o4 = orient(p3, p4, p1), orient(p3, p4, p2)
    return o1 * o2 < 0 and o3 * o4 < 0


def _segments(points):
    return list(zip(points, points[1:]))


def _segment_hits_rect(p, q, r, pad=2.0):
    x1, y1 = p
    x2, y2 = q
    rx0, ry0 = r.x + pad, r.y + pad
    rx1, ry1 = r.x + r.w - pad, r.y + r.h - pad
    if rx1 <= rx0 or ry1 <= ry0:
        return False
    dx, dy = x2 - x1, y2 - y1
    t0, t1 = 0.0, 1.0
    for pp, qq in ((-dx, x1 - rx0), (dx, rx1 - x1), (-dy, y1 - ry0), (dy, ry1 - y1)):
        if pp == 0:
            if qq < 0:
                return False
        else:
            t = qq / pp
            if pp < 0:
                if t > t1:
                    return False
                t0 = max(t0, t)
            else:
                if t < t0:
                    return False
                t1 = min(t1, t)
    return True


def metrics(layouts):
    crossings = 0
    overlaps = 0
    node_crossings = 0
    per_page = {}
    for page in layouts:
        cells = {c.cid: c for c in page.cells}
        polys = [(edge, route_edge(edge, cells)) for edge in page.edges]
        page_cross = 0
        for i in range(len(polys)):
            for j in range(i + 1, len(polys)):
                for a in _segments(polys[i][1]):
                    for b in _segments(polys[j][1]):
                        if _cross(a[0], a[1], b[0], b[1]):
                            page_cross += 1
        real = [c for c in page.cells if c.kind != "junction"]
        page_overlap = 0
        for i, a in enumerate(real):
            for b in real[i + 1:]:
                if a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h:
                    page_overlap += 1
        page_node = 0
        for edge, points in polys:
            for seg in _segments(points):
                for c in real:
                    if c.cid in (edge.source, edge.target):
                        continue
                    if _segment_hits_rect(seg[0], seg[1], c):
                        page_node += 1
        crossings += page_cross
        overlaps += page_overlap
        node_crossings += page_node
        per_page[page.name] = (page_cross, page_overlap, page_node)
    return crossings, overlaps, node_crossings, per_page


def main():
    OUT_DIR.mkdir(exist_ok=True)
    failed = False

    for rel, expected in CASES.items():
        language = expected["language"]
        source = (FIX_DIR / rel).read_text(encoding="utf-8")
        print(f"\n=== {rel} [{language}] ===")
        try:
            pages = get_parser(language).parse(source)
            layouts = layout_pages(pages)
            xml = build_mxfile(layouts)
            ET.fromstring(xml)
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL: ошибка построения/парсинга XML: {exc}")
            failed = True
            continue

        out = OUT_DIR / (Path(rel).name.replace(".py", "").replace(".cs", "") + ".drawio")
        out.write_text(xml, encoding="utf-8")

        diagrams = analyse(xml)
        crossings, overlaps, node_crossings, per_page = metrics(layouts)
        print(f"  страниц: {len(diagrams)} -> {', '.join(diagrams)}")
        for name, counts in diagrams.items():
            pc, po, pn = per_page.get(name, (0, 0, 0))
            print(f"  [{name}] {counts}  пересечений={pc} наложений={po} сквозь узлы={pn}")

        if set(diagrams) != expected["pages"]:
            print(f"  FAIL: страницы {set(diagrams)} != {expected['pages']}")
            failed = True

        for name, counts in diagrams.items():
            if counts.get("terminator", 0) != 2:
                print(f"  FAIL: {name}: ожидалось 2 terminator")
                failed = True

        total = {}
        for counts in diagrams.values():
            for key, value in counts.items():
                total[key] = total.get(key, 0) + value
        for key in ("rhombus", "hexagon", "io"):
            if key in expected and total.get(key, 0) != expected[key]:
                print(f"  FAIL: {key} = {total.get(key, 0)}, ожидалось {expected[key]}")
                failed = True

        limit = expected.get("max_crossings", 0)
        if crossings > limit:
            print(f"  FAIL: пересечений {crossings} > допустимых {limit}")
            failed = True
        if overlaps > 0:
            print(f"  FAIL: наложений фигур {overlaps}")
            failed = True
        if node_crossings > 0:
            print(f"  FAIL: рёбра проходят сквозь узлы: {node_crossings}")
            failed = True

        print(f"  итого пересечений={crossings}, наложений={overlaps}, сквозь узлы={node_crossings}")
        print(f"  сохранено: {out}")

    print("\nИТОГ:", "ОШИБКИ" if failed else "всё успешно")
    return 1 if failed else 0


def test_generation_cases() -> None:
    """Pytest-обёртка: полный прогон генерации и проверок метрик."""
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
