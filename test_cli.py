import contextlib
import io
import unittest
from unittest import mock

from tests.helpers import Project
from zest import __version__
from zest.builtins import BUILTINS
from zest.cli import main, repl
from zest.interpreter import Interpreter


def run_cli(*argv, stdin=""):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
            mock.patch("sys.stdin", io.StringIO(stdin)):
        try:
            code = main(list(argv))
        except SystemExit as stop:
            if isinstance(stop.code, str):
                err.write(stop.code)
                code = 1
            else:
                code = stop.code or 0
    return code, out.getvalue(), err.getvalue()


def run_repl(lines):
    pending = iter(lines)

    def read(prompt):
        try:
            return next(pending)
        except StopIteration:
            raise EOFError

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = repl(Interpreter(), read)
    return code, out.getvalue()


class RunTests(unittest.TestCase):
    def setUp(self):
        self.project = Project({
            "hello.zest": 'say "Hello!"\n',
            "ask.zest": 'name = ask("Name? ")\nsay "Hi {name}"\n',
            "bad_run.zest": 'say "before"\nsay 1 / 0\n',
            "bad_syntax.zest": "if true\n  say 1\n",
            "quit.zest": "say 1\nquit(3)\nsay 2\n",
            "use_main.zest": 'use "tools"\nsay twice(4)\n',
            "tools.zest": "to twice(n)\n  give n * 2\nend\n",
        })
        self.addCleanup(self.project.cleanup)

    def test_run_a_program(self):
        code, out, err = run_cli("run", self.project.path("hello.zest"))
        self.assertEqual((code, out, err), (0, "Hello!\n", ""))

    def test_a_file_name_alone_means_run(self):
        code, out, _ = run_cli(self.project.path("hello.zest"))
        self.assertEqual((code, out), (0, "Hello!\n"))

    def test_programs_can_read_input(self):
        code, out, _ = run_cli(self.project.path("ask.zest"), stdin="Ada\n")
        self.assertEqual((code, out), (0, "Name? Hi Ada\n"))

    def test_a_problem_while_running(self):
        code, out, err = run_cli(self.project.path("bad_run.zest"))
        self.assertEqual(code, 1)
        self.assertEqual(out, "before\n")
        self.assertIn("Problem in", err)
        self.assertIn("line 2", err)
        self.assertIn("I can't divide by zero.", err)
        self.assertIn("say 1 / 0", err)

    def test_a_problem_reading_the_code(self):
        code, out, err = run_cli(self.project.path("bad_syntax.zest"))
        self.assertEqual((code, out), (1, ""))
        self.assertIn("Can't read", err)
        self.assertIn("missing its 'end'", err)

    def test_missing_file(self):
        code, _, err = run_cli("nothing.zest")
        self.assertEqual(code, 1)
        self.assertIn("couldn't find the file 'nothing.zest'", err)

    def test_file_that_is_not_text(self):
        path = self.project.path("binary.zest")
        with open(path, "wb") as handle:
            handle.write(b"\xff\xfe\x00\x01")
        code, _, err = run_cli(path)
        self.assertEqual(code, 1)
        self.assertIn("not a text file in UTF-8", err)

    def test_quit_sets_the_exit_code(self):
        code, out, _ = run_cli(self.project.path("quit.zest"))
        self.assertEqual((code, out), (3, "1\n"))

    def test_use_works_from_any_folder(self):
        code, out, _ = run_cli(self.project.path("use_main.zest"))
        self.assertEqual((code, out), (0, "8\n"))

    def test_a_closed_pipe_is_not_an_error(self):
        with mock.patch("zest.cli.cmd_run", side_effect=BrokenPipeError):
            code, _, err = run_cli(self.project.path("hello.zest"))
        self.assertEqual((code, err), (0, ""))


