"""Юнит-тесты парсеров и реестра языков.

Запуск::

    python3 test_parsers.py
"""

from __future__ import annotations

import sys

from ir import Break, Continue, For, FuncCall, If, Input, Output, Return, While
from parsers import (
    ParseError,
    available_languages,
    detect_language,
    get_parser,
)

PYTHON_CODE = (
    "def foo():\n"
    "    return 1\n"
    "\n"
    "x = input()\n"
    "print(x)\n"
    "if x:\n"
    "    foo()\n"
)

CSHARP_CODE = (
    "using System;\n"
    "class P {\n"
    "    static void Main(string[] a) {\n"
    '        int x = int.Parse(Console.ReadLine());\n'
    '        Console.WriteLine("hi");\n'
    "        if (x > 0) { Console.Write(x); } else { Console.Write(-x); }\n"
    "        while (x < 3) { x++; if (x == 1) continue; if (x == 2) break; }\n"
    "        for (int i = 0; i < 3; i++) { Console.WriteLine(i); }\n"
    "        foreach (var c in a) { Console.WriteLine(c); }\n"
    "        Add(1, 2);\n"
    "        return;\n"
    "    }\n"
    "    static int Add(int a, int b) { return a + b; }\n"
    "}\n"
)


def _flatten(node, acc):
    from ir import Sequence

    items = node.items if isinstance(node, Sequence) else [node]
    for item in items:
        acc.append(item)
        if isinstance(item, If):
            _flatten(item.body, acc)
            if item.else_body:
                _flatten(item.else_body, acc)
        elif isinstance(item, (While, For)):
            _flatten(item.body, acc)
    return acc


def test_registry():
    langs = dict(available_languages())
    assert langs.get("python") == "Python", langs
    assert langs.get("csharp") == "C#", langs
    print("ok: реестр языков")


def test_detect():
    assert detect_language(PYTHON_CODE).id == "python"
    assert detect_language(CSHARP_CODE).id == "csharp"
    print("ok: автодетект языка")


def test_unknown_language():
    try:
        get_parser("brainfuck")
    except ParseError:
        pass
    else:  # pragma: no cover
        raise AssertionError("ожидалась ParseError для неизвестного языка")
    print("ok: неизвестный язык")


def test_python_parser():
    pages = get_parser("python").parse(PYTHON_CODE)
    names = [p.name for p in pages]
    assert names == ["main", "foo"], names
    nodes = _flatten(pages[0].body, [])
    assert any(isinstance(n, Input) for n in nodes)
    assert any(isinstance(n, Output) for n in nodes)
    assert any(isinstance(n, FuncCall) and n.call_name == "foo" for n in nodes)
    print("ok: Python-парсер")


def test_csharp_parser():
    pages = get_parser("csharp").parse(CSHARP_CODE)
    names = [p.name for p in pages]
    assert names == ["main", "Add"], names
    nodes = _flatten(pages[0].body, [])
    assert any(isinstance(n, Input) for n in nodes), "нет Input"
    assert any(isinstance(n, Output) for n in nodes), "нет Output"
    assert any(isinstance(n, If) for n in nodes), "нет If"
    assert any(isinstance(n, While) for n in nodes), "нет While"
    assert any(isinstance(n, For) for n in nodes), "нет For"
    assert any(isinstance(n, Break) for n in nodes), "нет Break"
    assert any(isinstance(n, Continue) for n in nodes), "нет Continue"
    assert any(isinstance(n, Return) for n in nodes), "нет Return"
    assert any(isinstance(n, FuncCall) and n.call_name == "Add" for n in nodes), "нет FuncCall"
    print("ok: C#-парсер")


def test_coalesce():
    from optimizer import coalesce_pages

    code = 'print("a")\nprint("b")\nprint("c")\nx = 1\ny = 2\n'
    pages = get_parser("python").parse(code)
    coalesce_pages(pages)
    items = pages[0].body.items
    outputs = [n for n in items if isinstance(n, Output)]
    processes = [n for n in items if type(n).__name__ == "Process"]
    assert len(outputs) == 1 and outputs[0].text.count("\n") == 2, outputs
    assert len(processes) == 1 and processes[0].text.count("\n") == 1, processes
    print("ok: объединение простых операторов")


def test_parse_errors():
    try:
        get_parser("python").parse("def (")
    except ParseError as exc:
        assert exc.line == 1, exc.line
    else:  # pragma: no cover
        raise AssertionError("ожидалась ParseError (Python)")

    try:
        get_parser("csharp").parse("class {")
    except ParseError as exc:
        assert exc.line is not None
    else:  # pragma: no cover
        raise AssertionError("ожидалась ParseError (C#)")
    print("ok: ошибки разбора с позицией")


def main() -> int:
    tests = [
        test_registry,
        test_detect,
        test_unknown_language,
        test_python_parser,
        test_csharp_parser,
        test_coalesce,
        test_parse_errors,
    ]
    for test in tests:
        test()
    print("\nИТОГ: всё успешно")
    return 0


if __name__ == "__main__":
    sys.exit(main())
