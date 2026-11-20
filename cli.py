"""The zest command: run programs, check them, or play in the prompt."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Callable, List, Optional

from . import __version__
from .builtins import BUILTINS
from .errors import QuitProgram, ZestError, ZestSyntaxError, format_error
from .interpreter import Interpreter
from .parser import parse

COMMANDS = {"run", "check", "repl", "builtins"}

BANNER = f"""Zest {__version__}. Type code and press Enter.
Try:  say "Hello"      Leave with:  exit  (or press Ctrl-D)"""


def _report(error: ZestError, interpreter: Optional[Interpreter], stream=None) -> None:
    sources = interpreter.sources if interpreter else {}
    (stream or sys.stderr).write(format_error(error, sources))


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except FileNotFoundError:
        raise SystemExit(f"zest: I couldn't find the file '{path}'.")
    except UnicodeDecodeError:
        raise SystemExit(f"zest: '{path}' is not a text file in UTF-8, so I can't read it.")
    except OSError as error:
        raise SystemExit(f"zest: I couldn't open '{path}': {error}")


def cmd_run(args: argparse.Namespace) -> int:
    source = _read(args.file)
    interpreter = Interpreter(base_dir=os.getcwd())
    try:
        interpreter.loaded.add(os.path.abspath(args.file))
        interpreter.run_source(source, args.file)
    except QuitProgram as stop:
        return stop.code
    except ZestError as error:
        sys.stdout.flush()
        _report(error, interpreter)
        return 1
    except RecursionError:
        sys.stdout.flush()
        sys.stderr.write("Problem: something is nested too deeply to run.\n")
        return 1
    except KeyboardInterrupt:
        sys.stdout.flush()
        sys.stderr.write("\nStopped.\n")
        return 130
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    source = _read(args.file)
    try:
        program = parse(source, args.file)
    except ZestError as error:
        _report(error, Interpreter_with_source(args.file, source))
        return 1
    except RecursionError:
        sys.stderr.write("Problem: something is nested too deeply to read.\n")
        return 1
    print(f"No problems found in {args.file} ({len(program)} top-level statements).")
    return 0


def Interpreter_with_source(filename: str, source: str) -> Interpreter:
    interpreter = Interpreter()
    interpreter.sources[filename] = source.splitlines()
    return interpreter


def cmd_builtins(args: argparse.Namespace) -> int:
    width = max(len(b.usage) for b in BUILTINS.values())
    for name in sorted(BUILTINS):
        entry = BUILTINS[name]
        print(f"{entry.usage:<{width}}  {entry.doc}")
    return 0


def repl(interpreter: Interpreter, read: Callable[[str], str] = input) -> int:
    print(BANNER)
    count = 0
    while True:
        try:
            line = read("zest> ")
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print()
            continue
        if line.strip() in ("exit", "quit"):
            return 0
        if not line.strip():
            continue
        buffer = [line]
        while True:
            count += 1
            try:
                interpreter.run_snippet("\n".join(buffer), f"<repl-{count}>", echo=True)
            except QuitProgram as stop:
                return stop.code
            except ZestSyntaxError as error:
                if error.at_end:
                    try:
                        buffer.append(read("....> "))
                    except EOFError:
                        print()
                        break
                    except KeyboardInterrupt:
                        print()
                        break
                    continue
                _report(error, interpreter, sys.stdout)
            except ZestError as error:
                _report(error, interpreter, sys.stdout)
            except RecursionError:
                print("Problem: something is nested too deeply to run.")
            except KeyboardInterrupt:
                print("\nStopped.")
            break


def cmd_repl(args: argparse.Namespace) -> int:
    return repl(Interpreter(base_dir=os.getcwd()))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zest",
        description="Zest: a programming language that is easy to read, write and learn.",
        epilog="Run a program:  zest hello.zest      Try things out:  zest repl")
    parser.add_argument("--version", action="version", version=f"zest {__version__}")
    sub = parser.add_subparsers(dest="command")
    run = sub.add_parser("run", help="run a Zest program")
    run.add_argument("file")
    run.set_defaults(func=cmd_run)
    check = sub.add_parser("check", help="look for mistakes without running the program")
    check.add_argument("file")
    check.set_defaults(func=cmd_check)
    sub.add_parser("repl", help="type code and see results straight away").set_defaults(func=cmd_repl)
    sub.add_parser("builtins", help="list every built-in function").set_defaults(func=cmd_builtins)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in COMMANDS and not argv[0].startswith("-"):
        argv.insert(0, "run")  # "zest hello.zest" means "zest run hello.zest"
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        return cmd_repl(args)
    try:
        return args.func(args)
    except BrokenPipeError:
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        except (OSError, ValueError, AttributeError):
            pass
        return 0
