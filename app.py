"""Flask-приложение: Python-код -> файл .drawio."""

from flask import Flask, jsonify, render_template, request

from drawio import build_mxfile
from layout import layout_pages
from parser import parse_pages
from preview import build_previews

app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/convert")
def convert():
    data = request.get_json(silent=True) or {}
    code = data.get("code") or request.form.get("code", "")
    if not code.strip():
        return jsonify(error="Пустой код"), 400
    try:
        pages = parse_pages(code)
        layouts = layout_pages(pages)
        xml = build_mxfile(layouts)
        previews = build_previews(layouts)
    except SyntaxError as exc:
        line = f" (строка {exc.lineno})" if exc.lineno else ""
        return jsonify(error=f"Синтаксическая ошибка: {exc.msg}{line}"), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify(error=f"Ошибка обработки: {exc}"), 400
    return jsonify(xml=xml, pages=previews)


if __name__ == "__main__":
    app.run(debug=True)
