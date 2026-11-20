import contextlib
import io
import os
import re
import unittest

import zest
from zest.builtins import BUILTINS
from zest.errors import ZestError, format_error
from zest.interpreter import Interpreter
from zest.lexer import KEYWORDS
from zest.parser import parse

ROOT = os.path.join(os.path.dirname(__file__), "..")
DOC_FILES = ["README.md", "docs/LANGUAGE.md", "docs/DESIGN.md"]


def read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as handle:
        return handle.read()


def blocks(text, language):
    return re.findall(r"```" + language + r"\n(.*?)```", text, re.S)


def run_source(source):
    out = io.StringIO()
    Interpreter(write=out.write, flush=lambda: None).run_source(source, "doc.zest")
    return out.getvalue()


def problem_text(source, filename):
    interpreter = Interpreter(write=lambda text: None, flush=lambda: None)
    try:
        interpreter.run_source(source, filename)
    except ZestError as error:
        return format_error(error, interpreter.sources).strip()
    raise AssertionError("expected a problem")


class DocumentationTests(unittest.TestCase):
    def test_every_builtin_is_documented_with_its_exact_usage(self):
        language = read("docs/LANGUAGE.md")
        for name, entry in BUILTINS.items():
            self.assertIn(f"`{entry.usage}`", language, name)
            self.assertIn(entry.doc, language, name)

    def test_every_special_word_is_listed(self):
        language = read("docs/LANGUAGE.md")
        for word in KEYWORDS:
            self.assertIn(f"`{word}`", language, word)

    def test_every_zest_code_block_is_valid(self):
        for name in DOC_FILES:
            for number, source in enumerate(blocks(read(name), "zest"), 1):
                with self.subTest(file=name, block=number):
                    parse(source, f"{name}#{number}")

    def test_the_readme_examples_really_run(self):
        readme = read("README.md")
        first, tour = blocks(readme, "zest")[:2]
        self.assertEqual(run_source(first), "Items: 4\nTotal: 4.45\n")
        run_source(tour)

    def test_the_python_example_in_the_readme_runs(self):
        readme = read("README.md")
        code = blocks(readme, "python")[0]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            exec(compile(code, "README.md", "exec"), {})
        self.assertEqual(out.getvalue(), "Hello from Zest\n42\n\n")

    def test_error_messages_in_the_docs_are_the_real_ones(self):
        samples = {
            "typo.zest": 'name = "Ada"\nsay nmae\n',
            "equals.zest": 'age = 20\nif age = 18\n  say "adult"\nend\n',
            "arity.zest": "to area(w, h)\n  give w * h\nend\nsay area(3)\n",
            "trace.zest": "to half(n)\n  give n / 0\nend\nto run()\n  give half(4)\nend\nrun()\n",
        }
        language, readme = read("docs/LANGUAGE.md"), read("README.md")
        for filename, source in samples.items():
            shown = problem_text(source, filename)
            self.assertIn(shown, language, filename)
            if filename != "arity.zest":
                self.assertIn(shown, readme, filename)

    def test_the_prompt_example_in_the_readme_is_real(self):
        from tests.test_cli import run_repl
        _, out = run_repl(["x = 5", "x * 2", '"Hello, " + "Ada"', "to square(n)", "  give n * n", "end", "square(12)", "exit"])
        for expected in ["\n10\n", '\n"Hello, Ada"\n', "\n144\n"]:
            self.assertIn(expected, out)
        for line in ["zest> x * 2", "10", 'zest> "Hello, " + "Ada"', '"Hello, Ada"', "....>   give n * n", "144"]:
            self.assertIn(line, read("README.md"))

    def test_links_between_documents_point_at_real_files(self):
        for name in DOC_FILES:
            base = os.path.dirname(os.path.join(ROOT, name))
            for target in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", read(name)):
                if target.startswith("http"):
                    continue
                self.assertTrue(os.path.exists(os.path.join(base, target)), f"{name} links to {target}")

    def test_every_example_is_mentioned_in_the_readme(self):
        readme = read("README.md")
        for filename in os.listdir(os.path.join(ROOT, "examples")):
            self.assertIn(f"examples/{filename}", readme, filename)

    def test_the_readme_counts_are_right(self):
        readme = read("README.md")
        self.assertIn(f"{len(BUILTINS)}-function", readme)
        self.assertIn("Forty-one built-in functions", readme)
        self.assertEqual(len(BUILTINS), 41)
        self.assertIn(f"{len(os.listdir(os.path.join(ROOT, 'examples')))} programs", readme.replace("eight", "8"))

    def test_the_version_matches_the_package_file(self):
        project = read("pyproject.toml")
        self.assertIn(f'version = "{zest.__version__}"', project)

    def test_the_documented_grammar_mentions_every_statement(self):
        design = read("docs/DESIGN.md")
        for word in ["say", "to", "give", "if", "while", "repeat", "for", "stop", "skip", "try", "fail", "use"]:
            self.assertIn(f'"{word}"', design, word)


if __name__ == "__main__":
    unittest.main()
