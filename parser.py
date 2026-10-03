"""Обратная совместимость: разбор Python-кода.

Этот модуль оставлен как тонкий shim над :mod:`parsers.python_parser`.
Новый код должен использовать :mod:`parsers`.
"""

from __future__ import annotations

from parsers.python_parser import PythonParser, parse_pages

__all__ = ["PythonParser", "parse_pages"]
