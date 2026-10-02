"""Расчёт координат фигур (IR -> геометрия)."""

from dataclasses import dataclass, field

from ir import (
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


def _line_count(text: str) -> int:
    return max(1, len(text.splitlines()))


def _fit_width(text: str, base: float) -> float:
    longest = max((len(line) for line in text.splitlines()), default=0)
    return max(base, min(400, 7 * longest))


class LayoutEngine:
    def __init__(self) -> None:
        self.cells: list[Cell] = []
        self.edges: list[Edge] = []
        self.return_ids: list[int] = []
        self._id = 1

    def _nid(self) -> int:
        self._id += 1
        return self._id

    def _add_cell(self, kind: str, text: str, x, y, w, h) -> Cell:
        cell = Cell(self._nid(), kind, text, x, y, w, h)
        self.cells.append(cell)
        return cell

    def _add_edge(
        self,
        source: int,
        target: int,
        label: str = "",
        waypoints=None,
        exit_side: str = "b",
        entry_side: str = "t",
    ) -> None:
        self.edges.append(
            Edge(source, target, label, list(waypoints or []), exit_side, entry_side)
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

        if isinstance(node, (Process, Input, Output, FuncCall, Other, Return)):
            return self.simple_size(node.text)

        if isinstance(node, If):
            bw, bh = self.measure(node.body)
            has_else = node.else_body is not None and bool(node.else_body.items)
            ew, eh = self.measure(node.else_body) if node.else_body is not None else (0.0, 0.0)
            body_h = max(bh, eh if has_else else 0.0)
            right_w = ew if has_else else RHOMBUS_W
            w = max(RHOMBUS_W, bw + GAP + right_w)
            h = RHOMBUS_H + (GAP + body_h if body_h else 0.0)
            return w, h

        if isinstance(node, While):
            bw, bh = self.measure(node.body)
            content_w = max(RHOMBUS_W, bw)
            h = RHOMBUS_H + (GAP + bh if bh else 0.0)
            return content_w + 2 * BACK_MARGIN, h

        if isinstance(node, For):
            bw, bh = self.measure(node.body)
            content_w = max(HEX_W, bw)
            h = HEX_H + (GAP + bh if bh else 0.0)
            return content_w + 2 * BACK_MARGIN, h

        return PROC_W, PROC_H

    # --- укладка ---------------------------------------------------------
    def place(self, node, x: float, y: float) -> Block:
        if isinstance(node, Sequence):
            return self._place_sequence(node, x, y)
        if isinstance(node, (Process, Input, Output, FuncCall, Other, Return)):
            return self._place_simple(node, x, y)
        if isinstance(node, If):
            return self._place_if(node, x, y)
        if isinstance(node, While):
            return self._place_loop(node, x, y, "rhombus")
        if isinstance(node, For):
            return self._place_loop(node, x, y, "hexagon")
        return Block(self._add_cell("process", "", x, y, PROC_W, PROC_H), [], PROC_W, PROC_H)

    def _place_sequence(self, node: Sequence, x: float, y: float) -> Block:
        w, h = self.measure(node)
        cur = y
        entry = None
        prev = None
        exits: list = []
        for item in node.items:
            iw, ih = self.measure(item)
            ix = x + (w - iw) / 2
            block = self.place(item, ix, cur)
            if entry is None and block.entry is not None:
                entry = block.entry
            if prev is not None and block.entry is not None:
                for conn in prev:
                    self._add_edge(
                        conn.cell.cid, block.entry.cid, conn.label,
                        waypoints=conn.waypoints,
                        exit_side=conn.side, entry_side="t",
                    )
            prev = block.exits
            cur += ih + GAP
        if prev is not None:
            exits = prev
        return Block(entry, exits, w, h)

    def _place_simple(self, node, x: float, y: float) -> Block:
        w, h = self.simple_size(node.text)
        kind = {
            Process: "process",
            FuncCall: "process",
            Input: "input",
            Output: "output",
            Other: "other",
            Return: "process",
        }[type(node)]
        cell = self._add_cell(kind, node.text, x, y, w, h)
        if isinstance(node, Return):
            self.return_ids.append(cell.cid)
            return Block(cell, [], w, h)
        return Block(cell, [Conn(cell)], w, h)

    def _place_if(self, node: If, x: float, y: float) -> Block:
        w, h = self.measure(node)
        center = x + w / 2
        diamond = self._add_cell("rhombus", node.condition, center - RHOMBUS_W / 2, y, RHOMBUS_W, RHOMBUS_H)
        body_y = y + RHOMBUS_H + GAP
        exits: list = []

        if node.body.items:
            bw, _ = self.measure(node.body)
            bx = max(x, center - GAP / 2 - bw)
            block = self.place(node.body, bx, body_y)
            self._add_edge(diamond.cid, block.entry.cid, "Да", exit_side="l", entry_side="t")
            exits.extend(block.exits)

        has_else = node.else_body is not None and bool(node.else_body.items)
        if has_else:
            ew, _ = self.measure(node.else_body)
            ex = min(center + GAP / 2, x + w - ew)
            block = self.place(node.else_body, ex, body_y)
            self._add_edge(diamond.cid, block.entry.cid, "Нет", exit_side="r", entry_side="t")
            exits.extend(block.exits)
        else:
            exits.append(Conn(diamond, "Нет", "r", [(x + w, y + h)]))

        return Block(diamond, exits, w, h)

    def _place_loop(self, node, x: float, y: float, head_kind: str) -> Block:
        w, h = self.measure(node)
        margin = BACK_MARGIN
        content_w = w - 2 * margin
        center = x + w / 2
        if head_kind == "hexagon":
            head_w, head_h, head_text = HEX_W, HEX_H, node.text
        else:
            head_w, head_h, head_text = RHOMBUS_W, RHOMBUS_H, node.condition

        head = self._add_cell(head_kind, head_text, center - head_w / 2, y, head_w, head_h)
        exits: list = []

        if node.body.items:
            bw, bh = self.measure(node.body)
            body_x = x + margin + (content_w - bw) / 2
            body_y = y + head_h + GAP
            block = self.place(node.body, body_x, body_y)
            first_label = "Да" if head_kind == "rhombus" else ""
            self._add_edge(head.cid, block.entry.cid, first_label, exit_side="b", entry_side="t")
            head_cx = center
            head_cy = y + head_h / 2
            for conn in block.exits:
                cell = conn.cell
                cell_cx = cell.x + cell.w / 2
                side = "l" if cell_cx <= head_cx else "r"
                wx = x + margin / 2 if side == "l" else x + w - margin / 2
                entry = "l" if side == "l" else "r"
                self._add_edge(
                    cell.cid, head.cid, "", [(wx, head_cy)],
                    exit_side=side, entry_side=entry,
                )

        exits.append(
            Conn(
                head,
                "Нет" if head_kind == "rhombus" else "",
                "r",
                [(x + w - margin / 2, y + h)],
            )
        )
        return Block(head, exits, w, h)


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
    end = engine._add_cell(
        "terminator", "Конец", (content_w - TERM_W) / 2, body_bottom + GAP, TERM_W, TERM_H
    )

    if block is None or block.entry is None:
        engine._add_edge(start.cid, end.cid, exit_side="b", entry_side="t")
    else:
        engine._add_edge(start.cid, block.entry.cid, exit_side="b", entry_side="t")
        for conn in block.exits:
            engine._add_edge(
                conn.cell.cid, end.cid, conn.label,
                waypoints=conn.waypoints,
                exit_side=conn.side or "b", entry_side="t",
            )

    width = max(content_w, TERM_W)
    if engine.return_ids:
        ret_right = width + 40
        end_cy = end.y + end.h / 2
        for rid in engine.return_ids:
            engine._add_edge(
                rid, end.cid, exit_side="r", entry_side="t",
                waypoints=[(ret_right, end_cy)],
            )
        width = ret_right + 40

    height = body_bottom + GAP + TERM_H
    return PageLayout(page.name, engine.cells, engine.edges, width, height)


def layout_pages(pages: list[Page]) -> list[PageLayout]:
    return [layout_page(page) for page in pages]
