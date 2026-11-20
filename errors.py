"""Errors that explain themselves.

Every problem Zest reports has a plain-English message, the line it happened
on, a pointer to the exact spot, and (where possible) a hint for fixing it.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple


class ZestError(Exception):
    """Base class for every problem in a Zest program."""

    def __init__(
        self,
        message: str,
        line: Optional[int] = None,
        col: Optional[int] = None,
        hint: Optional[str] = None,
        filename: Optional[str] = None,
        length: int = 1,
        at_end: bool = False,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.line = line
        self.col = col
        self.hint = hint
        self.filename = filename
        self.length = length
        self.at_end = at_end  # the code simply stopped too soon (used by the REPL)
        self.catchable = True  # False for problems that 'try' must not hide
        self.trace: List[Tuple[str, int, Optional[str]]] = []  # (function, call line, call file)


class ZestSyntaxError(ZestError):
    """The code could not be read."""


class ZestRuntimeError(ZestError):
    """The code was read fine, but something went wrong while running it."""


class QuitProgram(Exception):
    """Raised by quit() to stop the program on purpose."""

    def __init__(self, code: int = 0) -> None:
        super().__init__(code)
        self.code = code


def _label(filename: Optional[str]) -> str:
    if filename is None:
        return "your program"
    if filename.startswith("<repl"):
        return "your input"
    return filename


def format_error(error: ZestError, sources: Optional[Dict[str, List[str]]] = None) -> str:
    """Turn an error into the message a person sees."""
    sources = sources or {}
    opener = "Can't read" if isinstance(error, ZestSyntaxError) else "Problem in"
    where = _label(error.filename)
    head = f"{opener} {where}, line {error.line}:" if error.line is not None else f"{opener} {where}:"
    lines = [head, f"  {error.message}"]
    source = sources.get(error.filename) if error.filename else None
    if error.line is not None and source and 1 <= error.line <= len(source):
        number = str(error.line)
        text = source[error.line - 1].replace("\t", " ").rstrip()
        lines += ["", f"  {number} | {text}"]
        if error.col is not None:
            pointer = " " * (error.col - 1) + "^" * max(1, error.length)
            lines.append(f"  {' ' * len(number)} | {pointer}")
        lines.append("")
    if error.hint:
        lines.append(f"  Hint: {error.hint}")
    index = 0
    trace = error.trace
    while index < len(trace):
        name, line, filename = trace[index]
        repeats = 1
        while index + repeats < len(trace) and trace[index + repeats] == trace[index]:
            repeats += 1
        where_called = f"line {line}" if filename is None or filename == error.filename else f"line {line} of {_label(filename)}"
        again = f", {repeats} times in a row" if repeats > 1 else ""
        lines.append(f"  (inside {name}(), called from {where_called}{again})")
        index += repeats
    return "\n".join(lines).rstrip() + "\n"
