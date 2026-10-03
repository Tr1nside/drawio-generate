"""Расчёт координат фигур (IR -> геометрия)."""

from dataclasses import dataclass, field

from ir import (
    Break,
    Continue,
    For,
    FuncCall,
    If,
    Input,
    Other,
    Output,
    Page,
    Process,
    Return,
    Sequence,
    While,
)

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


def _line_count(text: str) -> int:
    return max(1, len(text.splitlines()))


def _fit_width(text: str, base: float) -> float:
    longest = max((len(line) for line in text.splitlines()), default=0)
    return max(base, min(MAX_W, int(longest * CHAR_W) + TEXT_PAD))


def wrap_lines(text: str, width: float) -> list:
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


def _orthogonalize(raw: list, start_side: str) -> list:
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


def route_edge(edge: "Edge", cells: dict) -> list:
    """Построить полную ортогональную полилинию ребра.

    Используется и предпросмотром, и генератором ``.drawio`` — это
    гарантирует одинаковый маршрут в обоих представлениях.

    Args:
        edge: Ребро с якорями и промежуточными точками.
        cells: Отображение ``cid → Cell``.

    Returns:
        Список точек ``[(x, y), ...]`` от якоря источника до якоря цели.
    """
    source = cells[edge.source]
    target = cells[edge.target]
    start = anchor_point(source, edge.exit_side)
    end = anchor_point(target, edge.entry_side)
    return _orthogonalize([start, *edge.waypoints, end], edge.exit_side)


