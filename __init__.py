"""Zest: a programming language that is easy to read, write and learn."""

__version__ = "1.0.0"

from .errors import ZestError, ZestRuntimeError, ZestSyntaxError, format_error  # noqa: E402
from .interpreter import Interpreter  # noqa: E402
from .parser import parse  # noqa: E402

__all__ = ["Interpreter", "parse", "ZestError", "ZestSyntaxError", "ZestRuntimeError",
           "format_error", "__version__"]
