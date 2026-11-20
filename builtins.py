"""The functions that come with Zest."""

from __future__ import annotations

import math
import os
import re
import time
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, localcontext
from typing import Any, Dict, List

from .errors import QuitProgram, ZestRuntimeError
from .values import (Builtin, check_key, count_between, describe, display, is_number, kind,
                     range_size, show, to_position, values_equal)

BUILTINS: Dict[str, Builtin] = {}
MAX_LIST = 10_000_000
_ORDINAL = ["first", "second", "third"]
_NUMBER_TEXT = re.compile(r"^\s*[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\s*$")


def builtin(name: str, usage: str, doc: str, min_args: int, max_args: int):
    def register(fn):
        BUILTINS[name] = Builtin(name, fn, min_args, max_args, usage, doc)
        return fn
    return register


def _fail(message: str, hint: str = None) -> ZestRuntimeError:
    return ZestRuntimeError(message, hint=hint)


def _number(fname: str, value: Any, index: int = 0) -> Any:
    if not is_number(value):
        raise _fail(f"{fname}() needs the {_ORDINAL[index]} value to be a number, but got {describe(value)}.")
    return value


def _whole(fname: str, value: Any, index: int = 0) -> int:
    _number(fname, value, index)
    if isinstance(value, float) and not value.is_integer():
        raise _fail(f"{fname}() needs the {_ORDINAL[index]} value to be a whole number, but got {describe(value)}.")
    return int(value)


def _text(fname: str, value: Any, index: int = 0) -> str:
    if not isinstance(value, str):
        raise _fail(f"{fname}() needs the {_ORDINAL[index]} value to be text, but got {describe(value)}.")
    return value


def _list(fname: str, value: Any, index: int = 0) -> list:
    if not isinstance(value, list):
        raise _fail(f"{fname}() needs the {_ORDINAL[index]} value to be a list, but got {describe(value)}.")
    return value


def _map(fname: str, value: Any, index: int = 0) -> dict:
    if not isinstance(value, dict):
        raise _fail(f"{fname}() needs the {_ORDINAL[index]} value to be a map, but got {describe(value)}.")
    return value


# ---- text and numbers in and out -------------------------------------------

@builtin("text", "text(value)", "Turn any value into text.", 1, 1)
def _to_text(ctx, value):
    return display(value)


@builtin("number", "number(value)", "Turn text such as \"42\" into a number.", 1, 1)
def _to_number(ctx, value):
    if is_number(value):
        return value
    if isinstance(value, str) and _NUMBER_TEXT.match(value):
        stripped = value.strip()
        return float(stripped) if re.search(r"[.eE]", stripped) else int(stripped)
    raise _fail(f"I can't turn {describe(value)} into a number.",
                hint="Text must look like a number, for example \"42\" or \"3.5\".")


@builtin("kind", "kind(value)", "The kind of a value: number, text, boolean, list, map, function or nothing.", 1, 1)
def _kind(ctx, value):
    return kind(value)


@builtin("ask", "ask(question)", "Show a question, wait for the person to type, and give back what they typed as text.", 0, 1)
def _ask(ctx, question=""):
    prompt = display(question)
    if prompt:
        ctx.write(prompt)
        ctx.flush()
    line = ctx.read_line()
    if line == "":
        error = _fail("ask() wanted an answer, but there is no more input.",
                      hint="If the input comes from a file or a pipe, make sure it has enough lines.")
        error.catchable = False  # otherwise a loop that keeps asking could never end
        raise error
    return line.rstrip("\r\n")


# ---- lists, maps and text --------------------------------------------------

@builtin("length", "length(thing)", "How many characters in text, items in a list, or entries in a map.", 1, 1)
def _length(ctx, thing):
    if isinstance(thing, (str, list, dict)):
        return len(thing)
    raise _fail(f"length() works on text, lists and maps, but got {describe(thing)}.")