class LayoutEngine:
    """Рекурсивный расчёт геометрии одной страницы.

    Содержит изменяемое состояние: размещённые ячейки, рёбра, идентификаторы
    возвратов и реестр дорожек. Для каждой страницы создаётся новый движок.
    """

    def __init__(self) -> None:
        self.cells: list[Cell] = []
        self.edges: list[Edge] = []
        self.return_ids: list[int] = []
        self._return_lanes: dict = {"l": [], "r": []}
        self._id = 1

    def _nid(self) -> int:
        self._id += 1
        return self._id

    def _add_cell(self, kind, text, x, y, w, h, link_name="") -> Cell:
        cell = Cell(self._nid(), kind, text, x, y, w, h, link_name)
        self.cells.append(cell)
        return cell

    def _add_junction(self, x: float, y: float) -> Cell:
        return self._add_cell("junction", "", x - J / 2, y - J / 2, J, J)

    def _add_edge(self, source, target, label="", waypoints=None, exit_side="b", entry_side="t"):
        self.edges.append(
            Edge(source, target, label, list(waypoints or []), exit_side, entry_side)
        )

    def _connect(self, conn: Conn, target, entry_side="t") -> None:
        self._add_edge(
            conn.cell.cid,
            target.cid,
            conn.label,
            conn.waypoints,
            conn.side,
            entry_side,
        )

    # --- измерение -------------------------------------------------------
    def simple_size(self, text: str) -> tuple[float, float]:
        w = _fit_width(text, PROC_W)
        lines = wrap_lines(text, w - 16)
        h = max(PROC_H, len(lines) * LINE_H + 20)
        return w, h

    @staticmethod
    def shape_size(text: str, base_w: float, base_h: float, factor: float) -> tuple[float, float]:
        w = _fit_width(text, base_w)
        inner = max(40.0, (w - 16) * factor)
        lines = wrap_lines(text, inner)
        h = max(base_h, len(lines) * LINE_H + 24)
        return w, h

    def condition_size(self, text: str) -> tuple[float, float]:
        w = _fit_width(text, RHOMBUS_W)
        lines = wrap_lines(text, w * 0.5)
        longest = max((len(line) for line in lines), default=0)
        w = max(w, int(longest * CHAR_W / 0.6) + 16)
        lines = wrap_lines(text, w * 0.5)
        h = max(RHOMBUS_H, int(len(lines) * LINE_H / 0.6) + 16)
        return w, h

    def for_size(self, text: str) -> tuple[float, float]:
        return self.shape_size(text, HEX_W, HEX_H, 0.72)

    def measure(self, node) -> tuple[float, float]:
        if isinstance(node, Sequence):
            if not node.items:
                return 0.0, 0.0
            w = 0.0
            h = 0.0
            for i, item in enumerate(node.items):
                iw, ih = self.measure(item)
                w = max(w, iw)
                h += ih
                if i:
                    h += GAP
            return w, h

        if isinstance(node, (Process, Input, Output, FuncCall, Other, Return, Break, Continue)):
            return self.simple_size(node.text)

        if isinstance(node, If):
            geo = self._if_geometry(node)
            return geo["w"], geo["h"]

        if isinstance(node, While):
            geo = self._loop_geometry(node, "rhombus")
            return geo["w"], geo["h"]

        if isinstance(node, For):
            geo = self._loop_geometry(node, "hexagon")
            return geo["w"], geo["h"]

        return PROC_W, PROC_H

    def _if_geometry(self, node: If) -> dict:
        dw, dh = self.condition_size(node.condition)
        has_else = node.else_body is not None and bool(node.else_body.items)
        bw, bh = self.measure(node.body) if node.body.items else (0.0, 0.0)
        ew, eh = self.measure(node.else_body) if has_else else (0.0, 0.0)
        spine_rel = max(dw / 2, bw + GAP / 2)
        right_extent = max(dw / 2, (GAP / 2 + ew) if has_else else 0.0)
        w = max(dw, spine_rel + right_extent)
        body_h = max(bh, eh if has_else else 0.0)
        h = dh + GAP + (body_h + GAP if body_h else 0.0) + J
        return {
            "dw": dw, "dh": dh, "has_else": has_else,
            "bw": bw, "bh": bh, "ew": ew, "eh": eh,
            "spine_rel": spine_rel, "w": w, "h": h,
        }

    def _loop_geometry(self, node, head_kind: str) -> dict:
        if head_kind == "hexagon":
            head_text = node.text
            hw, hh = self.for_size(head_text)
        else:
            head_text = node.condition
            hw, hh = self.condition_size(head_text)
        bw, bh = self.measure(node.body) if node.body.items else (0.0, 0.0)
        content_w = max(hw, bw)
        w = content_w + 2 * BACK_MARGIN
        body_part = (GAP + bh) if bh else 0.0
        h = hh + body_part + GAP + J + GAP + J
        return {
            "hw": hw, "hh": hh, "head_text": head_text,
            "bw": bw, "bh": bh, "content_w": content_w, "w": w, "h": h,
        }

    # --- укладка ---------------------------------------------------------
    def place(self, node, x: float, y: float, ctx=None) -> Block:
        if isinstance(node, Sequence):
            return self._place_sequence(node, x, y, ctx)
        if isinstance(node, (Break, Continue)):
            return self._place_jump(node, x, y, ctx)
        if isinstance(node, (Process, Input, Output, FuncCall, Other, Return)):
            return self._place_simple(node, x, y)
        if isinstance(node, If):
            return self._place_if(node, x, y, ctx)
        if isinstance(node, While):
            return self._place_loop(node, x, y, ctx, "rhombus")
        if isinstance(node, For):
            return self._place_loop(node, x, y, ctx, "hexagon")
        return Block(self._add_cell("process", "", x, y, PROC_W, PROC_H), [], PROC_W, PROC_H)

    def _place_sequence(self, node: Sequence, x: float, y: float, ctx) -> Block:
        w, h = self.measure(node)
        cur = y
        entry = None
        prev = None
        for item in node.items:
            iw, ih = self.measure(item)
            ix = x + (w - iw) / 2
            block = self.place(item, ix, cur, ctx)
            if entry is None and block.entry is not None:
                entry = block.entry
            if prev is not None and block.entry is not None:
                for conn in prev:
                    self._connect(conn, block.entry, "t")
            prev = block.exits
            cur += ih + GAP
        return Block(entry, prev if prev is not None else [], w, h)

    def _place_simple(self, node, x: float, y: float) -> Block:
        w, h = self.simple_size(node.text)
        kind = {
            Process: "process",
            FuncCall: "process",
            Input: "input",
            Output: "output",
            Other: "other",
            Return: "process",
        }.get(type(node), "process")
        link = getattr(node, "call_name", "") if isinstance(node, FuncCall) else ""
        cell = self._add_cell(kind, node.text, x, y, w, h, link)
        if isinstance(node, Return):
            self.return_ids.append(cell.cid)
            return Block(cell, [], w, h)
        return Block(cell, [Conn(cell)], w, h)

    def _place_jump(self, node, x: float, y: float, ctx) -> Block:
        w, h = self.simple_size(node.text)
        cell = self._add_cell("process", node.text, x, y, w, h)
        if ctx is not None:
            cx = cell.x + cell.w / 2
            cy = cell.y + cell.h / 2
            if isinstance(node, Break):
                exit_j = ctx["exit_j"]
                ex_cx = exit_j.x + exit_j.w / 2
                ex_cy = exit_j.y + exit_j.h / 2
                side = "l" if cx < ex_cx else "r"
                lane = ctx["left"] if side == "l" else ctx["right"]
                self._add_edge(
                    cell.cid, exit_j.cid, "",
                    [(lane, cy), (lane, ex_cy)],
                    exit_side=side, entry_side=side,
                )
            else:
                head = ctx["head"]
                self._add_edge(
                    cell.cid, head.cid, "", [(ctx["left"], cy)],
                    exit_side="l", entry_side="l",
                )
            return Block(cell, [], w, h)
        return Block(cell, [Conn(cell)], w, h)

    def _place_if(self, node: If, x: float, y: float, ctx) -> Block:
        geo = self._if_geometry(node)
        w, h = geo["w"], geo["h"]
        dw, dh = geo["dw"], geo["dh"]
        spine = x + geo["spine_rel"]
        diamond = self._add_cell("rhombus", node.condition, spine - dw / 2, y, dw, dh)
        body_y = y + dh + GAP

        base_bottom = y + dh
        true_block = None
        false_block = None

        if node.body.items:
            bx = spine - GAP / 2 - geo["bw"]
            true_block = self.place(node.body, bx, body_y, ctx)
            self._add_edge(diamond.cid, true_block.entry.cid, "Да", exit_side="l", entry_side="t")
            base_bottom = max(base_bottom, body_y + geo["bh"])

        if geo["has_else"]:
            fx = spine + GAP / 2
            false_block = self.place(node.else_body, fx, body_y, ctx)
            self._add_edge(diamond.cid, false_block.entry.cid, "Нет", exit_side="r", entry_side="t")
            base_bottom = max(base_bottom, body_y + geo["eh"])

        merge = self._add_junction(spine, base_bottom + GAP)

        if true_block is not None:
            for conn in true_block.exits:
                self._connect(conn, merge, "t")
        else:
            self._add_edge(diamond.cid, merge.cid, "Да", exit_side="l", entry_side="t")

        if false_block is not None:
            for conn in false_block.exits:
                self._connect(conn, merge, "t")
        else:
            self._add_edge(diamond.cid, merge.cid, "Нет", exit_side="b", entry_side="t")

        return Block(diamond, [Conn(merge, "", "b")], w, h)

    def _place_loop(self, node, x: float, y: float, ctx, head_kind: str) -> Block:
        geo = self._loop_geometry(node, head_kind)
        w, h = geo["w"], geo["h"]
        margin = BACK_MARGIN
        content_w = geo["content_w"]
        spine = x + w / 2
        head_w, head_h = geo["hw"], geo["hh"]

        head = self._add_cell(head_kind, geo["head_text"], spine - head_w / 2, y, head_w, head_h)
        bw, bh = geo["bw"], geo["bh"]
        body_y = y + head_h + GAP
        back_j = self._add_junction(spine, body_y + (bh if bh else 0) + GAP)
        exit_j = self._add_junction(spine, back_j.y + J + GAP)

        inner = {
            "head": head,
            "back_j": back_j,
            "exit_j": exit_j,
            "left": x + margin / 2,
            "right": x + w - margin / 2,
        }

        if node.body.items:
            body_x = x + margin + (content_w - bw) / 2
            block = self.place(node.body, body_x, body_y, inner)
            first_label = "Да" if head_kind == "rhombus" else ""
            self._add_edge(head.cid, block.entry.cid, first_label, exit_side="b", entry_side="t")
            for conn in block.exits:
                self._connect(conn, back_j, "t")
        else:
            self._add_edge(head.cid, back_j.cid, exit_side="b", entry_side="t")

        head_cy = y + head_h / 2
        self._add_edge(
            back_j.cid, head.cid, "", [(x + margin / 2, head_cy)],
            exit_side="l", entry_side="l",
        )
        self._add_edge(
            head.cid, exit_j.cid, "Нет" if head_kind == "rhombus" else "",
            [(x + w - margin / 2, head_cy)],
            exit_side="r", entry_side="r",
        )

        return Block(head, [Conn(exit_j, "", "b")], w, h)

    def _alloc_return_lane(self, side: str, x_base: float, y0: float, y1: float) -> float:
        lanes = self._return_lanes[side]
        k = 0
        while True:
            offset = LANE_W * (k + 1)
            x = x_base + offset if side == "r" else x_base - offset
            conflict = any(
                abs(lx - x) < 0.5 and not (y1 <= ly0 or y0 >= ly1)
                for lx, ly0, ly1 in lanes
            )
            if not conflict:
                lanes.append((x, y0, y1))
                return x
            k += 1


