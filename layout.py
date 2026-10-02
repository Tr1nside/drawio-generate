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
    return max(base, min(400, 7 * longest))


def anchor_point(cell: Cell, side: str) -> tuple[float, float]:
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


def route_edge(edge: Edge, cells: dict) -> list:
    """Полная ортогональная полилиния ребра (от якоря до якоря)."""
    source = cells[edge.source]
    target = cells[edge.target]
    start = anchor_point(source, edge.exit_side)
    end = anchor_point(target, edge.entry_side)
    return _orthogonalize([start, *edge.waypoints, end], edge.exit_side)


class LayoutEngine:
    def __init__(self) -> None:
        self.cells: list[Cell] = []
        self.edges: list[Edge] = []
        self.return_ids: list[int] = []
        self._return_lanes: list[tuple[float, float, float]] = []
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
        lines = _line_count(text)
        w = _fit_width(text, PROC_W)
        h = PROC_H + LINE_H * (lines - 1)
        return w, h

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
            bw, bh = self.measure(node.body)
            has_else = node.else_body is not None and bool(node.else_body.items)
            ew, eh = self.measure(node.else_body) if node.else_body is not None else (0.0, 0.0)
            body_h = max(bh, eh if has_else else 0.0)
            right_w = ew if has_else else 0.0
            w = max(RHOMBUS_W, bw + (GAP + right_w if right_w else 0.0))
            if body_h:
                h = RHOMBUS_H + GAP + body_h + GAP + J
            else:
                h = RHOMBUS_H + GAP + J
            return w, h

        if isinstance(node, While):
            return self._measure_loop(node, RHOMBUS_H)

        if isinstance(node, For):
            return self._measure_loop(node, HEX_H)

        return PROC_W, PROC_H

    def _measure_loop(self, node, head_h: float) -> tuple[float, float]:
        bw, bh = self.measure(node.body)
        head_w = RHOMBUS_W if head_h == RHOMBUS_H else HEX_W
        content_w = max(head_w, bw)
        w = content_w + 2 * BACK_MARGIN
        body_part = (GAP + bh) if bh else 0.0
        h = head_h + body_part + GAP + J + GAP + J
        return w, h

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
            cy = cell.y + cell.h / 2
            if isinstance(node, Break):
                self._add_edge(
                    cell.cid, ctx["exit_j"].cid, "", [(ctx["right"], cy)],
                    exit_side="r", entry_side="t",
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
        w, h = self.measure(node)
        spine = x + w / 2
        diamond = self._add_cell(
            "rhombus", node.condition, spine - RHOMBUS_W / 2, y, RHOMBUS_W, RHOMBUS_H
        )
        body_y = y + RHOMBUS_H + GAP
        has_else = node.else_body is not None and bool(node.else_body.items)

        base_bottom = y + RHOMBUS_H
        true_block = None
        false_block = None

        if node.body.items:
            bw, bh = self.measure(node.body)
            bx = max(x, spine - GAP / 2 - bw)
            true_block = self.place(node.body, bx, body_y, ctx)
            self._add_edge(diamond.cid, true_block.entry.cid, "Да", exit_side="l", entry_side="t")
            base_bottom = max(base_bottom, body_y + bh)

        if has_else:
            ew, eh = self.measure(node.else_body)
            fx = spine + GAP / 2
            false_block = self.place(node.else_body, fx, body_y, ctx)
            self._add_edge(diamond.cid, false_block.entry.cid, "Нет", exit_side="r", entry_side="t")
            base_bottom = max(base_bottom, body_y + eh)

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
        w, h = self.measure(node)
        margin = BACK_MARGIN
        content_w = w - 2 * margin
        spine = x + w / 2
        if head_kind == "hexagon":
            head_w, head_h, head_text = HEX_W, HEX_H, node.text
        else:
            head_w, head_h, head_text = RHOMBUS_W, RHOMBUS_H, node.condition

        head = self._add_cell(head_kind, head_text, spine - head_w / 2, y, head_w, head_h)
        bw, bh = self.measure(node.body)
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

    def _alloc_return_lane(self, x_base: float, y0: float, y1: float) -> float:
        k = 0
        while True:
            x = x_base + LANE_W * (k + 1)
            conflict = any(
                abs(lx - x) < 0.5 and not (y1 <= ly0 or y0 >= ly1)
                for lx, ly0, ly1 in self._return_lanes
            )
            if not conflict:
                self._return_lanes.append((x, y0, y1))
                return x
            k += 1


def layout_page(page: Page) -> PageLayout:
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
    for rid in engine.return_ids:
        cell = next(c for c in engine.cells if c.cid == rid)
        cy = cell.y + cell.h / 2
        lane = engine._alloc_return_lane(width, min(cy, merge_cy), max(cy, merge_cy))
        engine._add_edge(
            rid, merge.cid, "",
            [(lane, cy), (lane, merge_cy)],
            exit_side="r", entry_side="r",
        )
        width = max(width, lane + LANE_W)

    height = end.y + end.h
    return PageLayout(page.name, engine.cells, engine.edges, width, height, page.func_name)


def layout_pages(pages: list[Page]) -> list[PageLayout]:
    return [layout_page(page) for page in pages]