@builtin("add", "add(list, item)", "Put an item at the end of a list.", 2, 2)
def _add(ctx, items, item):
    _list("add", items).append(item)


@builtin("insert", "insert(list, position, item)", "Put an item into a list at a position (1 is the front).", 3, 3)
def _insert(ctx, items, position, item):
    _list("insert", items)
    where = _whole("insert", position, 1)
    if where == 0 or where > len(items) + 1 or where < -(len(items) + 1):
        raise _fail(f"Can't insert at position {where}: the list has {len(items)} items.",
                    hint="Use 1 to put it first, or the length plus 1 (or -1) to put it last.")
    items.insert(where - 1 if where > 0 else len(items) + where + 1, item)


@builtin("remove", "remove(thing, where)", "Take an item out of a list (by position) or a map (by key), and give it back.", 2, 2)
def _remove(ctx, thing, where):
    if isinstance(thing, list):
        return thing.pop(to_position(where, len(thing)))
    if isinstance(thing, dict):
        key = check_key(where)
        if key not in thing:
            raise _fail(f"The map has no key {show(key)}.")
        return thing.pop(key)
    raise _fail(f"remove() works on lists and maps, but got {describe(thing)}.")


@builtin("keys", "keys(map)", "A list of the keys in a map.", 1, 1)
def _keys(ctx, table):
    return list(_map("keys", table))


@builtin("values", "values(map)", "A list of the values in a map.", 1, 1)
def _values(ctx, table):
    return list(_map("values", table).values())


@builtin("copy", "copy(thing)", "Make a separate copy of a list or map.", 1, 1)
def _copy(ctx, thing):
    if isinstance(thing, list):
        return list(thing)
    if isinstance(thing, dict):
        return dict(thing)
    return thing


@builtin("sorted", "sorted(list)", "A new list with the items in order (all numbers or all text).", 1, 1)
def _sorted(ctx, items):
    _list("sorted", items)
    if all(is_number(x) for x in items) or all(isinstance(x, str) for x in items):
        return sorted(items)
    raise _fail("sorted() needs a list of only numbers or only text.")


@builtin("reversed", "reversed(thing)", "A new list, or text, in the opposite order.", 1, 1)
def _reversed(ctx, thing):
    if isinstance(thing, list):
        return thing[::-1]
    if isinstance(thing, str):
        return thing[::-1]
    raise _fail(f"reversed() works on lists and text, but got {describe(thing)}.")


@builtin("range", "range(from, to)  or  range(from, to, step)",
         "A list of numbers from one number to another, both included. Use a negative step to count down.", 2, 3)
def _range(ctx, start, stop, step=1):
    _number("range", start, 0)
    _number("range", stop, 1)
    _number("range", step, 2)
    for value in (start, stop, step):
        if isinstance(value, float) and not math.isfinite(value):
            raise _fail("range() can't work with infinity or not-a-number.")
    if step == 0:
        raise _fail("The step of range() can't be 0.")
    size = range_size(start, stop, step)
    if size > MAX_LIST:
        raise _fail(f"That range would have {size:,} numbers, which is too many for one list.",
                    hint="Use a loop instead: for each i in 1 to 1000000")
    return list(count_between(start, stop, step))


@builtin("slice", "slice(thing, from, to)", "Part of a list or text, from one position to another, both included.", 3, 3)
def _slice(ctx, thing, first, last):
    if not isinstance(thing, (list, str)):
        raise _fail(f"slice() works on lists and text, but got {describe(thing)}.")
    size = len(thing)
    a, b = _whole("slice", first, 1), _whole("slice", last, 2)
    a = a + size + 1 if a < 0 else a
    b = b + size + 1 if b < 0 else b
    a, b = max(a, 1), min(b, size)
    return thing[a - 1:b] if a <= b else thing[0:0]


