import unittest

from zest.errors import ZestRuntimeError, ZestSyntaxError, format_error


class FormatTests(unittest.TestCase):
    def test_runtime_problem_with_everything(self):
        error = ZestRuntimeError("I don't know anything called 'y'.", 2, 12, "Did you mean 'x'?", "prog.zest", 1)
        text = format_error(error, {"prog.zest": ["to f(x)", "  give x + y", "end"]})
        self.assertEqual(text, (
            "Problem in prog.zest, line 2:\n"
            "  I don't know anything called 'y'.\n"
            "\n"
            "  2 |   give x + y\n"
            "    |            ^\n"
            "\n"
            "  Hint: Did you mean 'x'?\n"))

    def test_syntax_problems_use_their_own_wording(self):
        error = ZestSyntaxError("Oops.", 1, 1, None, "a.zest")
        self.assertTrue(format_error(error, {"a.zest": ["x"]}).startswith("Can't read a.zest, line 1:"))

    def test_underline_length(self):
        error = ZestRuntimeError("m", 1, 5, None, "a.zest", 4)
        self.assertIn("|     ^^^^\n", format_error(error, {"a.zest": ["say nmae"]}))

    def test_without_source_or_line(self):
        self.assertEqual(format_error(ZestRuntimeError("Plain.")), "Problem in your program:\n  Plain.\n")

    def test_prompt_input_has_a_friendly_name(self):
        error = ZestRuntimeError("m", 1, 1, None, "<repl-3>")
        self.assertIn("in your input, line 1", format_error(error, {"<repl-3>": ["x"]}))

    def test_tabs_keep_the_pointer_in_line(self):
        error = ZestRuntimeError("m", 1, 3, None, "a.zest")
        text = format_error(error, {"a.zest": ["\t\tx"]})
        self.assertIn("|   x\n", text)
        self.assertIn("|   ^\n", text)

    def test_trace_lines(self):
        error = ZestRuntimeError("m", 1, 1, None, "a.zest")
        error.trace = [("inner", 5, "a.zest"), ("outer", 9, "a.zest")]
        text = format_error(error, {})
        self.assertIn("(inside inner(), called from line 5)", text)
        self.assertIn("(inside outer(), called from line 9)", text)

    def test_repeated_trace_lines_are_squashed(self):
        error = ZestRuntimeError("m", 1, 1, None, "a.zest")
        error.trace = [("f", 3, "a.zest")] * 400 + [("main", 8, "a.zest")]
        text = format_error(error, {})
        self.assertEqual(text.count("inside f()"), 1)
        self.assertIn("400 times in a row", text)
        self.assertLess(len(text.splitlines()), 10)

    def test_trace_names_other_files(self):
        error = ZestRuntimeError("m", 1, 1, None, "lib.zest")
        error.trace = [("helper", 4, "main.zest")]
        self.assertIn("called from line 4 of main.zest", format_error(error, {}))

    def test_line_outside_the_source_is_not_shown(self):
        error = ZestRuntimeError("m", 99, 1, None, "a.zest")
        self.assertNotIn("|", format_error(error, {"a.zest": ["x"]}))


if __name__ == "__main__":
    unittest.main()
