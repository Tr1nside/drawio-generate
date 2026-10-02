"""Промежуточное представление (IR) блок-схемы."""

from dataclasses import dataclass, field


@dataclass
class Node:
    """Базовый узел IR."""


@dataclass
class Sequence(Node):
    items: list = field(default_factory=list)


@dataclass
class Process(Node):
    text: str = ""


@dataclass
class Input(Node):
    text: str = ""


@dataclass
class Output(Node):
    text: str = ""


@dataclass
class FuncCall(Node):
    text: str = ""
    call_name: str = ""


@dataclass
class Other(Node):
    text: str = ""


@dataclass
class Return(Node):
    text: str = ""


@dataclass
class Break(Node):
    text: str = "break"


@dataclass
class Continue(Node):
    text: str = "continue"


@dataclass
class Branch:
    condition: str
    body: Sequence


@dataclass
class If(Node):
    condition: str = ""
    body: Sequence = field(default_factory=Sequence)
    else_body: "Sequence | None" = None


@dataclass
class While(Node):
    condition: str = ""
    body: Sequence = field(default_factory=Sequence)


@dataclass
class For(Node):
    text: str = ""
    body: Sequence = field(default_factory=Sequence)


@dataclass
class Page:
    name: str
    body: Sequence
    start_label: str = "Начало"
    func_name: "str | None" = None
