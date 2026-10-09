"""Парсер Python: ``ast`` → IR.

Реализует :class:`parsers.base.LanguageParser` для языка Python. Разбор
выполняется стандартным модулем :mod:`ast`, поэтому дополнительных
зависимостей не требуется.
"""

from __future__ import annotations

import ast

from ..ir import (
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
from .base import LanguageParser, ParseError


class PythonParser(LanguageParser):
    """Разбирает Python-код в :class:`ir.Page`.

    Каждая функция ``def`` становится отдельной страницей; код верхнего
    уровня — главной страницей ``main``.
    """

    id = "python"
    display_name = "Python"

    def detect(self, source: str) -> int:
        """Эвристическая оценка принадлежности кода к Python."""
        score = 0
        markers = ("def ", "import ", "class ", "if __name__", "print(", "elif ", "self.")
        for marker in markers:
            if marker in source:
                score += 2
        if "{" in source and ";" in source:
            score -= 1
        return max(0, score)

    def parse(self, source: str) -> list[Page]:
        """Разобрать Python-код в список страниц.

        Args:
            source: Исходный текст на Python.

        Returns:
            Список страниц: ``main`` и по одной на каждую ``def``.

        Raises:
            ParseError: При синтаксической ошибке (с указанием строки).
        """
        try:
            return _Parser(source).parse_pages()
        except SyntaxError as exc:
            raise ParseError(
                f"Синтаксическая ошибка: {exc.msg}", exc.lineno, exc.offset
            ) from exc


class _Parser:
    """Внутренний рекурсивный обход ``ast`` (деталь реализации)."""

    def __init__(self, source: str) -> None:
        self.source = source

    def _seg(self, node: ast.AST) -> str:
        try:
            seg = ast.get_source_segment(self.source, node)
        except Exception:
            seg = None
        return (seg or "").strip()

    @staticmethod
    def _expr(node: ast.AST) -> str:
        try:
            return ast.unparse(node)
        except Exception:
            return ""

    @staticmethod
    def _is_call(node: ast.AST, name: str) -> bool:
        return (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == name
        )

    @staticmethod
    def _call_name(node: ast.AST) -> str:
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            return node.func.id
        return ""

    def _contains_call(self, node: ast.AST, name: str) -> bool:
        return any(self._is_call(n, name) for n in ast.walk(node))

    @staticmethod
    def _is_main_guard(node: ast.If) -> bool:
        test = node.test
        return (
            isinstance(test, ast.Compare)
            and isinstance(test.left, ast.Name)
            and test.left.id == "__name__"
            and len(test.comparators) == 1
            and isinstance(test.comparators[0], ast.Constant)
            and test.comparators[0].value == "__main__"
        )

    def parse_pages(self) -> list[Page]:
        tree = ast.parse(self.source)
        main_body: list = []
        functions: list[ast.FunctionDef] = []
        for stmt in tree.body:
            if isinstance(stmt, ast.FunctionDef):
                functions.append(stmt)
            else:
                main_body.extend(self._parse_stmt(stmt))

        pages = [Page("main", Sequence(main_body), "Начало")]
        used = {"main"}
        for fn in functions:
            name = fn.name
            counter = 2
            while name in used:
                name = f"{fn.name}_{counter}"
                counter += 1
            used.add(name)
            body = Sequence(self._parse_body(fn.body))
            pages.append(Page(name, body, f"Начало {fn.name}", func_name=fn.name))
        return pages

    def _parse_body(self, body: list) -> list:
        nodes: list = []
        for stmt in body:
            nodes.extend(self._parse_stmt(stmt))
        return nodes

    def _parse_stmt(self, stmt: ast.stmt) -> list:
        if isinstance(stmt, ast.Pass):
            return []

        if isinstance(stmt, ast.If):
            if self._is_main_guard(stmt):
                return self._parse_body(stmt.body)
            return [self._parse_if(stmt)]

        if isinstance(stmt, ast.While):
            return [While(self._expr(stmt.test), Sequence(self._parse_body(stmt.body)))]

        if isinstance(stmt, ast.For):
            text = f"for {self._expr(stmt.target)} in {self._expr(stmt.iter)}"
            return [For(text, Sequence(self._parse_body(stmt.body)))]

        if isinstance(stmt, ast.Return):
            return [Return(self._expr(stmt))]

        if isinstance(stmt, ast.Break):
            return [Break()]

        if isinstance(stmt, ast.Continue):
            return [Continue()]

        if isinstance(stmt, ast.Assign):
            return [self._parse_assign(stmt)]

        if isinstance(stmt, ast.AugAssign):
            return [Process(self._expr(stmt))]

        if isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
            return [self._parse_assign(stmt)]

        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            call = stmt.value
            if self._is_call(call, "print"):
                return [Output(self._expr(stmt))]
            if self._is_call(call, "input"):
                return [Input(self._expr(stmt))]
            return [FuncCall(self._expr(stmt), self._call_name(call))]

        if isinstance(stmt, ast.Try):
            result: list = list(self._parse_body(stmt.body))
            catch_nodes: list = []
            for handler in stmt.handlers:
                parts = ["except"]
                if handler.type is not None:
                    parts.append(self._expr(handler.type))
                if handler.name is not None:
                    parts.append(handler.name)
                label = " ".join(parts)
                body = self._parse_body(handler.body)
                if body:
                    catch_nodes.append(Other(f"{label}:"))
                    catch_nodes.extend(body)
                else:
                    catch_nodes.append(Other(label))
            else_body = Sequence(self._parse_body(stmt.orelse)) if stmt.orelse else None
            if catch_nodes:
                result.append(If("exception", Sequence(catch_nodes), else_body))
            elif else_body is not None:
                result.extend(else_body.items)
            if stmt.finalbody:
                result.append(Other("finally:"))
                result.extend(self._parse_body(stmt.finalbody))
            return result

        return [Other(self._seg(stmt))]

    def _parse_assign(self, stmt) -> Process:
        value = stmt.value
        if self._contains_call(value, "input"):
            return Input(self._expr(stmt))
        if self._is_call(value, "print"):
            return Output(self._expr(stmt))
        return Process(self._expr(stmt))

    def _parse_if(self, stmt: ast.If) -> If:
        body = Sequence(self._parse_body(stmt.body))
        else_body = None
        if stmt.orelse:
            if len(stmt.orelse) == 1 and isinstance(stmt.orelse[0], ast.If):
                else_body = Sequence([self._parse_if(stmt.orelse[0])])
            else:
                else_body = Sequence(self._parse_body(stmt.orelse))
        return If(self._expr(stmt.test), body, else_body)


def parse_pages(source: str) -> list[Page]:
    """Удобная функция-обёртка: разобрать Python-код в страницы.

    Args:
        source: Исходный текст на Python.

    Returns:
        Список страниц :class:`ir.Page`.

    Raises:
        ParseError: При синтаксической ошибке.
    """
    return PythonParser().parse(source)
