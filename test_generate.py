"""Проверка генерации .drawio на тестовых файлах LAB3/4/5."""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from drawio import build_mxfile
from layout import layout_pages
from parser import parse_pages

CS_DIR = Path("/Users/chertik/Documents/Projects/CS")
OUT_DIR = Path(__file__).parent / "out"

CASES = {
    "LAB3/17.py": {
        "pages": {"main", "main_2", "_input_data", "_check_triangle", "_check_equilateralism"},
        "rhombus": 3,
        "io": 9,
    },
    "LAB4/22.py": {
        "pages": {"main"},
        "rhombus": 2,
        "io": 2,
    },
    "LAB5/66.py": {
        "pages": {"main"},
        "rhombus": 1,
        "hexagon": 1,
        "io": 2,
    },
}


def parse_build(source):
    pages = layout_pages(parse_pages(source))
    return build_mxfile(pages)


def classify(style):
    if "arcSize=50" in style:
        return "terminator"
    if style.startswith("rhombus"):
        return "rhombus"
    if "shape=hexagon" in style:
        return "hexagon"
    if "shape=parallelogram" in style:
        return "io"
    if "rounded=0" in style:
        return "process"
    return "process"


def analyse(xml):
    root = ET.fromstring(xml)
    diagrams = {}
    for diagram in root.findall("diagram"):
        name = diagram.get("name")
        counts = {}
        for cell in diagram.iter("mxCell"):
            if cell.get("vertex") != "1":
                continue
            kind = classify(cell.get("style", ""))
            counts[kind] = counts.get(kind, 0) + 1
        diagrams[name] = counts
    return diagrams


def main():
    OUT_DIR.mkdir(exist_ok=True)
    failed = False

    for rel, expected in CASES.items():
        path = CS_DIR / rel
        source = path.read_text(encoding="utf-8")
        print(f"\n=== {rel} ===")
        try:
            xml = parse_build(source)
            ET.fromstring(xml)
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL: ошибка построения/парсинга XML: {exc}")
            failed = True
            continue

        out = OUT_DIR / (Path(rel).name.replace(".py", "") + ".drawio")
        out.write_text(xml, encoding="utf-8")

        diagrams = analyse(xml)
        print(f"  страниц: {len(diagrams)} -> {', '.join(diagrams)}")

        if set(diagrams) != expected["pages"]:
            print(f"  FAIL: страницы {set(diagrams)} != {expected['pages']}")
            failed = True

        for name, counts in diagrams.items():
            terms = counts.get("terminator", 0)
            print(f"  [{name}] {counts}")
            if terms != 2:
                print(f"  FAIL: {name}: ожидалось 2 terminator (начало+конец), получено {terms}")
                failed = True

        total = {}
        for counts in diagrams.values():
            for key, value in counts.items():
                total[key] = total.get(key, 0) + value
        for key in ("rhombus", "hexagon", "io"):
            if key in expected and total.get(key, 0) != expected[key]:
                print(f"  FAIL: {key} = {total.get(key, 0)}, ожидалось {expected[key]}")
                failed = True

        print(f"  сохранено: {out}")

    print("\nИТОГ:", "ОШИБКИ" if failed else "всё успешно")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
