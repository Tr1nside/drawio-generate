"""Flask-приложение: исходный код (Python/C#) → файл .drawio."""

import argparse
import logging
import os
import sys
import time

from io import BytesIO

from flask import Flask, Response, jsonify, render_template, request

from ..docx_format import build_docx, build_rtf, highlight_html
from ..layout import layout_pages
from ..parsers import ParseError, available_languages, detect_language, get_parser
from ..render import build_mxfile, build_previews

logger = logging.getLogger("drawio")

app = Flask(__name__)


def configure_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        root.addHandler(handler)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)


@app.before_request
def _log_request_start() -> None:
    request._start_time = time.perf_counter()  # type: ignore[attr-defined]


@app.after_request
def _log_request_end(response):
    elapsed = (time.perf_counter() - getattr(request, "_start_time", time.perf_counter())) * 1000
    if request.path.startswith("/static/"):
        logger.debug("%s %s -> %s (%.1f ms)", request.method, request.path, response.status_code, elapsed)
    else:
        logger.info(
            "%s %s -> %s (%.1f ms)",
            request.method,
            request.path,
            response.status_code,
            elapsed,
        )
    return response


@app.errorhandler(404)
def _not_found(error):
    logger.warning("404: %s", request.path)
    if request.path.startswith("/convert"):
        return jsonify(error="Не найдено"), 404
    return render_template("index.html"), 404


@app.errorhandler(500)
def _server_error(error):
    logger.exception("Внутренняя ошибка при обработке %s", request.path)
    return jsonify(error="Внутренняя ошибка сервера"), 500


@app.get("/")
def index():
    return render_template("index.html", languages=available_languages())


@app.get("/healthz")
def healthz():
    return jsonify(status="ok")


@app.post("/convert")
def convert():
    """Построить блок-схему из исходного кода.

    Ожидает JSON с полями ``code`` и (опционально) ``language``.

    Returns:
        JSON с полями ``xml``, ``pages``, ``language``, ``language_name``
        либо ``error`` при ошибке разбора.
    """
    started = time.perf_counter()
    data = request.get_json(silent=True) or {}
    code = data.get("code") or request.form.get("code", "")
    raw_language = data.get("language") or request.form.get("language") or "auto"
    language = str(raw_language).strip()
    if not isinstance(code, str) or not code.strip():
        logger.warning("convert: пустой код")
        return jsonify(error="Пустой код"), 400
    try:
        parser = detect_language(code) if language in ("", "auto") else get_parser(language)
        pages = parser.parse(code)
        layouts = layout_pages(pages)
        xml = build_mxfile(layouts)
        previews = build_previews(layouts)
    except ParseError as exc:
        logger.warning("convert: ошибка разбора (%s): %s", language, exc)
        payload = {"error": str(exc)}
        if exc.line is not None:
            payload["line"] = exc.line
        if exc.column is not None:
            payload["column"] = exc.column
        return jsonify(payload), 400
    except Exception as exc:  # noqa: BLE001
        logger.exception("convert: ошибка обработки кода")
        return jsonify(error=f"Ошибка обработки: {exc}"), 400
    elapsed = (time.perf_counter() - started) * 1000
    logger.info(
        "convert: ok [%s] — %d строк, %d страниц (%s), XML %d Б, %.1f ms",
        parser.id,
        len(code.splitlines()),
        len(layouts),
        ", ".join(page.name for page in pages),
        len(xml),
        elapsed,
    )
    return jsonify(
        xml=xml,
        pages=previews,
        language=parser.id,
        language_name=parser.display_name,
    )


@app.post("/format")
def format_code():
    data = request.get_json(silent=True) or {}
    code = data.get("code") or request.form.get("code", "")
    raw_language = data.get("language") or request.form.get("language") or "auto"
    language = str(raw_language).strip()

    if not isinstance(code, str) or not code.strip():
        return jsonify(error="Пустой код"), 400

    try:
        html, lang_name = highlight_html(code, language)
    except Exception as exc:
        logger.exception("format: ошибка подсветки")
        return jsonify(error=f"Ошибка: {exc}"), 400

    return jsonify(html=html, language=lang_name)


@app.post("/download")
def download():
    data = request.get_json(silent=True) or {}
    code = data.get("code") or request.form.get("code", "")
    raw_language = data.get("language") or request.form.get("language") or "auto"
    language = str(raw_language).strip()

    if not isinstance(code, str) or not code.strip():
        return jsonify(error="Пустой код"), 400

    try:
        buf = build_docx(code, language)
    except Exception as exc:
        logger.exception("download: ошибка генерации docx")
        return jsonify(error=f"Ошибка: {exc}"), 400

    return Response(
        buf.read(),
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": 'attachment; filename="code.docx"',
            "Content-Length": str(buf.tell()),
        },
    )


@app.post("/clipboard")
def clipboard():
    data = request.get_json(silent=True) or {}
    code = data.get("code") or request.form.get("code", "")
    raw_language = data.get("language") or request.form.get("language") or "auto"
    language = str(raw_language).strip()

    if not isinstance(code, str) or not code.strip():
        return jsonify(error="Пустой код"), 400

    try:
        rtf = build_rtf(code, language)
    except Exception as exc:
        logger.exception("clipboard: ошибка генерации RTF")
        return jsonify(error=f"Ошибка: {exc}"), 400

    return jsonify(rtf=rtf)


def _proxy_warning() -> str | None:
    proxy = (
        os.environ.get("HTTP_PROXY")
        or os.environ.get("http_proxy")
        or os.environ.get("ALL_PROXY")
        or os.environ.get("all_proxy")
    )
    if not proxy:
        return None
    return (
        "Обнаружен HTTP-прокси: "
        f"{proxy}\n"
        "  Браузер может отправлять запросы к localhost через прокси и получать 403/503.\n"
        "  Добавьте 127.0.0.1 и localhost в исключения прокси (No proxy for),\n"
        "  либо задайте в терминале: export NO_PROXY=127.0.0.1,localhost"
    )


def _print_banner(host: str, port: int, debug: bool) -> None:
    display_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    url = f"http://{display_host}:{port}"
    lines = [
        "",
        "  ┌─────────────────────────────────────────────┐",
        "  │  Генератор блок-схем + Код в Word           │",
        "  └─────────────────────────────────────────────┘",
        f"  Откройте:   {url}",
        f"  Режим:      {'отладка' if debug else 'обычный'}",
        f"  Слушает:    {host}:{port}",
    ]
    warning = _proxy_warning()
    if warning:
        lines.append("")
        lines.append("  ⚠ " + warning.replace("\n", "\n    "))
    print("\n".join(lines) + "\n", flush=True)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Веб-генератор блок-схем drawio из исходного кода.")
    parser.add_argument(
        "--host",
        default=os.environ.get("HOST", "127.0.0.1"),
        help="адрес прослушивания (по умолчанию 127.0.0.1; для доступа из сети — 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "5000")),
        help="порт (по умолчанию 5000)",
    )
    parser.add_argument(
        "--debug",
        action=argparse.BooleanOptionalAction,
        default=os.environ.get("DEBUG", "").lower() in ("1", "true", "yes"),
        help="включить/выключить режим отладки",
    )
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    configure_logging(args.debug)
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        _print_banner(args.host, args.port, args.debug)
    logger.info("Запуск сервера на %s:%s", args.host, args.port)
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)


if __name__ == "__main__":
    main()