@builtin("find", "find(thing, item)", "The position of an item in a list, or of a piece of text in text. 0 means not found.", 2, 2)
def _find(ctx, thing, item):
    if isinstance(thing, str):
        return thing.find(_text("find", item, 1)) + 1
    if isinstance(thing, list):
        for position, candidate in enumerate(thing, 1):
            if values_equal(candidate, item):
                return position
        return 0
    raise _fail(f"find() works on text and lists, but got {describe(thing)}.")


@builtin("split", "split(text)  or  split(text, separator)", "Cut text into a list of pieces. With no separator it cuts at spaces.", 1, 2)
def _split(ctx, text, separator=None):
    _text("split", text)
    if separator is None:
        return text.split()
    if _text("split", separator, 1) == "":
        raise _fail("The separator in split() can't be empty.")
    return text.split(separator)


@builtin("join", "join(list)  or  join(list, separator)", "Glue the items of a list into one text.", 1, 2)
def _join(ctx, items, separator=""):
    return _text("join", separator, 1).join(display(x) for x in _list("join", items))


@builtin("replace", "replace(text, old, new)", "Swap every old piece of text for a new one.", 3, 3)
def _replace(ctx, text, old, new):
    if _text("replace", old, 1) == "":
        raise _fail("The text to replace can't be empty.")
    return _text("replace", text).replace(old, _text("replace", new, 2))


@builtin("upper", "upper(text)", "The text in CAPITAL letters.", 1, 1)
def _upper(ctx, text):
    return _text("upper", text).upper()


@builtin("lower", "lower(text)", "The text in small letters.", 1, 1)
def _lower(ctx, text):
    return _text("lower", text).lower()


@builtin("trim", "trim(text)", "The text without spaces at the start and end.", 1, 1)
def _trim(ctx, text):
    return _text("trim", text).strip()


@builtin("starts_with", "starts_with(text, start)", "True if the text begins with the given piece.", 2, 2)
def _starts_with(ctx, text, start):
    return _text("starts_with", text).startswith(_text("starts_with", start, 1))


@builtin("ends_with", "ends_with(text, end)", "True if the text finishes with the given piece.", 2, 2)
def _ends_with(ctx, text, end):
    return _text("ends_with", text).endswith(_text("ends_with", end, 1))


# ---- maths -----------------------------------------------------------------

@builtin("abs", "abs(number)", "The number without its minus sign.", 1, 1)
def _abs(ctx, value):
    return abs(_number("abs", value))


