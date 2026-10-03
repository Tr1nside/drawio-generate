"""Промежуточное представление (IR) блок-схемы.

IR не зависит от языка программирования: любой парсер из пакета
:mod:`parsers` возвращает набор :class:`Page`. Укладка (:mod:`layout`) и
рендеринг (:mod:`drawio`, :mod:`preview`) работают только с этими узлами.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Node:
    """Базовый узел IR."""


@dataclass
class Sequence(Node):
    """Последовательность узлов, выполняемых сверху вниз."""

    items: list[Node] = field(default_factory=list)


@dataclass
class Process(Node):
    """Действие/присваивание (прямоугольник)."""

    text: str = ""


@dataclass
class Input(Node):
    """Ввод данных (параллелограмм)."""

    text: str = ""


@dataclass
class Output(Node):
    """Вывод данных (параллелограмм)."""

    text: str = ""


@dataclass
class FuncCall(Node):
    """Вызов функции.

    Attributes:
        text: Исходный текст вызова.
        call_name: Имя вызываемой функции (для ссылок между страницами).
    """

    text: str = ""
    call_name: str = ""


@dataclass
class Other(Node):
    """Неподдерживаемая конструкция (блок «прочее»)."""

    text: str = ""


@dataclass
class Return(Node):
    """Возврат из функции (дуга к «Концу»)."""

    text: str = ""


@dataclass
class Break(Node):
    """Досрочный выход из цикла."""

    text: str = "break"


@dataclass
class Continue(Node):
    """Переход к следующей итерации цикла."""

    text: str = "continue"


@dataclass
class If(Node):
    """Условие (ромб) с ветками ``body`` и ``else_body``.

    ``else if`` представляется вложенным :class:`If` внутри ``else_body``.
    """

    condition: str = ""
    body: Sequence = field(default_factory=Sequence)
    else_body: "Sequence | None" = None


@dataclass
class While(Node):
    """Цикл с условием (ромб)."""

    condition: str = ""
    body: Sequence = field(default_factory=Sequence)


@dataclass
class For(Node):
    """Цикл с параметром/перебором (шестиугольник)."""

    text: str = ""
    body: Sequence = field(default_factory=Sequence)


@dataclass
class Page:
    """Одна страница диаграммы (``main`` или функция).

    Attributes:
        name: Имя страницы (уникальное).
        body: Тело страницы.
        start_label: Текст фигуры «Начало».
        func_name: Имя исходной функции (для гиперссылок), если применимо.
    """

    name: str
    body: Sequence
    start_label: str = "Начало"
    func_name: "str | None" = None