def layout_page(page: Page) -> PageLayout:
    """Уложить одну страницу IR в геометрию.

    Args:
        page: Страница IR.

    Returns:
        :class:`PageLayout` с размещёнными ячейками и рёбрами.
    """
    engine = LayoutEngine()
    body_w, body_h = engine.measure(page.body)
    content_w = max(body_w, TERM_W)

    start = engine._add_cell(
        "terminator", page.start_label, (content_w - TERM_W) / 2, 0.0, TERM_W, TERM_H
    )

    body_x = (content_w - body_w) / 2 if body_w else 0.0
    body_y = TERM_H + GAP
    block = engine.place(page.body, body_x, body_y) if page.body.items else None
    body_bottom = body_y + body_h if body_h else TERM_H

    merge = engine._add_junction(content_w / 2, body_bottom + GAP)
    end = engine._add_cell(
        "terminator", "Конец", (content_w - TERM_W) / 2, merge.y + J + GAP, TERM_W, TERM_H
    )

    if block is None or block.entry is None:
        engine._add_edge(start.cid, merge.cid, exit_side="b", entry_side="t")
    else:
        engine._add_edge(start.cid, block.entry.cid, exit_side="b", entry_side="t")
        for conn in block.exits:
            engine._connect(conn, merge, "t")
    engine._add_edge(merge.cid, end.cid, exit_side="b", entry_side="t")

    width = max(content_w, TERM_W)
    merge_cy = merge.y + J / 2
    left_extent = 0.0
    right_extent = width
    for rid in engine.return_ids:
        cell = next(c for c in engine.cells if c.cid == rid)
        cy = cell.y + cell.h / 2
        cx = cell.x + cell.w / 2
        side = "r" if cx >= content_w / 2 else "l"
        x_base = width if side == "r" else 0.0
        lane = engine._alloc_return_lane(side, x_base, min(cy, merge_cy), max(cy, merge_cy))
        engine._add_edge(
            rid, merge.cid, "",
            [(lane, cy), (lane, merge_cy)],
            exit_side=side, entry_side=side,
        )
        if side == "l":
            left_extent = min(left_extent, lane - LANE_W)
        else:
            right_extent = max(right_extent, lane + LANE_W)

    offset = -left_extent if left_extent < 0 else 0.0
    if offset:
        for cell in engine.cells:
            cell.x += offset
        for edge in engine.edges:
            edge.waypoints = [(x + offset, y) for x, y in edge.waypoints]
    width = right_extent + offset

    height = end.y + end.h
    return PageLayout(page.name, engine.cells, engine.edges, width, height, page.func_name)


def layout_pages(pages: list[Page]) -> list[PageLayout]:
    """Уложить список страниц IR.

    Args:
        pages: Страницы IR.

    Returns:
        Список :class:`PageLayout` в том же порядке.
    """
    return [layout_page(page) for page in pages]
