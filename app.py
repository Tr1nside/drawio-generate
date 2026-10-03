"""Точка входа Flask-приложения генератора блок-схем.

Тонкая обёртка над :mod:`drawio_gen.web.app` для запуска
``flask --app app run`` либо ``python app.py``.
"""

from drawio_gen.web.app import app, configure_logging, main, parse_args

__all__ = ["app", "configure_logging", "main", "parse_args"]


if __name__ == "__main__":
    main()
