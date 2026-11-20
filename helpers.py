import io
import os
import tempfile

from zest.errors import ZestError
from zest.interpreter import Interpreter


def make_interpreter(stdin="", **kwargs):
    out = io.StringIO()
    interpreter = Interpreter(write=out.write, read_line=io.StringIO(stdin).readline,
                              flush=lambda: None, **kwargs)
    return interpreter, out


def run(source, stdin="", seed=None):
    """Run Zest source and return everything it said."""
    interpreter, out = make_interpreter(stdin)
    if seed is not None:
        interpreter.rng.seed(seed)
    interpreter.run_source(source, "test.zest")
    return out.getvalue()


def error_of(source, stdin=""):
    """Run Zest source that must fail, and return the problem it reported."""
    try:
        run(source, stdin)
    except ZestError as error:
        return error
    raise AssertionError("expected the program to fail, but it ran fine:\n" + source)


class Project:
    """A temporary folder of Zest files."""

    def __init__(self, files):
        self.folder = tempfile.TemporaryDirectory()
        self.root = self.folder.name
        for name, content in files.items():
            path = os.path.join(self.root, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)

    def path(self, name):
        return os.path.join(self.root, name)

    def run(self, name, stdin=""):
        interpreter, out = make_interpreter(stdin, base_dir=self.root)
        try:
            interpreter.run_file(self.path(name))
        finally:
            self.interpreter = interpreter
        return out.getvalue()

    def cleanup(self):
        self.folder.cleanup()
