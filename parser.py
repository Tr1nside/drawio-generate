"""Разбор Python-кода (устаревшая точка входа).

Этот модуль оставлен как тонкий shim над
:mod:`drawio_gen.parsers.python_parser`. Новый код должен использовать
:mod:`drawio_gen.parsers` (``get_parser`` / ``detect_language``).

Контракт изменился относительно прежних версий:

* публичный класс ``Parser`` удалён — используйте
  :class:`drawio_gen.parsers.python_parser.PythonParser` либо функцию
  ``parse_pages``;
* ``parse_pages`` теперь возбуждает :class:`drawio_gen.parsers.base.ParseError`
  (с полями ``line`` и ``column``), а не встроенный ``SyntaxError``.
"""

from __future__ import annotations

from drawio_gen.parsers.python_parser import PythonParser, parse_pages

__all__ = ["PythonParser", "parse_pages"]
