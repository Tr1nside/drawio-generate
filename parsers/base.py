"""Базовые абстракции для парсеров исходного кода.

Модуль задаёт единый интерфейс :class:`LanguageParser`, которому следуют все
языковые парсеры, и язык-нейтральную ошибку :class:`ParseError`.

Каждый парсер обязан возвращать список :class:`ir.Page` — единое
промежуточное представление, поэтому укладка и рендеринг не зависят от языка
(принцип открытости/закрытости).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ir import Page


class ParseError(Exception):
    """Ошибка разбора исходного кода.

    Attributes:
        message: Текст ошибки для пользователя.
        line: Номер строки (1-based) или ``None``.
        column: Номер столбца (1-based) или ``None``.
    """

    def __init__(
        self, message: str, line: int | None = None, column: int | None = None
    ) -> None:
        self.message = message
        self.line = line
        self.column = column
        super().__init__(message)

    def __str__(self) -> str:
        if self.line is None:
            return self.message
        if self.column is None:
            return f"{self.message} (строка {self.line})"
        return f"{self.message} (строка {self.line}, столбец {self.column})"


class LanguageParser(ABC):
    """Интерфейс парсера исходного кода в единый IR.

    Attributes:
        id: Машиночитаемый идентификатор языка (например, ``"python"``).
        display_name: Человекочитаемое название для интерфейса.
    """

    id: str = ""
    display_name: str = ""

    @abstractmethod
    def parse(self, source: str) -> list[Page]:
        """Разобрать исходный код в список страниц блок-схемы.

        Args:
            source: Исходный код на соответствующем языке.

        Returns:
            Список страниц :class:`ir.Page` (первая — главная).

        Raises:
            ParseError: Если код не удалось разобрать.
        """

    def detect(self, source: str) -> int:
        """Оценить, насколько вероятно, что код написан на этом языке.

        Args:
            source: Исходный код.

        Returns:
            Неотрицательный вес; больше — вероятнее. По умолчанию ``0``.
        """
        return 0
