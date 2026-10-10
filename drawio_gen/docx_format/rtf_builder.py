from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatter import Formatter
from pygments.util import ClassNotFound


def _parse_style_def(style_def: str) -> tuple[str | None, bool, bool]:
    color: str | None = None
    bold = False
    italic = False
    if not style_def:
        return None, False, False
    tokens = style_def.strip().split()
    for tok in tokens:
        if tok.startswith("#"):
            color = tok.lstrip("#")
        elif tok == "bold":
            bold = True
        elif tok == "nobold":
            bold = False
        elif tok == "italic":
            italic = True
        elif tok == "noitalic":
            italic = False
    return color, bold, italic


class RtfFormatter(Formatter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._color_table: dict[str, int] = {}
        self._next_color = 1
        self._buf: list[str] = []
        self._group_open = False
        self._current_fg: int | None = None
        self._current_bold = False
        self._current_italic = False

    def _get_color_index(self, hex_str: str) -> int | None:
        if not hex_str:
            return None
        if hex_str not in self._color_table:
            self._color_table[hex_str] = self._next_color
            self._next_color += 1
        return self._color_table[hex_str]

    def _close_formatting_group(self):
        if self._group_open:
            self._buf.append("}")
            self._group_open = False

    def _update_formatting(self, fg_idx: int | None, bold: bool, italic: bool):
        if (fg_idx == self._current_fg and bold == self._current_bold and italic == self._current_italic):
            return
        self._close_formatting_group()
        self._buf.append("{")
        parts = []
        if fg_idx is not None:
            parts.append(f"\\cf{fg_idx}")
        if bold:
            parts.append("\\b")
        if italic:
            parts.append("\\i")
        parts.append("\\f0")
        parts.append("\\fs20")
        self._buf.append(" ".join(parts) + " ")
        self._group_open = True
        self._current_fg = fg_idx
        self._current_bold = bold
        self._current_italic = italic

    def format(self, tokensource, outfile):
        self._buf = []
        self._group_open = False
        self._current_fg = None
        self._current_bold = False
        self._current_italic = False

        for ttype, value in tokensource:
            if not value:
                continue
            style_def = self.style.styles.get(ttype, "")
            color_hex, bold, italic = _parse_style_def(style_def)
            fg_idx = self._get_color_index(color_hex) if color_hex else None

            self._update_formatting(fg_idx, bold, italic)

            escaped = (
                value.replace("\\", "\\\\")
                .replace("{", "\\{")
                .replace("}", "\\}")
                .replace("\n", "\\line\n")
            )
            self._buf.append(escaped)

        self._close_formatting_group()
        outfile.write(self._make_rtf())

    def _make_rtf(self) -> str:
        colortbl = "{\\colortbl;\\red0\\green0\\blue0;"
        for hex_str in sorted(self._color_table.keys()):
            r = int(hex_str[0:2], 16)
            g = int(hex_str[2:4], 16)
            b = int(hex_str[4:6], 16)
            colortbl += f"\\red{r}\\green{g}\\blue{b};"
        colortbl += "}"

        fonttbl = "{\\fonttbl{\\f0\\fmodern\\fcharset0 Consolas;}}"

        header = (
            "{\\rtf1\\ansi\\deff0"
            f"{fonttbl}"
            f"{colortbl}"
            "\\sectd\\sbknone"
        )
        body = "\\pard\\s0" + "".join(self._buf) + "\\par"
        return header + body + "}"


def build_rtf(code: str, language: str = "auto") -> str:
    if language and language != "auto":
        try:
            lexer = get_lexer_by_name(language, stripall=False)
        except ClassNotFound:
            lexer = guess_lexer(code)
    else:
        lexer = guess_lexer(code)

    formatter = RtfFormatter(style="default")
    rtf = highlight(code, lexer, formatter)
    return rtf


__all__ = ["build_rtf"]