def round_half_up(value: Any, places: int) -> Any:
    """Round the way people expect: 2.5 becomes 3 (not 2)."""
    if isinstance(value, int):
        return value
    if math.isinf(value) or math.isnan(value):
        raise _fail("I can't round infinity or not-a-number.")
    with localcontext() as context:
        context.prec = 400
        try:
            rounded = Decimal(repr(value)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
        except InvalidOperation:
            raise _fail("That number is too big to round.")
    return int(rounded) if places == 0 else float(rounded)


@builtin("round", "round(number)  or  round(number, places)", "Round to the nearest whole number, or to some decimal places. Halves round up.", 1, 2)
def _round(ctx, value, places=0):
    _number("round", value)
    digits = _whole("round", places, 1)
    if digits < 0 or digits > 15:
        raise _fail("round() can keep between 0 and 15 decimal places.")
    return round_half_up(value, digits)


def _check_finite(fname: str, value: Any) -> None:
    if isinstance(value, float) and (math.isinf(value) or math.isnan(value)):
        raise _fail(f"{fname}() can't work with infinity or not-a-number.")


@builtin("floor", "floor(number)", "Round down to a whole number.", 1, 1)
def _floor(ctx, value):
    _check_finite("floor", _number("floor", value))
    return math.floor(value)


@builtin("ceiling", "ceiling(number)", "Round up to a whole number.", 1, 1)
def _ceiling(ctx, value):
    _check_finite("ceiling", _number("ceiling", value))
    return math.ceil(value)


@builtin("sqrt", "sqrt(number)", "The square root of a number.", 1, 1)
def _sqrt(ctx, value):
    _number("sqrt", value)
    if value < 0:
        raise _fail("I can't take the square root of a negative number.")
    return math.sqrt(value)


def _items_for(fname: str, args: tuple) -> List[Any]:
    items = list(args[0]) if len(args) == 1 and isinstance(args[0], list) else list(args)
    if not items:
        raise _fail(f"{fname}() needs at least one value.")
    if not (all(is_number(x) for x in items) or all(isinstance(x, str) for x in items)):
        raise _fail(f"{fname}() needs values that are all numbers or all text.")
    return items


@builtin("min", "min(list)  or  min(a, b, ...)", "The smallest value.", 1, 1000)
def _min(ctx, *args):
    return min(_items_for("min", args))


@builtin("max", "max(list)  or  max(a, b, ...)", "The biggest value.", 1, 1000)
def _max(ctx, *args):
    return max(_items_for("max", args))


@builtin("sum", "sum(list)", "Add up all the numbers in a list.", 1, 1)
def _sum(ctx, items):
    for x in _list("sum", items):
        if not is_number(x):
            raise _fail(f"sum() needs a list of numbers, but it contains {describe(x)}.")
    return sum(items)


@builtin("random", "random()  or  random(from, to)", "A random decimal between 0 and 1, or a random whole number from one number to another (both included).", 0, 2)
def _random(ctx, *args):
    if len(args) == 0:
        return ctx.rng.random()
    if len(args) == 1:
        raise _fail("random() needs no values, or two: random(1, 6).")
    low, high = _whole("random", args[0], 0), _whole("random", args[1], 1)
    if low > high:
        raise _fail(f"random() needs the first number to be the smaller one, but got {low} and {high}.")
    return ctx.rng.randint(low, high)


@builtin("pick", "pick(list)", "A random item from a list.", 1, 1)
def _pick(ctx, items):
    if not _list("pick", items):
        raise _fail("pick() can't choose from an empty list.")
    return ctx.rng.choice(items)


@builtin("seed", "seed(number)", "Make random numbers repeat the same way every run.", 1, 1)
def _seed(ctx, value):
    ctx.rng.seed(_whole("seed", value))


# ---- time, files, quitting -------------------------------------------------

@builtin("now", "now()", "The current time, as the number of seconds since 1970.", 0, 0)
def _now(ctx):
    return time.time()


@builtin("wait", "wait(seconds)", "Pause the program for some seconds.", 1, 1)
def _wait(ctx, seconds):
    if _number("wait", seconds) < 0:
        raise _fail("wait() can't pause for a negative time.")
    time.sleep(min(seconds, 3600))


@builtin("read_file", "read_file(path)", "All the text inside a file.", 1, 1)
def _read_file(ctx, path):
    try:
        with open(_text("read_file", path), encoding="utf-8") as handle:
            return handle.read()
    except FileNotFoundError:
        raise _fail(f"I couldn't find the file {show(path)}.")
    except (OSError, UnicodeDecodeError) as error:
        raise _fail(f"I couldn't read the file {show(path)}: {error}")


@builtin("write_file", "write_file(path, text)", "Save text into a file (replacing what was there).", 2, 2)
def _write_file(ctx, path, text):
    name = _text("write_file", path)
    content = _text("write_file", text, 1)  # check both values first, so a bad call never empties a file
    try:
        with open(name, "w", encoding="utf-8") as handle:
            handle.write(content)
    except OSError as error:
        raise _fail(f"I couldn't write the file {show(path)}: {error}")


@builtin("file_exists", "file_exists(path)", "True if a file or folder with that name exists.", 1, 1)
def _file_exists(ctx, path):
    return os.path.exists(_text("file_exists", path))


@builtin("quit", "quit()  or  quit(code)", "Stop the program right now.", 0, 1)
def _quit(ctx, code=0):
    raise QuitProgram(_whole("quit", code))
