"""Turn Zest source text into tokens."""

from __future__ import annotations

import re
from typing import List, NamedTuple, Optional, Tuple

from .errors import ZestSyntaxError

KEYWORDS = frozenset({
    "say", "to", "give", "if", "else", "end", "repeat", "while", "for",
    "stop", "skip", "and", "or", "not", "true", "false", "nothing",
    "try", "catch", "fail", "use", "in",
})


class Token(NamedTuple):
    kind: str      # number, text, name, keyword, op, newline, eof
    value: object
    line: int
    col: int
    length: int


class Interp(NamedTuple):
    """A {piece of code} inside a text, kept as source until the parser reads it."""

    source: str
    line: int
    col: int


_NUMBER = re.compile(r"\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")
_WORD = re.compile(r"[^\W\d]\w*")
_TWO = {"==", "!=", "<=", ">=", "+=", "-=", "*=", "/="}
_ONE = set("+-*/%^=<>()[]{},:.")
_OPEN = {"(": ")", "[": "]", "{": "}"}
_CLOSE = {")": "(", "]": "[", "}": "{"}
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "'": "'", "{": "{", "}": "}"}
_CHAR_HINTS = {
    ";": "Zest does not need semicolons. Just end the line.",
    "!": "To say 'not', write: not something. To say 'different', write: a != b.",
    "&": "To combine two conditions, write: a and b",
    "|": "To allow either condition, write: a or b",
    "$": "Names are plain words. Write price, not $price.",
    "@": "Zest has no '@' symbol.",
    "?": "Zest has no '?' symbol. Use if ... else ... end.",
    "~": "Zest has no '~' symbol.",
    "`": "Use normal quotes for text: \"like this\".",
    "\\": "A backslash only works inside text, like \"line one\\nline two\".",
}


