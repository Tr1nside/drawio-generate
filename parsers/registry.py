"""Реестр языковых парсеров.

Реестр реализует принцип инверсии зависимостей: приложение работает с
абстракцией :class:`parsers.base.LanguageParser`, а конкретные парсеры
регистрируются здесь. Добавление нового языка не требует правок в других
модулях.
"""

from __future__ import annotations

from parsers.base import LanguageParser, ParseError

__all__ = ["LanguageRegistry", "registry", "ParseError"]


class LanguageRegistry:
    """Хранилище доступных языковых парсеров.

    Attributes:
        _parsers: Отображение ``id`` языка → экземпляр парсера.
    """

    def __init__(self) -> None:
        self._parsers: dict[str, LanguageParser] = {}

    def register(self, parser: LanguageParser) -> None:
        """Зарегистрировать парсер.

        Args:
            parser: Экземпляр парсера языка.
        """
        self._parsers[parser.id] = parser

    def get(self, language_id: str) -> LanguageParser:
        """Получить парсер по идентификатору языка.

        Args:
            language_id: Идентификатор языка.

        Returns:
            Зарегистрированный парсер.

        Raises:
            ParseError: Если язык не поддерживается.
        """
        try:
            return self._parsers[language_id]
        except KeyError as exc:
            raise ParseError(f"Язык не поддерживается: {language_id}") from exc

    def languages(self) -> list[tuple[str, str]]:
        """Вернуть список ``(id, display_name)`` всех языков."""
        return [(p.id, p.display_name) for p in self._parsers.values()]

    def detect(self, source: str, default: str = "python") -> LanguageParser:
        """Определить язык по эвристикам парсеров.

        Args:
            source: Исходный код.
            default: Идентификатор языка по умолчанию при неоднозначности.

        Returns:
            Наиболее вероятный парсер.
        """
        best: LanguageParser | None = None
        best_score = -1
        for parser in self._parsers.values():
            score = parser.detect(source)
            if score > best_score:
                best, best_score = parser, score
        if best is None or best_score <= 0:
            return self.get(default)
        return best


def _build_default_registry() -> LanguageRegistry:
    """Собрать реестр со стандартным набором парсеров."""
    reg = LanguageRegistry()
    from parsers.python_parser import PythonParser

    reg.register(PythonParser())
    try:
        from parsers.csharp_parser import CSharpParser

        reg.register(CSharpParser())
    except ImportError:  # pragma: no cover - зависимость tree-sitter необязательна
        pass
    return reg


registry = _build_default_registry()
