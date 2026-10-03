"""Инварианты укладки (layout) и генерации .drawio.

Запуск::

    python3 test_layout.py
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET

from drawio import build_mxfile
from layout import layout_pages
from parsers import get_parser

PYTHON_CODE = (
    "def helper(a):\n"
    "    return a * 2\n"
    "\n"
    'x = input("x = ")\n'
    'print("start")\n'
    "if x:\n"
    "    helper(x)\n"
    "else:\n"
    '    print("no")\n'
    "while x:\n"
    "    x -= 1\n"
)

CSHARP_CODE = (
    "using System;\n"
    "class P {\n"
    "    static int F(int a) { return a + 1; }\n"
    "    static void Main() {\n"
    '        int x = int.Parse(Console.ReadLine());\n'
    "        for (int i = 0; i < 3; i++) { Console.WriteLine(F(i)); }\n"
    "    }\n"
    "}\n"
)


def _layouts(code: str, language: str):
    pages = get_parser(language).parse(code)
    return layout_pages(pages)


def _diagrams(xml: str):
    return ET.fromstring(xml).findall("diagram")


def test_xml_is_well_formed():
    for code, language in ((PYTHON_CODE, "python"), (CSHARP_CODE, "csharp")):
        ET.fromstring(build_mxfile(_layouts(code, language)))


def test_each_page_has_start_and_end():
    for code, language in ((PYTHON_CODE, "python"), (CSHARP_CODE, "csharp")):
        xml = build_mxfile(_layouts(code, language))
        for diagram in _diagrams(xml):
            terminators = [
                cell
                for cell in diagram.iter("mxCell")
                if cell.get("vertex") == "1"
                and "arcSize=50" in (cell.get("style") or "")
            ]
            assert len(terminators) == 2, (diagram.get("name"), len(terminators))


def test_edges_reference_existing_cells():
    for code, language in ((PYTHON_CODE, "python"), (CSHARP_CODE, "csharp")):
        xml = build_mxfile(_layouts(code, language))
        for diagram in _diagrams(xml):
            ids = {cell.get("id") for cell in diagram.iter("mxCell")}
            for cell in diagram.iter("mxCell"):
                if cell.get("edge") == "1":
                    assert cell.get("source") in ids, (diagram.get("name"), "source")
                    assert cell.get("target") in ids, (diagram.get("name"), "target")


def test_special_characters_are_escaped():
    code = 'print("<a> & \\"b\\" \'c\'")\n'
    xml = build_mxfile(_layouts(code, "python"))
    ET.fromstring(xml)
    assert "&lt;a&gt;" in xml
    assert "&amp;" in xml
    assert "&quot;" in xml or "&apos;" in xml


def test_optimizer_coalesces_consecutive_calls():
    code = 'print("a")\nprint("b")\n'
    layouts = _layouts(code, "python")
    outputs = [cell for cell in layouts[0].cells if cell.kind == "output"]
    assert len(outputs) == 1, [c.text for c in outputs]
    assert "\n" in outputs[0].text


def test_unknown_constructs_become_other_block():
    code = "with open('x') as f:\n    pass\n"
    layouts = _layouts(code, "python")
    kinds = {cell.kind for cell in layouts[0].cells}
    assert "other" in kinds, kinds


def main() -> int:
    tests = [
        test_xml_is_well_formed,
        test_each_page_has_start_and_end,
        test_edges_reference_existing_cells,
        test_special_characters_are_escaped,
        test_optimizer_coalesces_consecutive_calls,
        test_unknown_constructs_become_other_block,
    ]
    for test in tests:
        test()
        print(f"ok: {test.__name__}")
    print("\nИТОГ: всё успешно")
    return 0


if __name__ == "__main__":
    sys.exit(main())