class Lexer:
    def __init__(self, source: str, line: int = 1, col: int = 1, filename: Optional[str] = None) -> None:
        self.src = source[1:] if source.startswith("\ufeff") else source
        self.i = 0
        self.line = line
        self.col = col
        self.filename = filename
        self.tokens: List[Token] = []
        self.brackets: List[Tuple[str, int, int]] = []

    # ---- helpers ----------------------------------------------------------

    def _error(self, message: str, line: int, col: int, length: int = 1,
               hint: Optional[str] = None, at_end: bool = False) -> ZestSyntaxError:
        return ZestSyntaxError(message, line, col, hint, self.filename, length, at_end)

    def _step(self, count: int = 1) -> None:
        self.i += count
        self.col += count

    def _add(self, kind: str, value: object, line: int, col: int, length: int) -> None:
        self.tokens.append(Token(kind, value, line, col, length))

    # ---- main loop --------------------------------------------------------

    def tokenize(self) -> List[Token]:
        src = self.src
        size = len(src)
        while self.i < size:
            char = src[self.i]
            if char in " \t\r":
                self._step()
            elif char == "\n":
                if not self.brackets and self.tokens and self.tokens[-1].kind != "newline":
                    self._add("newline", "\n", self.line, self.col, 1)
                self.i += 1
                self.line += 1
                self.col = 1
            elif char == "#":
                while self.i < size and src[self.i] != "\n":
                    self._step()
            elif char in "0123456789":
                self._number()
            elif char in "\"'":
                self._text()
            elif _WORD.match(src, self.i):
                self._word()
            else:
                self._symbol()
        if self.brackets:
            opener, line, col = self.brackets[-1]
            raise self._error(f"This '{opener}' was never closed.", line, col,
                              hint=f"Add a '{_OPEN[opener]}' where it ends.", at_end=True)
        if self.tokens and self.tokens[-1].kind != "newline":
            self._add("newline", "\n", self.line, self.col, 1)
        self._add("eof", None, self.line, self.col, 0)
        return self.tokens

    # ---- pieces -----------------------------------------------------------

    def _number(self) -> None:
        match = _NUMBER.match(self.src, self.i)
        assert match is not None
        text = match.group()
        end = match.end()
        if end < len(self.src) and (self.src[end].isalpha() or self.src[end] == "_"):
            raise self._error("A number can't be followed by letters.", self.line, self.col, len(text) + 1,
                              hint="To multiply, write: 3 * x")
        is_float = "." in text or "e" in text or "E" in text
        self._add("number", float(text) if is_float else int(text), self.line, self.col, len(text))
        self._step(len(text))

    def _word(self) -> None:
        match = _WORD.match(self.src, self.i)
        assert match is not None
        word = match.group()
        kind = "keyword" if word in KEYWORDS else "name"
        self._add(kind, word, self.line, self.col, len(word))
        self._step(len(word))

    def _symbol(self) -> None:
        src, i = self.src, self.i
        char = src[i]
        pair = src[i:i + 2]
        if pair == "&&":
            raise self._error("Zest uses the word 'and', not '&&'.", self.line, self.col, 2, "Write: a and b")
        if pair == "||":
            raise self._error("Zest uses the word 'or', not '||'.", self.line, self.col, 2, "Write: a or b")
        if pair == "++":
            raise self._error("Zest has no '++'.", self.line, self.col, 2, "To add one, write: x += 1")
        if pair in _TWO:
            self._add("op", pair, self.line, self.col, 2)
            self._step(2)
            return
        if char in _ONE:
            if char in _OPEN:
                self.brackets.append((char, self.line, self.col))
            elif char in _CLOSE:
                if not self.brackets:
                    raise self._error(f"This '{char}' has nothing to close.", self.line, self.col,
                                      hint=f"Remove it, or add the '{_CLOSE[char]}' it belongs to.")
                opener, oline, _ = self.brackets[-1]
                if _CLOSE[char] != opener:
                    raise self._error(f"This '{char}' does not match the '{opener}' on line {oline}.",
                                      self.line, self.col, hint=f"Close the '{opener}' with '{_OPEN[opener]}' first.")
                self.brackets.pop()
            self._add("op", char, self.line, self.col, 1)
            self._step()
            return
        raise self._error(f"I don't know what to do with the character '{char}'.", self.line, self.col,
                          hint=_CHAR_HINTS.get(char))

    def _text(self) -> None:
        src = self.src
        size = len(src)
        quote = src[self.i]
        start_line, start_col = self.line, self.col
        j = self.i + 1
        parts: List[object] = []
        buffer: List[str] = []

        def unfinished(at: int) -> ZestSyntaxError:
            return self._error("This text was never closed.", start_line, start_col, at - self.i,
                               hint=f"Finish it with a matching {quote} on the same line.")

        while True:
            if j >= size or src[j] == "\n":
                raise unfinished(j)
            char = src[j]
            if char == quote:
                j += 1
                break
            if char == "\\":
                if j + 1 >= size or src[j + 1] == "\n":
                    raise unfinished(j + 1)
                escaped = src[j + 1]
                if escaped not in _ESCAPES:
                    raise self._error(f"I don't know the escape '\\{escaped}'.", start_line,
                                      start_col + (j - self.i), 2,
                                      hint="Escapes are \\n (new line), \\t (tab), \\\\ (backslash), \\\" and \\{ .")
                buffer.append(_ESCAPES[escaped])
                j += 2
            elif char == "{":
                end = self._interpolation_end(j, start_line, start_col, unfinished)
                code = src[j + 1:end]
                if not code.strip():
                    raise self._error("There is nothing inside these { }.", start_line,
                                      start_col + (j - self.i), 2,
                                      hint="Put a name or calculation inside, like {name}. For a plain brace, write \\{")
                if buffer:
                    parts.append("".join(buffer))
                    buffer = []
                parts.append(Interp(code, start_line, start_col + (j + 1 - self.i)))
                j = end + 1
            else:
                buffer.append(char)
                j += 1
        if buffer or not parts:
            parts.append("".join(buffer))
        length = j - self.i
        self._add("text", parts, start_line, start_col, length)
        self.i = j
        self.col += length

    def _interpolation_end(self, open_index: int, start_line: int, start_col: int, unfinished) -> int:
        """Find the } that closes the { at open_index, skipping over quoted text inside."""
        src, size = self.src, len(self.src)
        depth = 1
        j = open_index + 1
        while j < size and src[j] != "\n":
            char = src[j]
            if char in "\"'":
                k = j + 1
                while k < size and src[k] != char and src[k] != "\n":
                    k += 2 if src[k] == "\\" else 1
                if k >= size or src[k] != char:
                    raise unfinished(k)
                j = k + 1
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return j
            j += 1
        raise self._error("This '{' was never closed.", start_line, start_col + (open_index - self.i), 1,
                          hint="Add a '}' on the same line, or write \\{ for a plain brace.")
