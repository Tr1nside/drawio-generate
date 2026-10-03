"""Пакет языковых парсеров.

Публичный API:

* :func:`get_parser` — получить парсер по идентификатору языка;
* :func:`detect_language` — определить язык по исходному коду;
* :func:`available_languages` — список поддерживаемых языков;
* :class:`ParseError` — язык-нейтральная ошибка разбора.
"""

from __future__ import annotations

from .base import LanguageParser, ParseError
from .registry import LanguageRegistry, registry

__all__ = [
    "LanguageParser",
    "LanguageRegistry",
    "ParseError",
    "available_languages",
    "detect_language",
    "get_parser",
    "registry",
]


def get_parser(language_id: str) -> LanguageParser:
    """Вернуть парсер по идентификатору языка.

    Args:
        language_id: Идентификатор языка (например, ``"python"``).

    Returns:
        Экземпляр :class:`LanguageParser`.
    """
    return registry.get(language_id)


def detect_language(source: str) -> LanguageParser:
    """Определить язык исходного кода по эвристикам.

    Args:
        source: Исходный код.

    Returns:
        Наиболее вероятный парсер языка.
    """
    return registry.detect(source)


def available_languages() -> list[tuple[str, str]]:
    """Вернуть список ``(id, display_name)`` поддерживаемых языков."""
    return registry.languages()
