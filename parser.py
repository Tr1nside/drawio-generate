"""Разбор Python-кода (устаревшая точка входа).

Этот модуль оставлен как тонкий shim над :mod:`parsers.python_parser`.
Новый код должен использовать :mod:`parsers` (``get_parser`` /
``detect_language``).

Контракт изменился относительно прежних версий:

* публичный класс ``Parser`` удалён — используйте
  :class:`parsers.python_parser.PythonParser` либо функцию ``parse_pages``;
* ``parse_pages`` теперь возбуждает :class:`parsers.base.ParseError`
  (с полями ``line`` и ``column``), а не встроенный ``SyntaxError``.
"""

from __future__ import annotations

from parsers.python_parser import PythonParser, parse_pages

__all__ = ["PythonParser", "parse_pages"]
