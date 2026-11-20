"""Break Zest on purpose and check that the tests notice.

Each "mutation" changes one small piece of the interpreter (for example, making
list positions start at 0). The change is made on a throwaway COPY of the
project, the tests are run there, and the copy is deleted. Your real files are
never touched.

A mutation the tests fail to catch is reported as SURVIVED. That means a
behaviour exists that no test protects. If this file reports a pattern as
missing, the code it targets has changed and the entry needs updating.

Usage:  python tools/mutation_check.py
"""

import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECONDS_PER_RUN = 20  # the whole test suite normally takes about one second

MUTATIONS = [
    ("zest/values.py", "return position - 1 if position > 0 else length + position",
     "return position if position > 0 else length + position", "list positions start at 1"),
    ("zest/interpreter.py",
     "        while env is not None and not env.builtin:\n            if name in env.vars:\n                env.vars[name] = value\n                return\n            env = env.parent\n        self.vars[name] = value",
     "        self.vars[name] = value", "setting a name updates an outer one"),
    ("zest/interpreter.py",
     "        if isinstance(value, bool):\n            return value\n        raise ZestRuntimeError(f\"{what} needs true or false",
     "        return bool(value)\n        raise ZestRuntimeError(f\"{what} needs true or false", "conditions must be true or false"),
    ("zest/values.py", "    return 0 if span < -1e-9 else int(span + 1e-9) + 1",
     "    return int(abs(span) + 1e-9) + 1", "decimal counting never turns around"),
    ("zest/values.py", "        return max(0, (stop - start) // step + 1)",
     "        return abs((stop - start) // step) + 1", "whole-number counting never turns around"),
    ("zest/interpreter.py", "            if isinstance(error, ZestError) and not error.catchable:\n                raise\n",
     "", "running out of input cannot be hidden"),
    ("zest/builtins.py", "        error.catchable = False  # otherwise a loop that keeps asking could never end\n",
     "", "ask() marks end of input as uncatchable"),
    ("zest/values.py", 'text = format(value, ".15g")', "text = repr(value)", "0.1 + 0.2 shows as 0.3"),
    ("zest/interpreter.py",
     "            if isinstance(left, int) and isinstance(right, int) and left % right == 0:\n                return left // right\n",
     "", "whole division stays exact"),
    ("zest/interpreter.py", "            return (is_number(item) or isinstance(item, str)) and item in container",
     "            return False", "'in' works on maps"),
    ("zest/interpreter.py", "items: Iterable[Any] = list(things)  # a snapshot", "items = things  # a snapshot",
     "loops go over a snapshot"),
    ("zest/interpreter.py", "        if self.depth >= self.max_depth:", "        if False:", "recursion depth limit"),
    ("zest/parser.py", 'return n.Binary("^", base, self.parse_unary(), op.line, op.col)',
     'return n.Binary("^", base, self.parse_power(), op.line, op.col)', "2 ^ -1 is allowed"),
    ("zest/builtins.py", "rounding=ROUND_HALF_UP", "rounding=ROUND_HALF_EVEN", "round() sends halves up"),
    ("zest/interpreter.py", "        self.loaded.add(key)\n        self.sources[full]", "        self.sources[full]",
     "a file is used only once"),
    ("zest/interpreter.py", "        if node.op == \"and\" and not left:\n            return False\n",
     "", "'and' stops early"),
    ("zest/interpreter.py",
     "env.define(node.name, Function(node.name, node.params, node.body, env, self.current_file))",
     "env.define(node.name, Function(node.name, node.params, node.body, self.globals, self.current_file))",
     "functions remember where they were made"),
    ("zest/parser.py", "                orelse = [self.parse_if_tail(inner)]", "                orelse = []", "else-if chains"),
    ("zest/interpreter.py", "            error.trace.append((fn.name, node.line, caller_file))\n", "", "problems carry a call trace"),
    ("zest/values.py",
     "    if length == 0:\n        raise ZestRuntimeError(f\"There is no {noun} {position}: this is empty.\")\n",
     "", "empty list message"),
]


def run_one(path, old, new):
    work = tempfile.mkdtemp(prefix="zest-mutation-")
    try:
        copy = os.path.join(work, "zest")
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("__pycache__", ".git", "*.egg-info", "build"))
        target = os.path.join(copy, path)
        with open(target, encoding="utf-8") as handle:
            text = handle.read()
        if old not in text:
            return None, "pattern missing"
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(text.replace(old, new, 1))
        try:
            result = subprocess.run([sys.executable, "-m", "unittest", "-q"], cwd=copy,
                                    capture_output=True, text=True, timeout=SECONDS_PER_RUN)
        except subprocess.TimeoutExpired:
            return True, "the tests hung"
        return result.returncode != 0, "the tests failed"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    problems = []
    for path, old, new, label in MUTATIONS:
        caught, how = run_one(path, old, new)
        if caught is None:
            print(f"MISSING   {label}  ({how})", flush=True)
            problems.append(label)
        elif caught:
            print(f"caught    {label}  ({how})", flush=True)
        else:
            print(f"SURVIVED  {label}", flush=True)
            problems.append(label)
    print(f"\n{len(MUTATIONS) - len(problems)} of {len(MUTATIONS)} deliberate bugs were caught.")
    print("survivors:", problems)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
