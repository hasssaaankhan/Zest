"""Run a Zest program."""

from __future__ import annotations

import difflib
import math
import os
import random
import sys
from typing import Any, Callable, Dict, Iterable, List, Optional, Set

from . import nodes as n
from .builtins import BUILTINS
from .errors import QuitProgram, ZestError, ZestRuntimeError
from .parser import MISTAKES, parse
from .values import (Builtin, Function, check_key, count_between, describe, display, is_number,
                     kind, show, to_position, values_equal)

MAX_DEPTH = 500
MAX_TEXT = 50_000_000
RECURSION_LIMIT = 12_000  # Python frames; one Zest call uses roughly a dozen of them

_VERBS = {"-": "subtract", "*": "multiply", "/": "divide", "%": "find the remainder of", "^": "raise to a power"}

try:  # very long whole numbers should print in full
    sys.set_int_max_str_digits(0)
except AttributeError:
    pass


class _Give(Exception):
    def __init__(self, value: Any) -> None:
        super().__init__()
        self.value = value


class _Stop(Exception):
    pass


class _Skip(Exception):
    pass


class Environment:
    """A place where names live. Functions get their own; blocks share their function's."""

    def __init__(self, parent: Optional["Environment"] = None, builtin: bool = False) -> None:
        self.vars: Dict[str, Any] = {}
        self.parent = parent
        self.builtin = builtin

    def lookup(self, name: str) -> Any:
        env: Optional[Environment] = self
        while env is not None:
            if name in env.vars:
                return env.vars[name]
            env = env.parent
        raise KeyError(name)

    def define(self, name: str, value: Any) -> None:
        self.vars[name] = value

    def assign(self, name: str, value: Any) -> None:
        """Update the nearest existing name, or create it here. Built-ins are never changed."""
        env: Optional[Environment] = self
        while env is not None and not env.builtin:
            if name in env.vars:
                env.vars[name] = value
                return
            env = env.parent
        self.vars[name] = value

    def names(self) -> Set[str]:
        found: Set[str] = set()
        env: Optional[Environment] = self
        while env is not None:
            found.update(env.vars)
            env = env.parent
        return found


