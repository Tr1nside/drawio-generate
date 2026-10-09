"""Юнит-тесты парсеров и реестра языков.

Запуск::

    python3 tests/test_parsers.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from drawio_gen.ir import Break, Continue, For, FuncCall, If, Input, Other, Output, Return, While
from drawio_gen.parsers import (
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
    from drawio_gen.ir import Sequence

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
    from drawio_gen.optimizer import coalesce_pages

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


def test_csharp_switch_patterns():
    code = (
        "using System;\n"
        "class P {\n"
        "    static void Main(object o) {\n"
        "        int x = 1;\n"
        "        switch (o) {\n"
        "            case int n:\n"
        "                Console.WriteLine(n);\n"
        "                break;\n"
        "            default:\n"
        "                Console.WriteLine(0);\n"
        "                break;\n"
        "        }\n"
        "        switch (x) {\n"
        "            case 1:\n"
        "            case 2:\n"
        "                Console.WriteLine(x);\n"
        "                break;\n"
        "        }\n"
        "    }\n"
        "}\n"
    )
    nodes = _flatten(get_parser("csharp").parse(code)[0].body, [])
    ifs = [n for n in nodes if isinstance(n, If)]
    outputs = [n for n in nodes if isinstance(n, Output)]
    assert sum(1 for n in outputs if "WriteLine" in n.text) >= 3, [o.text for o in outputs]
    assert any("int n" in n.condition for n in ifs), [n.condition for n in ifs]
    conditions = [n.condition for n in ifs]
    assert "x == 1" in conditions and "x == 2" in conditions, conditions
    assert not any(isinstance(n, Other) for n in nodes), "pattern не должен попадать как Other"
    print("ok: C# switch (pattern/default/fall-through)")


def test_csharp_console_assignment():
    code = (
        "using System;\n"
        "class P {\n"
        "    static void Main() {\n"
        "        string s;\n"
        "        s = Console.ReadLine();\n"
        "        Console.WriteLine(s);\n"
        "    }\n"
        "}\n"
    )
    nodes = _flatten(get_parser("csharp").parse(code)[0].body, [])
    assert any(isinstance(n, Input) and "ReadLine" in n.text for n in nodes), nodes
    print("ok: C# ввод в присваивании")


def test_csharp_switch_discard():
    code = (
        "using System;\n"
        "class P {\n"
        "    static void Main(int o) {\n"
        "        switch (o) {\n"
        "            case 1:\n"
        "                Console.WriteLine(1);\n"
        "                break;\n"
        "            case _:\n"
        "                Console.WriteLine(42);\n"
        "                break;\n"
        "        }\n"
        "    }\n"
        "}\n"
    )
    nodes = _flatten(get_parser("csharp").parse(code)[0].body, [])
    outputs = [n for n in nodes if isinstance(n, Output)]
    assert any("42" in n.text for n in outputs), [n.text for n in outputs]
    ifs = [n for n in nodes if isinstance(n, If)]
    assert any("is _" in n.condition for n in ifs), [n.condition for n in ifs]
    print("ok: C# switch case _ (discard)")


def test_csharp_top_level_statements():
    code = (
        "using System;\n"
        "\n"
        "int x = int.Parse(Console.ReadLine());\n"
        "Console.WriteLine(x);\n"
    )
    pages = get_parser("csharp").parse(code)
    assert pages[0].name == "main", [p.name for p in pages]
    nodes = _flatten(pages[0].body, [])
    assert any(isinstance(n, Input) for n in nodes), "нет Input"
    assert any(isinstance(n, Output) for n in nodes), "нет Output"
    print("ok: C# top-level statements")


def test_csharp_switch_pattern_labels():
    code = (
        "using System;\n"
        "class P {\n"
        "    static void Main(int o) {\n"
        "        switch (o) {\n"
        "            case 0:\n"
        "                Console.WriteLine(0);\n"
        "                break;\n"
        "            case >= 5:\n"
        "                Console.WriteLine(5);\n"
        "                break;\n"
        "            case int n when n > 0:\n"
        "                Console.WriteLine(n);\n"
        "                break;\n"
        "        }\n"
        "    }\n"
        "}\n"
    )
    ifs = [
        n
        for n in _flatten(get_parser("csharp").parse(code)[0].body, [])
        if isinstance(n, If)
    ]
    conditions = [n.condition for n in ifs]
    assert "o == 0" in conditions, conditions
    assert any("is >= 5" in c for c in conditions), conditions
    assert any("is int n when n > 0" in c for c in conditions), conditions
    print("ok: C# switch labels для паттернов")


def test_convert_language_type():
    import app as webapp

    client = webapp.app.test_client()
    response = client.post(
        "/convert",
        json={"code": "x = 1\n", "language": 123},
    )
    assert response.status_code != 500, response.status_code
    print("ok: нестроковый language не роняет сервер")


def test_csharp_try_catch_throw():
    code = (
        "using System;\n"
        "class P {\n"
        "    static void Main() {\n"
        "        try {\n"
        "            int x = int.Parse(Console.ReadLine());\n"
        "            if (x < 0)\n"
        "                throw new Exception(\"negative\"); // comment here\n"
        "            Console.WriteLine(x);\n"
        "        }\n"
        "        catch (Exception e) // catch comment\n"
        "        {\n"
        "            // log error\n"
        "            Console.WriteLine(\"error\");\n"
        "        }\n"
        "        finally // finally comment\n"
        "        {\n"
        "            /* cleanup */\n"
        "            Console.WriteLine(\"done\");\n"
        "        }\n"
        "    }\n"
        "}\n"
    )
    pages = get_parser("csharp").parse(code)
    nodes = _flatten(pages[0].body, [])
    # throw should be a Return node, not Other
    throws = [n for n in nodes if isinstance(n, Return)]
    assert len(throws) == 1, f"expected 1 Return for throw, got {len(throws)}"
    assert "negative" in throws[0].text
    assert "//" not in throws[0].text, f"comment leaked into throw: {throws[0].text}"
    # catch should be an "exception" conditional with catch handlers in its body
    error_ifs = [n for n in nodes if isinstance(n, If) and n.condition == "exception"]
    assert len(error_ifs) == 1, f"expected 1 exception If, got {[n.condition for n in nodes if isinstance(n, If)]}"
    catch_labels = [n.text for n in error_ifs[0].body.items if isinstance(n, Other)]
    assert any("catch Exception e" in t for t in catch_labels), f"no catch label: {catch_labels}"
    assert error_ifs[0].else_body is None, "no-exception path must not add else body"
    # finally stays as a labeled Other node after the conditional
    others = [n for n in nodes if isinstance(n, Other)]
    assert any("finally" in o.text for o in others), f"no finally label: {[o.text for o in others]}"
    # no comment text should appear in any node
    for n in nodes:
        if hasattr(n, "text"):
            assert "//" not in n.text, f"comment // leaked: {n.text}"
            assert "/*" not in n.text, f"comment /* leaked: {n.text}"
    # catch body should be parsed as normal statements (Output), not raw text
    outputs = [n for n in nodes if isinstance(n, Output)]
    assert any("error" in o.text for o in outputs), f"catch body not parsed: {outputs}"
    assert any("done" in o.text for o in outputs), f"finally body not parsed: {outputs}"
    print("ok: C# try-catch-finally-throw + no comments in nodes")


def test_python_try_except():
    code = (
        "try:\n"
        "    x = int(input())\n"
        "except ValueError as e:  # comment\n"
        "    # handle error\n"
        "    print('invalid')\n"
        "finally:\n"
        "    # cleanup\n"
        "    print('done')\n"
    )
    pages = get_parser("python").parse(code)
    nodes = _flatten(pages[0].body, [])
    error_ifs = [n for n in nodes if isinstance(n, If) and n.condition == "exception"]
    assert len(error_ifs) == 1, f"expected 1 exception If, got {[n.condition for n in nodes if isinstance(n, If)]}"
    except_labels = [n.text for n in error_ifs[0].body.items if isinstance(n, Other)]
    assert any("except ValueError e" in t for t in except_labels), f"no except label: {except_labels}"
    others = [n for n in nodes if isinstance(n, Other)]
    assert any("finally" in o.text for o in others), f"no finally label: {[o.text for o in others]}"
    # no comments in any node
    for n in nodes:
        if hasattr(n, "text"):
            assert "#" not in n.text, f"comment leaked: {n.text}"
    # except body should be parsed as normal statements
    outputs = [n for n in nodes if isinstance(n, Output)]
    assert any("invalid" in o.text for o in outputs), f"except body not parsed: {outputs}"
    assert any("done" in o.text for o in outputs), f"finally body not parsed: {outputs}"
    print("ok: Python try-except-finally + no comments in nodes")


def test_csharp_comments_not_in_nodes():
    code = (
        "using System;\n"
        "class P {\n"
        "    static void Main() {\n"
        '        Console.WriteLine("http://example.com"); // real comment\n'
        '        string s = "a /* not a comment */ b";\n'
        "        // standalone comment\n"
        "        int x = 1; /* block */\n"
        "        Console.WriteLine(s);\n"
        "    }\n"
        "}\n"
    )
    nodes = _flatten(get_parser("csharp").parse(code)[0].body, [])
    # strings with comment-like content must survive intact
    texts = [n.text for n in nodes if hasattr(n, "text")]
    assert any("http://example.com" in t for t in texts), texts
    assert any("a /* not a comment */ b" in t for t in texts), texts
    # standalone comments must not become nodes
    assert all(t.strip() for t in texts), f"empty node leaked: {texts}"
    assert not any("real comment" in t or "standalone" in t for t in texts), texts
    print("ok: C# комментарии не попадают в ноды, строки не ломаются")


def main() -> int:
    tests = [
        test_registry,
        test_detect,
        test_unknown_language,
        test_python_parser,
        test_csharp_parser,
        test_csharp_switch_patterns,
        test_csharp_console_assignment,
        test_csharp_switch_discard,
        test_csharp_top_level_statements,
        test_csharp_switch_pattern_labels,
        test_csharp_try_catch_throw,
        test_python_try_except,
        test_csharp_comments_not_in_nodes,
        test_coalesce,
        test_parse_errors,
        test_convert_language_type,
    ]
    for test in tests:
        test()
    print("\nИТОГ: всё успешно")
    return 0


if __name__ == "__main__":
    sys.exit(main())