class OtherCommandTests(unittest.TestCase):
    def test_check_finds_no_problems(self):
        project = Project({"ok.zest": "say 1\nsay 2\n"})
        self.addCleanup(project.cleanup)
        code, out, _ = run_cli("check", project.path("ok.zest"))
        self.assertEqual(code, 0)
        self.assertIn("No problems found", out)
        self.assertIn("2 top-level statements", out)

    def test_check_reports_a_problem_without_running(self):
        project = Project({"bad.zest": 'say "never shown"\nprint "x"\n'})
        self.addCleanup(project.cleanup)
        code, out, err = run_cli("check", project.path("bad.zest"))
        self.assertEqual((code, out), (1, ""))
        self.assertIn("'print' is not a Zest word", err)
        self.assertIn('print "x"', err)

    def test_builtins_lists_everything(self):
        code, out, _ = run_cli("builtins")
        self.assertEqual(code, 0)
        for name in BUILTINS:
            self.assertIn(BUILTINS[name].usage, out)
        self.assertEqual(len(out.strip().splitlines()), len(BUILTINS))

    def test_version(self):
        code, out, _ = run_cli("--version")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), f"zest {__version__}")

    def test_repl_command_reads_from_input(self):
        code, out, _ = run_cli("repl", stdin="1 + 2\nexit\n")
        self.assertEqual(code, 0)
        self.assertIn("3", out)

    def test_no_arguments_starts_the_prompt(self):
        code, out, _ = run_cli(stdin='say "hi"\n')
        self.assertEqual(code, 0)
        self.assertIn("hi", out)


class ReplTests(unittest.TestCase):
    def test_values_are_echoed(self):
        code, out = run_repl(["1 + 2", '"hi"', "[1, 2]", "exit"])
        self.assertEqual(code, 0)
        self.assertIn("\n3\n", out)
        self.assertIn('\n"hi"\n', out)
        self.assertIn("\n[1, 2]\n", out)

    def test_names_survive_between_lines(self):
        _, out = run_repl(["x = 5", "say x * 2", "x += 1", "x", "exit"])
        self.assertIn("10\n", out)
        self.assertIn("\n6\n", out)

    def test_assignments_and_nothing_are_not_echoed(self):
        _, out = run_repl(["x = 5", "to f()", "end", "f()", "exit"])
        shown = out.split("exit")[-1] if "Leave with" not in out else out.split("(or press Ctrl-D)")[1]
        self.assertNotIn("nothing", shown)
        self.assertEqual(shown.replace("zest> ", "").replace("....> ", "").strip(), "")

    def test_blocks_continue_on_the_next_line(self):
        _, out = run_repl(["if 1 < 2", '  say "yes"', "end", "exit"])
        self.assertIn("yes\n", out)

    def test_functions_across_lines(self):
        _, out = run_repl(["to double(n)", "  give n * 2", "end", "double(21)", "exit"])
        self.assertIn("\n42\n", out)

    def test_problems_are_shown_and_the_prompt_goes_on(self):
        _, out = run_repl(["say nothing_here", "say 1 / 0", "say 7", "exit"])
        self.assertIn("Problem in your input, line 1:", out)
        self.assertIn("I don't know anything called 'nothing_here'", out)
        self.assertIn("I can't divide by zero.", out)
        self.assertIn("7\n", out)

    def test_syntax_problems_are_shown(self):
        _, out = run_repl(['print "x"', "exit"])
        self.assertIn("Can't read your input", out)

    def test_functions_made_earlier_still_report_their_lines(self):
        _, out = run_repl(["to bad()", "  give 1 / 0", "end", "bad()", "exit"])
        self.assertIn("  give 1 / 0", out)
        self.assertIn("inside bad()", out)

    def test_end_of_input_leaves_quietly(self):
        code, _ = run_repl(["say 1"])
        self.assertEqual(code, 0)

    def test_end_of_input_inside_a_block_leaves_quietly(self):
        code, _ = run_repl(["if true", "say 1"])
        self.assertEqual(code, 0)

    def test_blank_lines_are_ignored(self):
        code, out = run_repl(["", "   ", "say 1", "exit"])
        self.assertIn("1\n", out)

    def test_quit_function_leaves_with_its_code(self):
        code, _ = run_repl(["quit(4)"])
        self.assertEqual(code, 4)


if __name__ == "__main__":
    unittest.main()
