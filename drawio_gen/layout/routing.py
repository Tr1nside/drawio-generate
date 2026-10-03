"""Маршрутизация рёбер между фигурами."""

from .geometry import Edge, anchor_point, orthogonalize


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
    return orthogonalize([start, *edge.waypoints, end], edge.exit_side)
