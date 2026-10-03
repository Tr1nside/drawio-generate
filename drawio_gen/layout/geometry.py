"""Геометрия фигур, работа с текстом и модели уложенной страницы."""

from dataclasses import dataclass, field

GAP = 40
PROC_W = 170
PROC_H = 40
RHOMBUS_W = 170
RHOMBUS_H = 80
HEX_W = 180
HEX_H = 60
TERM_W = 150
TERM_H = 40
BACK_MARGIN = 40
LANE_W = 20
J = 1
LINE_H = 20
CHAR_W = 7.2
MAX_W = 360
TEXT_PAD = 24


@dataclass
class Cell:
    cid: int
    kind: str
    text: str
    x: float
    y: float
    w: float
    h: float
    link_name: str = ""


@dataclass
class Conn:
    cell: Cell
    label: str = ""
    side: str = "b"
    waypoints: list = field(default_factory=list)


@dataclass
class Edge:
    source: int
    target: int
    label: str = ""
    waypoints: list = field(default_factory=list)
    exit_side: str = "b"
    entry_side: str = "t"


@dataclass
class Block:
    entry: "Cell | None"
    exits: list
    w: float
    h: float


@dataclass
class PageLayout:
    name: str
    cells: list
    edges: list
    width: float
    height: float
    func_name: "str | None" = None


def line_count(text: str) -> int:
    """Число строк в тексте (минимум одна)."""
    return max(1, len(text.splitlines()))


def fit_width(text: str, base: float) -> float:
    """Подобрать ширину фигуры под самую длинную строку текста."""
    longest = max((len(line) for line in text.splitlines()), default=0)
    return max(base, min(MAX_W, int(longest * CHAR_W) + TEXT_PAD))


def wrap_lines(text: str, width: float) -> list:
    """Разбить текст на строки по ширине фигуры (в пикселях)."""
    max_chars = max(4, int(width / CHAR_W))
    lines: list = []
    for raw in (text or "").splitlines() or [""]:
        words = raw.split()
        if not words:
            lines.append("")
            continue
        cur = ""
        for word in words:
            if not cur:
                cur = word
            elif len(cur) + 1 + len(word) <= max_chars:
                cur += " " + word
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def anchor_point(cell: "Cell", side: str) -> tuple[float, float]:
    """Точка на границе фигуры для заданной стороны.

    Args:
        cell: Геометрия фигуры.
        side: Одна из сторон ``"l"``, ``"r"``, ``"t"``, ``"b"``.

    Returns:
        Координаты ``(x, y)`` точки привязки.
    """
    cx = cell.x + cell.w / 2
    cy = cell.y + cell.h / 2
    if side == "l":
        return cell.x, cy
    if side == "r":
        return cell.x + cell.w, cy
    if side == "t":
        return cx, cell.y
    return cx, cell.y + cell.h


def _dedupe(points: list) -> list:
    out: list = []
    for point in points:
        if not out or abs(point[0] - out[-1][0]) > 0.5 or abs(point[1] - out[-1][1]) > 0.5:
            out.append(point)
    return out


def orthogonalize(raw: list, start_side: str) -> list:
    """Привести ломаную к ортогональному виду (только горизонтали/вертикали)."""
    result = [raw[0]]
    first = True
    for q in raw[1:]:
        p = result[-1]
        if abs(p[0] - q[0]) < 0.5 or abs(p[1] - q[1]) < 0.5:
            result.append(q)
        else:
            if first and start_side in ("l", "r"):
                result.append((q[0], p[1]))
            else:
                result.append((p[0], q[1]))
            result.append(q)
        first = False
    return _dedupe(result)
