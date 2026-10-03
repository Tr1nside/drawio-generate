"""Тесты HTTP-API Flask (шина ``/convert``).

Запуск::

    python3 tests/test_app.py

Тесты используют встроенный test client Flask и не поднимают реальный сервер.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from drawio_gen.web import app as webapp

client = webapp.app.test_client()

PYTHON_CODE = 'x = input("x = ")\nprint(x)\n'
CSHARP_CODE = (
    "using System;\n"
    "class P { static void Main() { Console.WriteLine(1); } }\n"
)


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_index_renders_languages():
    response = client.get("/")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'id="language"' in body
    assert "Python" in body
    assert "C#" in body


def test_convert_python():
    response = client.post("/convert", json={"code": PYTHON_CODE})
    payload = response.get_json()
    assert response.status_code == 200, payload
    assert payload["language"] == "python"
    assert payload["language_name"] == "Python"
    assert "<mxfile" in payload["xml"]
    assert payload["pages"]


def test_convert_csharp():
    response = client.post(
        "/convert", json={"code": CSHARP_CODE, "language": "csharp"}
    )
    payload = response.get_json()
    assert response.status_code == 200, payload
    assert payload["language"] == "csharp"
    assert "<mxfile" in payload["xml"]


def test_convert_auto_detects_csharp():
    response = client.post(
        "/convert", json={"code": CSHARP_CODE, "language": "auto"}
    )
    assert response.status_code == 200
    assert response.get_json()["language"] == "csharp"


def test_convert_empty_code():
    response = client.post("/convert", json={"code": "   "})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_convert_unknown_language():
    response = client.post(
        "/convert", json={"code": PYTHON_CODE, "language": "brainfuck"}
    )
    assert response.status_code == 400
    assert "не поддерживается" in response.get_json()["error"].lower()


def test_convert_non_string_language_does_not_crash():
    for bad in (123, ["csharp"], {"id": "csharp"}, True):
        response = client.post(
            "/convert", json={"code": PYTHON_CODE, "language": bad}
        )
        assert response.status_code != 500, (bad, response.status_code)


def test_convert_non_string_code_does_not_crash():
    response = client.post("/convert", json={"code": 12345})
    assert response.status_code == 400


def test_convert_syntax_error_reports_line():
    response = client.post("/convert", json={"code": "def (\n", "language": "python"})
    payload = response.get_json()
    assert response.status_code == 400
    assert payload.get("line") == 1


def main() -> int:
    tests = [
        test_healthz,
        test_index_renders_languages,
        test_convert_python,
        test_convert_csharp,
        test_convert_auto_detects_csharp,
        test_convert_empty_code,
        test_convert_unknown_language,
        test_convert_non_string_language_does_not_crash,
        test_convert_non_string_code_does_not_crash,
        test_convert_syntax_error_reports_line,
    ]
    for test in tests:
        test()
        print(f"ok: {test.__name__}")
    print("\nИТОГ: всё успешно")
    return 0


if __name__ == "__main__":
    sys.exit(main())
