"""Парсер C#: tree-sitter → IR.

Реализует :class:`parsers.base.LanguageParser` для языка C#. Разбор дерева
выполняется грамматикой ``tree-sitter-c-sharp`` из пакета
``tree-sitter-language-pack``. Семантика узлов та же, что и у Python-парсера:
каждый метод — отдельная страница, ``Main`` — главная страница.
"""

from __future__ import annotations

from functools import lru_cache

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

#: Методы/функции, которые считаются операциями ввода/вывода .NET.
_INPUT_MEMBERS = {"ReadLine", "Read"}
_OUTPUT_MEMBERS = {"WriteLine", "Write"}


@lru_cache(maxsize=1)
def _ts_parser():
    """Ленивo загрузить tree-sitter-парсер C# (грамматика из language-pack).

    Returns:
        Готовый :class:`tree_sitter.Parser`.

    Raises:
        ParseError: Если грамматику не удалось загрузить.
    """
    try:
        from tree_sitter_language_pack import get_parser

        return get_parser("csharp")
    except Exception as exc:  # noqa: BLE001 - сообщаем нейтральной ошибкой
        raise ParseError(f"Не удалось загрузить грамматику C#: {exc}") from exc


class CSharpParser(LanguageParser):
    """Разбирает C#-код в :class:`ir.Page`."""

    id = "csharp"
    display_name = "C#"

    def detect(self, source: str) -> int:
        """Эвристическая оценка принадлежности кода к C#."""
        score = 0
        for marker in ("using ", "namespace ", "Console.", "public ", "private ",
                       "static ", "void ", "=>", " string ", " int "):
            if marker in source:
                score += 2
        for marker in ("def ", "import ", "elif "):
            if marker in source:
                score -= 2
        if "{" in source and ";" in source:
            score += 1
        return max(0, score)

    def parse(self, source: str) -> list[Page]:
        """Разобрать C#-код в список страниц.

        Args:
            source: Исходный текст на C#.

        Returns:
            Список страниц: ``main`` (метод ``Main``) и по одной на метод.

        Raises:
            ParseError: При синтаксической ошибке (с указанием позиции).
        """
        tree = _ts_parser().parse(source.encode("utf-8"))
        if tree.root_node.has_error:
            raise self._error(tree.root_node, source)
        return _Walker(source, tree).pages()

    @staticmethod
    def _error(root, source: str) -> ParseError:
        bad = _first_error(root)
        if bad is None:
            return ParseError("Синтаксическая ошибка")
        row, col = bad.start_point
        return ParseError("Синтаксическая ошибка", row + 1, col + 1)


def _first_error(node):
    """Найти первый узел ``ERROR``/``MISSING`` в дереве."""
    if node.type == "ERROR" or node.is_missing:
        return node
    for child in node.children:
        found = _first_error(child)
        if found is not None:
            return found
    return None


def _is_pattern(node) -> bool:
    """Является ли узел case-паттерном (``*_pattern`` или ``discard``)."""
    return node.type.endswith("_pattern") or node.type == "discard"