class Interpreter:
    def __init__(
        self,
        write: Optional[Callable[[str], Any]] = None,
        read_line: Optional[Callable[[], str]] = None,
        flush: Optional[Callable[[], Any]] = None,
        base_dir: Optional[str] = None,
        max_depth: int = MAX_DEPTH,
    ) -> None:
        sys.setrecursionlimit(max(sys.getrecursionlimit(), RECURSION_LIMIT))
        self.write = write or sys.stdout.write
        self.read_line = read_line or sys.stdin.readline
        self.flush = flush or getattr(sys.stdout, "flush", lambda: None)
        self.base_dir = base_dir or os.getcwd()
        self.max_depth = max_depth
        self.rng = random.Random()
        self.builtins_env = Environment(builtin=True)
        self.builtins_env.vars.update(BUILTINS)
        self.globals = Environment(self.builtins_env)
        self.sources: Dict[str, List[str]] = {}
        self.loaded: Set[str] = set()
        self.current_file: Optional[str] = None
        self.depth = 0
        self._exec = {
            n.Assign: self.exec_assign, n.Say: self.exec_say, n.If: self.exec_if,
            n.While: self.exec_while, n.Repeat: self.exec_repeat, n.ForEach: self.exec_for_each,
            n.ForRange: self.exec_for_range, n.Def: self.exec_def, n.Give: self.exec_give,
            n.Stop: self.exec_stop, n.Skip: self.exec_skip, n.Try: self.exec_try,
            n.Fail: self.exec_fail, n.Use: self.exec_use, n.ExprStmt: self.exec_expr,
        }
        self._eval = {
            n.Literal: self.eval_literal, n.Text: self.eval_text, n.Name: self.eval_name,
            n.ListLit: self.eval_list, n.MapLit: self.eval_map, n.Unary: self.eval_unary,
            n.Binary: self.eval_binary, n.Compare: self.eval_compare, n.Logic: self.eval_logic,
            n.Call: self.eval_call, n.Index: self.eval_index, n.Field: self.eval_field,
        }

    # ---- running programs -------------------------------------------------

    def run_source(self, source: str, filename: str = "<program>") -> None:
        self.sources[filename] = source.splitlines()
        program = parse(source, filename)
        self._run(program, filename)

    def run_file(self, path: str) -> None:
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
        self.loaded.add(os.path.abspath(path))
        self.run_source(source, path)

    def run_snippet(self, source: str, label: str, echo: bool = False) -> None:
        """Run one piece of code from the prompt. With echo, a bare value is shown."""
        self.sources[label] = source.splitlines()
        program = parse(source, label, repl=echo)
        previous = self.current_file
        self.current_file = label
        try:
            for statement in program:
                if echo and isinstance(statement, n.ExprStmt):
                    value = self.eval(statement.expr, self.globals)
                    if value is not None:
                        self.write(show(value) + "\n")
                else:
                    self.exec(statement, self.globals)
        finally:
            self.current_file = previous

    def _run(self, program: List[n.Node], filename: str) -> None:
        previous = self.current_file
        self.current_file = filename
        try:
            self.exec_block(program, self.globals)
        finally:
            self.current_file = previous

    # ---- dispatch ---------------------------------------------------------

    def _locate(self, error: ZestError, node: n.Node) -> None:
        if error.line is None:
            error.line = getattr(node, "line", None) or None
            error.col = getattr(node, "col", None) or None
            word = node if isinstance(node, n.Name) else getattr(node, "callee", None)
            if isinstance(word, n.Name):
                error.length = len(word.name)  # underline the whole name
        if error.filename is None:
            error.filename = self.current_file

    def exec_block(self, statements: Iterable[n.Node], env: Environment) -> None:
        for statement in statements:
            self.exec(statement, env)

    def exec(self, node: n.Node, env: Environment) -> None:
        try:
            self._exec[type(node)](node, env)
        except ZestError as error:
            self._locate(error, node)
            raise

    def eval(self, node: n.Node, env: Environment) -> Any:
        try:
            return self._eval[type(node)](node, env)
        except ZestError as error:
            self._locate(error, node)
            raise

    # ---- checks -----------------------------------------------------------

    def need_boolean(self, value: Any, what: str) -> bool:
        if isinstance(value, bool):
            return value
        raise ZestRuntimeError(f"{what} needs true or false, but this is {describe(value)}.",
                               hint="Use a comparison such as ==, !=, <, > or 'in' to get true or false.")

    def need_numbers(self, op: str, left: Any, right: Any) -> None:
        if not (is_number(left) and is_number(right)):
            raise ZestRuntimeError(
                f"I can only {_VERBS[op]} numbers, but this has {describe(left)} and {describe(right)}.")

    # ---- statements -------------------------------------------------------

    def exec_expr(self, node: n.ExprStmt, env: Environment) -> None:
        self.eval(node.expr, env)

    def exec_say(self, node: n.Say, env: Environment) -> None:
        pieces = [display(self.eval(arg, env)) for arg in node.args]
        self.write(" ".join(pieces) + "\n")

    def exec_assign(self, node: n.Assign, env: Environment) -> None:
        target = node.target
        value = self.eval(node.value, env)
        compound = node.op != "="
        if isinstance(target, n.Name):
            if compound:
                value = self.binary(node.op[0], self.eval(target, env), value)
            env.assign(target.name, value)
        elif isinstance(target, n.Index):
            container = self.eval(target.target, env)
            key = self.eval(target.index, env)
            if compound:
                value = self.binary(node.op[0], self.get_item(container, key), value)
            self.set_item(container, key, value)
        else:
            container = self.eval(target.target, env)
            if compound:
                value = self.binary(node.op[0], self.get_field(container, target.name), value)
            self.set_field(container, target.name, value)

    def exec_if(self, node: n.If, env: Environment) -> None:
        if self.need_boolean(self.eval(node.cond, env), "'if'"):
            self.exec_block(node.then, env)
        else:
            self.exec_block(node.orelse, env)

    def run_loop(self, env: Environment, var: Optional[str], items: Iterable[Any], body: List[n.Node]) -> None:
        for item in items:
            if var is not None:
                env.assign(var, item)
            try:
                self.exec_block(body, env)
            except _Skip:
                continue
            except _Stop:
                break

    def exec_while(self, node: n.While, env: Environment) -> None:
        while self.need_boolean(self.eval(node.cond, env), "'while'"):
            try:
                self.exec_block(node.body, env)
            except _Skip:
                continue
            except _Stop:
                break

    def exec_repeat(self, node: n.Repeat, env: Environment) -> None:
        count = self.eval(node.count, env)
        if not is_number(count) or (isinstance(count, float) and not count.is_integer()) or count < 0:
            raise ZestRuntimeError(f"'repeat' needs a whole number that is not negative, but this is {describe(count)}.")
        self.run_loop(env, None, range(int(count)), node.body)

    def exec_for_each(self, node: n.ForEach, env: Environment) -> None:
        things = self.eval(node.iterable, env)
        if isinstance(things, (list, str)):
            items: Iterable[Any] = list(things)  # a snapshot, so changing the list inside the loop is safe
        elif isinstance(things, dict):
            items = list(things)
        else:
            hint = "To count, write: for each i in 1 to 5" if is_number(things) else None
            raise ZestRuntimeError(f"'for each' needs a list, text, map or range, but this is {describe(things)}.", hint=hint)
        self.run_loop(env, node.var, items, node.body)

    def exec_for_range(self, node: n.ForRange, env: Environment) -> None:
        start = self.eval(node.start, env)
        stop = self.eval(node.stop, env)
        step = 1 if node.step is None else self.eval(node.step, env)
        for what, value in (("start", start), ("end", stop), ("'by' step", step)):
            if not is_number(value):
                raise ZestRuntimeError(f"The {what} of a 'for each ... to' loop must be a number, but this is {describe(value)}.")
        if step == 0:
            raise ZestRuntimeError("The 'by' step can't be 0.",
                                   hint="To count down, use a negative step: for each i in 10 to 1 by -1")
        if any(isinstance(v, float) and not math.isfinite(v) for v in (start, stop, step)):
            raise ZestRuntimeError("A 'for each ... to' loop can't use infinity or not-a-number.")
        self.run_loop(env, node.var, count_between(start, stop, step), node.body)

    def exec_def(self, node: n.Def, env: Environment) -> None:
        env.define(node.name, Function(node.name, node.params, node.body, env, self.current_file))

    def exec_give(self, node: n.Give, env: Environment) -> None:
        raise _Give(None if node.value is None else self.eval(node.value, env))

    def exec_stop(self, node: n.Stop, env: Environment) -> None:
        raise _Stop()

    def exec_skip(self, node: n.Skip, env: Environment) -> None:
        raise _Skip()

    def exec_try(self, node: n.Try, env: Environment) -> None:
        try:
            self.exec_block(node.body, env)
        except (ZestError, RecursionError) as error:
            if isinstance(error, ZestError) and not error.catchable:
                raise
            if node.name is not None:
                message = error.message if isinstance(error, ZestError) else "Too many things were nested inside each other."
                env.assign(node.name, message)
            self.exec_block(node.handler, env)

    def exec_fail(self, node: n.Fail, env: Environment) -> None:
        raise ZestRuntimeError(display(self.eval(node.value, env)))

    def exec_use(self, node: n.Use, env: Environment) -> None:
        path = node.path if os.path.splitext(node.path)[1] else node.path + ".zest"
        base = self.base_dir
        if self.current_file and not self.current_file.startswith("<"):
            base = os.path.dirname(os.path.abspath(self.current_file))
        full = path if os.path.isabs(path) else os.path.normpath(os.path.join(base, path))
        key = os.path.abspath(full)
        if key in self.loaded:
            return
        try:
            with open(full, encoding="utf-8") as handle:
                source = handle.read()
        except FileNotFoundError:
            raise ZestRuntimeError(f"I couldn't find the file '{node.path}'.", hint=f"I looked in {base}")
        except (OSError, UnicodeDecodeError) as error:
            raise ZestRuntimeError(f"I couldn't read the file '{node.path}': {error}")
        self.loaded.add(key)
        self.sources[full] = source.splitlines()
        self._run(parse(source, full), full)

    # ---- expressions ------------------------------------------------------

    def eval_literal(self, node: n.Literal, env: Environment) -> Any:
        return node.value

    def eval_text(self, node: n.Text, env: Environment) -> Any:
        return "".join(p if isinstance(p, str) else display(self.eval(p, env)) for p in node.parts)

    def eval_name(self, node: n.Name, env: Environment) -> Any:
        try:
            return env.lookup(node.name)
        except KeyError:
            hint = MISTAKES.get(node.name)
            if hint is None:
                close = difflib.get_close_matches(node.name, env.names(), n=1, cutoff=0.7)
                hint = f"Did you mean '{close[0]}'?" if close else "Names must get a value before they are used: name = value"
            raise ZestRuntimeError(f"I don't know anything called '{node.name}'.", node.line, node.col,
                                   hint, self.current_file, len(node.name))

    def eval_list(self, node: n.ListLit, env: Environment) -> Any:
        return [self.eval(item, env) for item in node.items]

    def eval_map(self, node: n.MapLit, env: Environment) -> Any:
        table: Dict[Any, Any] = {}
        for key_node, value_node in node.pairs:
            key = check_key(self.eval(key_node, env))
            table[key] = self.eval(value_node, env)
        return table

    def eval_unary(self, node: n.Unary, env: Environment) -> Any:
        value = self.eval(node.operand, env)
        if node.op == "not":
            return not self.need_boolean(value, "'not'")
        if not is_number(value):
            raise ZestRuntimeError(f"A minus sign needs a number, but this is {describe(value)}.")
        return -value

    def eval_binary(self, node: n.Binary, env: Environment) -> Any:
        return self.binary(node.op, self.eval(node.left, env), self.eval(node.right, env))

    def eval_logic(self, node: n.Logic, env: Environment) -> Any:
        left = self.need_boolean(self.eval(node.left, env), f"'{node.op}'")
        if node.op == "and" and not left:
            return False
        if node.op == "or" and left:
            return True
        return self.need_boolean(self.eval(node.right, env), f"'{node.op}'")

    def eval_compare(self, node: n.Compare, env: Environment) -> Any:
        left = self.eval(node.left, env)
        right = self.eval(node.right, env)
        op = node.op
        if op == "==":
            return values_equal(left, right)
        if op == "!=":
            return not values_equal(left, right)
        if op == "in":
            return self.contains(right, left)
        if (is_number(left) and is_number(right)) or (isinstance(left, str) and isinstance(right, str)):
            return {"<": left < right, ">": left > right, "<=": left <= right, ">=": left >= right}[op]
        raise ZestRuntimeError(
            f"I can only compare two numbers or two texts with '{op}', but this has {describe(left)} and {describe(right)}.")

    def contains(self, container: Any, item: Any) -> bool:
        if isinstance(container, list):
            return any(values_equal(item, other) for other in container)
        if isinstance(container, str):
            if not isinstance(item, str):
                raise ZestRuntimeError(f"To look inside text, use text on the left of 'in', but this is {describe(item)}.")
            return item in container
        if isinstance(container, dict):
            return (is_number(item) or isinstance(item, str)) and item in container
        raise ZestRuntimeError(f"'in' looks inside a list, text or map, but the right side is {describe(container)}.")

    # ---- operators --------------------------------------------------------

    def binary(self, op: str, left: Any, right: Any) -> Any:
        if op == "+":
            if is_number(left) and is_number(right):
                return left + right
            if isinstance(left, str) or isinstance(right, str):
                return display(left) + display(right)
            if isinstance(left, list) and isinstance(right, list):
                return left + right
            raise ZestRuntimeError(
                f"I can't add {describe(left)} and {describe(right)}.",
                hint="Numbers add up, text joins, and lists join. If either side is text, the result is text.")
        if op == "*" and (isinstance(left, str) != isinstance(right, str)):
            text, count = (left, right) if isinstance(left, str) else (right, left)
            if not is_number(count) or (isinstance(count, float) and not count.is_integer()) or count < 0:
                raise ZestRuntimeError(f"To repeat text, multiply it by a whole number, but this is {describe(count)}.")
            if len(text) * int(count) > MAX_TEXT:
                raise ZestRuntimeError("That text would be far too long.")
            return text * int(count)
        self.need_numbers(op, left, right)
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            if right == 0:
                raise ZestRuntimeError("I can't divide by zero.")
            if isinstance(left, int) and isinstance(right, int) and left % right == 0:
                return left // right
            return left / right
        if op == "%":
            if right == 0:
                raise ZestRuntimeError("I can't divide by zero.")
            if isinstance(left, float) and not math.isfinite(left):
                raise ZestRuntimeError("I can't find a remainder with infinity.")
            return left % right
        return self.power(left, right)

    def power(self, base: Any, exponent: Any) -> Any:
        if isinstance(base, int) and isinstance(exponent, int):
            if exponent >= 0:
                if abs(base) > 1 and exponent * math.log2(abs(base)) > 4_000_000:
                    raise ZestRuntimeError("That number would be far too big to hold.")
                return base ** exponent
            if base == 0:
                raise ZestRuntimeError("I can't raise zero to a negative power.")
            return base ** exponent
        try:
            return math.pow(base, exponent)
        except ValueError:
            raise ZestRuntimeError("I can't raise a negative number to a fractional power, or zero to a negative power.")
        except OverflowError:
            raise ZestRuntimeError("That number would be far too big to hold.")

    # ---- items and fields -------------------------------------------------

    def get_item(self, container: Any, key: Any) -> Any:
        if isinstance(container, list):
            return container[to_position(key, len(container))]
        if isinstance(container, str):
            return container[to_position(key, len(container), "character")]
        if isinstance(container, dict):
            key = check_key(key)
            if key not in container:
                raise self.missing_key(container, key)
            return container[key]
        raise ZestRuntimeError(f"Square brackets work on lists, text and maps, but this is {describe(container)}.")

    def set_item(self, container: Any, key: Any, value: Any) -> None:
        if isinstance(container, list):
            container[to_position(key, len(container))] = value
        elif isinstance(container, dict):
            container[check_key(key)] = value
        elif isinstance(container, str):
            raise ZestRuntimeError("Text can't be changed in place.",
                                   hint="Build a new text instead, for example: word = \"J\" + slice(word, 2, -1)")
        else:
            raise ZestRuntimeError(f"Square brackets work on lists and maps, but this is {describe(container)}.")

    def missing_key(self, container: dict, key: Any) -> ZestRuntimeError:
        hint = None
        if isinstance(key, str):
            close = difflib.get_close_matches(key, [k for k in container if isinstance(k, str)], n=1, cutoff=0.6)
            hint = f"Did you mean {show(close[0])}?" if close else None
        if hint is None:
            hint = "Check with: if key in map"
        return ZestRuntimeError(f"The map has no key {show(key)}.", hint=hint)

    def get_field(self, container: Any, name: str) -> Any:
        if not isinstance(container, dict):
            raise ZestRuntimeError(f"Only maps have fields, but this is {describe(container)}.",
                                   hint="Maps look like {name: \"Ada\"}; read a field with person.name")
        if name not in container:
            raise self.missing_key(container, name)
        return container[name]

    def set_field(self, container: Any, name: str, value: Any) -> None:
        if not isinstance(container, dict):
            raise ZestRuntimeError(f"Only maps have fields, but this is {describe(container)}.")
        container[name] = value

    def eval_index(self, node: n.Index, env: Environment) -> Any:
        return self.get_item(self.eval(node.target, env), self.eval(node.index, env))

    def eval_field(self, node: n.Field, env: Environment) -> Any:
        return self.get_field(self.eval(node.target, env), node.name)

    # ---- calls ------------------------------------------------------------

    def eval_call(self, node: n.Call, env: Environment) -> Any:
        callee = self.eval(node.callee, env)
        args = [self.eval(arg, env) for arg in node.args]
        if isinstance(callee, Function):
            return self.call_function(callee, args, node)
        if isinstance(callee, Builtin):
            return self.call_builtin(callee, args)
        hint = None
        if isinstance(node.callee, n.Name):
            what = f"'{node.callee.name}'"
            if node.callee.name in BUILTINS:
                hint = f"'{node.callee.name}' is also a built-in function. Did you reuse the name for something else?"
        else:
            what = "this"
        raise ZestRuntimeError(f"I can't use {what} like a function, because it is {describe(callee)}.", hint=hint)

    def call_builtin(self, fn: Builtin, args: List[Any]) -> Any:
        if not fn.min_args <= len(args) <= fn.max_args:
            if fn.min_args == fn.max_args:
                needs = f"{fn.min_args} value{'' if fn.min_args == 1 else 's'}"
            else:
                needs = f"{fn.min_args} to {fn.max_args} values" if fn.max_args < 1000 else f"at least {fn.min_args} value"
            raise ZestRuntimeError(f"{fn.name}() needs {needs}, but you gave {len(args)}.", hint=f"Use it like: {fn.usage}")
        try:
            return fn.fn(self, *args)
        except (ZestError, QuitProgram):
            raise
        except (ValueError, TypeError, OverflowError, ZeroDivisionError, OSError) as error:
            raise ZestRuntimeError(f"{fn.name}() could not do that: {error}")

    def call_function(self, fn: Function, args: List[Any], node: n.Call) -> Any:
        params = fn.params
        required = sum(1 for p in params if p.default is None)
        if not required <= len(args) <= len(params):
            names = ", ".join(p.name for p in params)
            if required == len(params):
                needs = f"{len(params)} value{'' if len(params) == 1 else 's'}"
            else:
                needs = f"{required} to {len(params)} values"
            raise ZestRuntimeError(f"{fn.name}() needs {needs}, but you gave {len(args)}.",
                                   hint=f"It was made like this: to {fn.name}({names})")
        if self.depth >= self.max_depth:
            raise ZestRuntimeError(f"{fn.name}() has called itself too many times (over {self.max_depth} levels deep).",
                                   hint="Make sure it has a way to stop, such as an 'if' that gives back a value.")
        scope = Environment(fn.env)
        caller_file = self.current_file
        self.depth += 1
        self.current_file = fn.filename
        try:
            for position, param in enumerate(params):
                if position < len(args):
                    scope.define(param.name, args[position])
                else:
                    scope.define(param.name, self.eval(param.default, scope))
            try:
                self.exec_block(fn.body, scope)
            except _Give as result:
                return result.value
            return None
        except ZestError as error:
            error.trace.append((fn.name, node.line, caller_file))
            raise
        finally:
            self.depth -= 1
            self.current_file = caller_file
