"""Оптимизация IR для компактных диаграмм.

Объединяет подряд идущие однотипные простые операторы (присваивания,
ввод, вывод, «прочее») в один узел, чтобы в схеме не появлялось множество
одинаковых фигур по одной строке. Например, два соседних ``print`` становятся
одной фигурой с двумя строками текста.

Модуль не зависит от языка: работает с готовым IR.
"""

from __future__ import annotations

from .ir import For, If, Input, Other, Output, Page, Process, Sequence, While

#: Типы узлов, которые допускается объединять (одинаковые и подряд).
_MERGEABLE = (Process, Input, Output, Other)


def coalesce_pages(pages: list[Page]) -> list[Page]:
    """Объединить соседние простые операторы на всех страницах.

    Args:
        pages: Страницы IR (мутируются на месте).

    Returns:
        Тот же список страниц с объединёнными узлами.
    """
    for page in pages:
        page.body = _optimize_node(page.body)
    return pages


def _optimize_node(node):
    """Рекурсивно оптимизировать узел (в глубину)."""
    if isinstance(node, Sequence):
        return _merge_items(node.items)
    if isinstance(node, If):
        node.body = _optimize_node(node.body)
        if node.else_body is not None:
            node.else_body = _optimize_node(node.else_body)
        return node
    if isinstance(node, (While, For)):
        node.body = _optimize_node(node.body)
        return node
    return node


def _merge_items(items: list) -> Sequence:
    """Объединить подряд идущие однотипные простые операторы в список."""
    merged: list = []
    for raw in items:
        item = _optimize_node(raw)
        if merged and _can_merge(merged[-1], item):
            merged[-1] = _combine(merged[-1], item)
        else:
            merged.append(item)
    return Sequence(merged)


def _can_merge(first, second) -> bool:
    """Можно ли объединить два узла в один."""
    return type(first) is type(second) and isinstance(first, _MERGEABLE)


def _combine(first, second):
    """Создать узел того же типа с текстом, склеенным в новую строку."""
    text = first.text
    if text and second.text:
        text = f"{text}\n{second.text}"
    else:
        text = text or second.text
    return type(first)(text=text)