class _Walker:
    """Рекурсивный обход дерева C# и построение IR."""

    def __init__(self, source: str, tree) -> None:
        self._raw = source.encode("utf-8")
        self._tree = tree

    def text(self, node) -> str:
        """Вернуть исходный текст узла."""
        if node is None:
            return ""
        return self._raw[node.start_byte:node.end_byte].decode("utf-8").strip()

    # --- страницы --------------------------------------------------------
    def pages(self) -> list[Page]:
        methods: list = []
        self._collect_methods(self._tree.root_node, methods)

        top_stmts: list = []
        for child in self._tree.root_node.named_children:
            if child.type == "global_statement":
                for inner in child.named_children:
                    top_stmts.extend(self._statement(inner))

        main_page: Page | None = (
            Page("main", Sequence(top_stmts), "Начало") if top_stmts else None
        )
        others: list[Page] = []
        used = {"main"}
        for method in methods:
            name_node = method.child_by_field_name("name")
            name = self.text(name_node) or "anon"
            body = self._method_body(method)
            nodes = self._statements(body)
            if name == "Main" and main_page is None:
                main_page = Page("main", Sequence(nodes), "Начало", func_name="Main")
                continue
            page_name = name
            counter = 2
            while page_name in used:
                page_name = f"{name}_{counter}"
                counter += 1
            used.add(page_name)
            others.append(
                Page(page_name, Sequence(nodes), f"Начало {name}", func_name=name)
            )

        if main_page is None:
            main_page = Page("main", Sequence([]), "Начало")
        return [main_page, *others]

    def _collect_methods(self, node, acc: list) -> None:
        if node.type in ("method_declaration", "local_function_statement"):
            acc.append(node)
        for child in node.children:
            self._collect_methods(child, acc)

    def _method_body(self, method):
        body = method.child_by_field_name("body")
        if body is not None:
            return body
        for child in method.named_children:
            if child.type in ("block", "arrow_expression_clause"):
                return child
        return None

    # --- операторы -------------------------------------------------------
    def _statements(self, node) -> list:
        if node is None:
            return []
        if node.type == "block":
            result: list = []
            for child in node.named_children:
                result.extend(self._statement(child))
            return result
        if node.type == "arrow_expression_clause":
            return self._statement(node)
        return self._statement(node)

    def _statement(self, node) -> list:
        handler = {
            "block": self._st_block,
            "if_statement": self._st_if,
            "while_statement": self._st_while,
            "do_statement": self._st_do,
            "for_statement": self._st_for,
            "foreach_statement": self._st_foreach,
            "switch_statement": self._st_switch,
            "try_statement": self._st_try,
            "return_statement": self._st_return,
            "break_statement": lambda n: [Break()],
            "continue_statement": lambda n: [Continue()],
            "local_declaration_statement": self._st_local,
            "expression_statement": self._st_expr,
            "throw_statement": lambda n: [Other(self.text(n))],
        }.get(node.type)
        if handler is not None:
            return handler(node)
        return [Other(self.text(node))]

    def _st_block(self, node) -> list:
        return self._statements(node)

    def _st_if(self, node) -> list:
        condition = self.text(node.child_by_field_name("condition"))
        body = Sequence(self._statements(node.child_by_field_name("consequence")))
        else_body = None
        alternative = node.child_by_field_name("alternative")
        if alternative is not None:
            if alternative.type == "if_statement":
                else_body = Sequence(self._st_if(alternative))
            else:
                else_body = Sequence(self._statements(alternative))
        return [If(condition, body, else_body)]

    def _st_while(self, node) -> list:
        condition = self.text(node.child_by_field_name("condition"))
        body = Sequence(self._statements(node.child_by_field_name("body")))
        return [While(condition, body)]

    def _st_do(self, node) -> list:
        body_node = node.child_by_field_name("body")
        condition = self.text(node.child_by_field_name("condition"))
        if condition:
            condition = f"do … while ({condition})"
        return [While(condition, Sequence(self._statements(body_node)))]

    def _st_for(self, node) -> list:
        body = Sequence(self._statements(node.child_by_field_name("body")))
        return [For(self._head(node), body)]

    def _st_foreach(self, node) -> list:
        body = Sequence(self._statements(node.child_by_field_name("body")))
        return [For(self._head(node), body)]

    def _head(self, node) -> str:
        """Текст заголовка до конца первых сбалансированных скобок."""
        full = self.text(node)
        start = full.find("(")
        if start == -1:
            return full
        depth = 0
        for i in range(start, len(full)):
            if full[i] == "(":
                depth += 1
            elif full[i] == ")":
                depth -= 1
                if depth == 0:
                    return full[: i + 1].strip()
        return full

    def _st_switch(self, node) -> list:
        value = ""
        body = None
        for child in node.named_children:
            if child.type == "switch_body":
                body = child
            elif not value:
                value = self.text(child)
        if body is None:
            return [Other(self.text(node))]

        cases: list[tuple[str, Sequence]] = []
        default_body: Sequence | None = None
        pending: list[str] = []
        for section in body.named_children:
            if section.type != "switch_section":
                continue
            is_default = any(c.type == "default" for c in section.children)
            patterns = [c for c in section.named_children if _is_pattern(c)]
            guard = next(
                (c for c in section.named_children if c.type == "when_clause"), None
            )
            labels = [self._case_condition(value, pat, guard) for pat in patterns]

            stmts: list = []
            terminated = False
            for child in section.named_children:
                if child.type == "when_clause" or _is_pattern(child):
                    continue
                if child.type == "break_statement":
                    terminated = True
                    continue
                stmts.extend(self._statement(child))

            if is_default:
                default_body = Sequence(stmts)
                for label in pending:
                    cases.append((label, Sequence(stmts)))
                pending.clear()
                continue
            if labels and not stmts and not terminated:
                pending.extend(labels)
                continue
            for label in (*pending, *labels):
                cases.append((label, Sequence(stmts)))
            pending.clear()

        for label in pending:
            cases.append((label, Sequence([])))

        if not cases:
            return list(default_body.items) if default_body else [Other(self.text(node))]

        else_body = default_body
        for condition, case_body in reversed(cases):
            else_body = Sequence([If(condition, case_body, else_body)])
        return list(else_body.items)

    def _case_condition(self, value: str, pattern, guard) -> str:
        pattern_text = self.text(pattern)
        if pattern.type == "constant_pattern":
            condition = f"{value} == {pattern_text}"
        else:
            condition = f"{value} is {pattern_text}"
        if guard is not None:
            guard_text = self.text(guard)
            if guard_text.startswith("when"):
                guard_text = guard_text[len("when"):].strip()
            condition = f"{condition} when {guard_text}"
        return condition

    def _st_try(self, node) -> list:
        nodes: list = list(self._statements(node.child_by_field_name("body")))
        for child in node.named_children:
            if child.type in ("catch_clause", "finally_clause"):
                nodes.append(Other(self.text(child)))
        return nodes

    def _st_return(self, node) -> list:
        return [Return(self.text(node))]

    def _st_local(self, node) -> list:
        if self._contains_console(node, _INPUT_MEMBERS):
            return [Input(self.text(node))]
        if self._contains_console(node, _OUTPUT_MEMBERS):
            return [Output(self.text(node))]
        return [Process(self.text(node))]

    def _st_expr(self, node) -> list:
        if node.named_child_count == 1:
            child = node.named_children[0]
            if child.type == "invocation_expression":
                return [self._invocation(child)]
            if child.type == "assignment_expression":
                if self._contains_console(child, _INPUT_MEMBERS):
                    return [Input(self.text(node))]
                if self._contains_console(child, _OUTPUT_MEMBERS):
                    return [Output(self.text(node))]
        return [Process(self.text(node))]

    def _invocation(self, node):
        if self._is_console(node, _OUTPUT_MEMBERS):
            return Output(self.text(node))
        if self._is_console(node, _INPUT_MEMBERS):
            return Input(self.text(node))
        return FuncCall(self.text(node), self._call_name(node))

    def _is_console(self, invocation, members: set[str]) -> bool:
        function = invocation.child_by_field_name("function")
        if function is None or function.type != "member_access_expression":
            return False
        expression = function.child_by_field_name("expression")
        name = function.child_by_field_name("name")
        return self.text(expression) == "Console" and self.text(name) in members

    def _contains_console(self, node, members: set[str]) -> bool:
        if node.type == "invocation_expression" and self._is_console(node, members):
            return True
        return any(self._contains_console(child, members) for child in node.children)

    def _call_name(self, invocation) -> str:
        function = invocation.child_by_field_name("function")
        if function is None:
            return ""
        if function.type == "identifier":
            return self.text(function)
        if function.type == "member_access_expression":
            return self.text(function.child_by_field_name("name"))
        return ""
