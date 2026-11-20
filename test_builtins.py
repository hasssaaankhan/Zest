import os
import random
import tempfile
import unittest

from tests.helpers import error_of, make_interpreter, run
from zest.builtins import BUILTINS
from zest.errors import QuitProgram


class ConversionTests(unittest.TestCase):
    def test_text(self):
        self.assertEqual(run('say text(1.5) + "!", text([1, "a"]), text(nothing), text(true)'),
                         '1.5! [1, "a"] nothing true\n')

    def test_number(self):
        self.assertEqual(run('say number("42"), number(" 3.5 "), number("1e3"), number("-7"), number(5)'),
                         "42 3.5 1000 -7 5\n")

    def test_number_refuses_things_that_are_not_numbers(self):
        for bad in ['"abc"', '""', '"0x10"', '"1_000"', "true", "nothing", "[1]", '"nan"', '"3 4"']:
            error = error_of(f"say number({bad})")
            self.assertIn("can't turn", error.message, bad)

    def test_kind(self):
        self.assertEqual(
            run('to f()\nend\nsay kind(1), kind(2.5), kind("a"), kind(true), kind([]), kind({}), kind(f), kind(length), kind(nothing)'),
            "number number text boolean list map function function nothing\n")


class CollectionTests(unittest.TestCase):
    def test_length(self):
        self.assertEqual(run('say length("héllo"), length([1, 2]), length({a: 1}), length(""), length([])'), "5 2 1 0 0\n")
        self.assertIn("works on text, lists and maps", error_of("say length(5)").message)

    def test_add_insert_remove(self):
        source = ('xs = [1, 2, 3]\nadd(xs, 4)\ninsert(xs, 1, "first")\ninsert(xs, 6, "last")\n'
                  'insert(xs, -1, "very last")\nsay xs\nsay remove(xs, 1), remove(xs, -1)\nsay xs')
        self.assertEqual(run(source),
                         '["first", 1, 2, 3, 4, "last", "very last"]\nfirst very last\n[1, 2, 3, 4, "last"]\n')

    def test_insert_limits(self):
        self.assertIn("position 0", error_of("insert([1], 0, 5)").message)
        self.assertIn("position 4", error_of("insert([1, 2], 4, 5)").message)
        self.assertIn("whole number", error_of("insert([1], 1.5, 5)").message)

    def test_add_needs_a_list(self):
        self.assertIn("needs the first value to be a list", error_of('add("a", 1)').message)

    def test_remove_from_a_map(self):
        self.assertEqual(run('m = {a: 1, b: 2}\nsay remove(m, "a"), m'), '1 {"b": 2}\n')
        self.assertIn('no key "z"', error_of('remove({a: 1}, "z")').message)
        self.assertIn("lists and maps", error_of("remove(5, 1)").message)
        self.assertIn("no item 3", error_of("remove([1, 2], 3)").message)

    def test_keys_values_copy(self):
        self.assertEqual(run('m = {b: 1, a: 2}\nsay keys(m), values(m)'), '["b", "a"] [1, 2]\n')
        self.assertEqual(run('m = {a: 1}\nc = copy(m)\nc.a = 2\nsay m.a, copy(5), copy("x")'), "1 5 x\n")
        self.assertIn("needs the first value to be a map", error_of("keys([1])").message)

    def test_sorted_and_reversed(self):
        self.assertEqual(run('xs = [3, 1, 2]\nsay sorted(xs), xs, sorted(["b", "a"]), sorted([])'),
                         '[1, 2, 3] [3, 1, 2] ["a", "b"] []\n')
        self.assertEqual(run('say reversed([1, 2, 3]), reversed("abc"), reversed([])'), "[3, 2, 1] cba []\n")
        self.assertIn("only numbers or only text", error_of('say sorted([1, "a"])').message)
        self.assertIn("lists and text", error_of("say reversed(5)").message)

    def test_range_refuses_infinity(self):
        for bad in ["range(0, 1e999)", "range(0, 5, 1e999)", "range(-1e999, 5)"]:
            self.assertIn("infinity", error_of(f"say {bad}").message, bad)

    def test_range(self):
        self.assertEqual(run("say range(1, 5), range(5, 1), range(5, 1, -2), range(0, 1, 0.5), range(3, 3)"),
                         "[1, 2, 3, 4, 5] [] [5, 3, 1] [0, 0.5, 1] [3]\n")
        self.assertIn("can't be 0", error_of("say range(1, 3, 0)").message)
        self.assertIn("too many", error_of("say range(1, 100000000)").message)
        self.assertIn("needs the second value to be a number", error_of('say range(1, "a")').message)

    def test_slice(self):
        self.assertEqual(run('say slice("hello", 2, 4), slice([1, 2, 3, 4], 2, -1), slice("hello", 3, 99), slice("hello", -3, -1)'),
                         "ell [2, 3, 4] llo llo\n")
        self.assertEqual(run('say slice("hello", 4, 2), slice([1, 2], 0, 5)'), " [1, 2]\n")
        self.assertIn("lists and text", error_of("say slice(5, 1, 2)").message)

    def test_find(self):
        self.assertEqual(run('say find("hello", "ll"), find("hello", "z"), find([5, 6, 7], 7), find([1], 9), find([[1]], [1])'),
                         "3 0 3 0 1\n")
        self.assertIn("needs the second value to be text", error_of('say find("a", 1)').message)
        self.assertIn("text and lists", error_of("say find(5, 1)").message)


class TextFunctionTests(unittest.TestCase):
    def test_split(self):
        self.assertEqual(run('say split("  a  b "), split("a,b,,c", ","), split("", ","), split("abc", "b")'),
                         '["a", "b"] ["a", "b", "", "c"] [""] ["a", "c"]\n')
        self.assertIn("can't be empty", error_of('say split("a", "")').message)

    def test_join(self):
        self.assertEqual(run('say join([1, 2.5, "x"], "-"), join(["a", "b"]), join([], ",")'), "1-2.5-x ab \n")
        self.assertIn("needs the first value to be a list", error_of('say join("abc")').message)

    def test_replace_and_case(self):
        self.assertEqual(run('say replace("a-b-c", "-", "+"), upper("aB"), lower("aB"), "[" + trim("  hi \\n") + "]"'),
                         "a+b+c AB ab [hi]\n")
        self.assertIn("can't be empty", error_of('say replace("a", "", "b")').message)

    def test_starts_and_ends(self):
        self.assertEqual(run('say starts_with("hello", "he"), starts_with("hello", "lo"), ends_with("hello", "lo"), ends_with("hello", "")'),
                         "true false true true\n")
        self.assertIn("needs the first value to be text", error_of("say upper(5)").message)


class MathTests(unittest.TestCase):
    def test_abs_floor_ceiling(self):
        self.assertEqual(run("say abs(-3), abs(2.5), floor(-2.5), floor(2.9), ceiling(-2.5), ceiling(2.1)"),
                         "3 2.5 -3 2 -2 3\n")
        self.assertIn("infinity", error_of("say floor(1e999)").message)
        self.assertIn("infinity", error_of("say ceiling(-1e999)").message)

    def test_round_halves_go_up(self):
        self.assertEqual(run("say round(2.5), round(3.5), round(-2.5), round(2.4), round(5), round(0.5)"),
                         "3 4 -3 2 5 1\n")
        self.assertEqual(run("say round(2.675, 2), round(1.005, 2), round(3.14159, 3), round(2.5, 0), round(10, 2)"),
                         "2.68 1.01 3.142 3 10\n")

    def test_round_limits(self):
        self.assertIn("between 0 and 15", error_of("say round(1.5, -1)").message)
        self.assertIn("whole number", error_of("say round(1.5, 0.5)").message)
        self.assertIn("infinity", error_of("say round(1e999)").message)

    def test_sqrt(self):
        self.assertEqual(run("say sqrt(16), sqrt(2), sqrt(0)"), "4 1.4142135623731 0\n")
        self.assertIn("negative", error_of("say sqrt(-1)").message)

    def test_min_max_sum(self):
        self.assertEqual(run('say min(3, 1, 2), max([3, 9, 2]), min("b", "a"), max(5), sum([1, 2.5]), sum([])'),
                         "1 9 a 5 3.5 0\n")
        self.assertIn("at least one", error_of("say min([])").message)
        self.assertIn("all numbers or all text", error_of('say max(1, "a")').message)
        self.assertIn("list of numbers", error_of('say sum([1, "a"])').message)

    def test_random_is_repeatable_with_a_seed(self):
        expected = str(random.Random(7).randint(1, 100))
        self.assertEqual(run("seed(7)\nsay random(1, 100)"), expected + "\n")
        self.assertEqual(run("seed(7)\nsay random(1, 100)"), run("seed(7)\nsay random(1, 100)"))

    def test_random_ranges(self):
        values = run("repeat 200 times\n  say random(1, 3)\nend").split()
        self.assertEqual(set(values), {"1", "2", "3"})
        self.assertEqual(run("say random(4, 4)"), "4\n")
        self.assertEqual(run("x = random()\nsay x >= 0 and x < 1"), "true\n")

    def test_random_problems(self):
        self.assertIn("no values, or two", error_of("say random(5)").message)
        self.assertIn("smaller one", error_of("say random(5, 1)").message)
        self.assertIn("whole number", error_of("say random(1, 2.5)").message)
        self.assertIn("empty list", error_of("say pick([])").message)
        self.assertIn("whole number", error_of("seed(1.5)").message)

    def test_pick(self):
        self.assertEqual(run('say pick(["only"])'), "only\n")
        self.assertIn(run("seed(1)\nsay pick([1, 2, 3])").strip(), {"1", "2", "3"})


class InputOutputTests(unittest.TestCase):
    def test_ask(self):
        self.assertEqual(run('name = ask("Name? ")\nsay "Hi " + name', stdin="Ada\n"), "Name? Hi Ada\n")
        self.assertEqual(run("say ask()", stdin="x\r\n"), "x\n")
        self.assertEqual(run('say ask("a "), ask("b ")', stdin="1\n2\n"), "a b 1 2\n")
        self.assertEqual(run("say length(ask())", stdin="\n"), "0\n")

    def test_ask_when_input_is_finished(self):
        error = error_of("say ask()", stdin="")
        self.assertIn("no more input", error.message)
        self.assertIn("pipe", error.hint)

    def test_files(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "note.txt").replace("\\", "/")
            source = (f'say file_exists("{path}")\nwrite_file("{path}", "héllo\\nworld")\n'
                      f'say file_exists("{path}")\nsay read_file("{path}")\nsay length(split(read_file("{path}"), "\\n"))')
            self.assertEqual(run(source), "false\ntrue\nhéllo\nworld\n2\n")

    def test_file_problems(self):
        error = error_of('say read_file("/no/such/file.txt")')
        self.assertIn("couldn't find the file", error.message)
        self.assertIn("couldn't write", error_of('write_file("/no/such/folder/x.txt", "a")').message)

    def test_a_bad_write_never_touches_the_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "keep.txt").replace("\\", "/")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("precious")
            error = error_of(f'write_file("{path}", 5)')
            self.assertIn("needs the second value to be text", error.message)
            with open(path, encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "precious")
            missing = os.path.join(folder, "never_made.txt").replace("\\", "/")
            error_of(f'write_file("{missing}", 5)')
            self.assertFalse(os.path.exists(missing))

    def test_time(self):
        self.assertEqual(run("say now() > 1600000000"), "true\n")
        self.assertEqual(run("wait(0)\nsay 1"), "1\n")
        self.assertIn("negative", error_of("wait(-1)").message)

    def test_quit(self):
        with self.assertRaises(QuitProgram) as caught:
            run("quit()")
        self.assertEqual(caught.exception.code, 0)
        with self.assertRaises(QuitProgram) as caught:
            run("quit(2)")
        self.assertEqual(caught.exception.code, 2)


class CallTests(unittest.TestCase):
    def test_wrong_number_of_values(self):
        error = error_of("say length()")
        self.assertEqual(error.message, "length() needs 1 value, but you gave 0.")
        self.assertEqual(error.hint, "Use it like: length(thing)")
        self.assertIn("needs 2 values", error_of("add([1])").message)
        self.assertIn("needs 1 to 2 values", error_of("say round(1, 2, 3)").message)
        self.assertIn("at least 1 value", error_of("say min()").message)

    def test_every_builtin_has_a_usage_and_a_description(self):
        for name, entry in BUILTINS.items():
            self.assertTrue(entry.usage.startswith(name + "("), name)
            self.assertTrue(entry.doc.endswith("."), name)
            self.assertLessEqual(entry.min_args, entry.max_args, name)

    def test_builtins_never_leak_python_errors(self):
        """Throw odd values at every built-in: it may refuse, but only with a Zest message."""
        from zest.errors import ZestError
        oddballs = ["nothing", "true", "0", "-1", "1.5", '""', '"x"', "[]", "[1, 2]", "{}", "{a: 1}", "1e999", "length"]
        skip = {"wait", "ask", "quit", "write_file", "read_file", "file_exists", "now", "random", "pick", "seed"}
        for name, entry in BUILTINS.items():
            if name in skip:
                continue
            for count in range(entry.min_args, min(entry.max_args, 3) + 1):
                for a in oddballs:
                    for b in oddballs:
                        args = ", ".join([a, b, a][:count])
                        try:
                            run(f"x = {name}({args})")
                        except ZestError:
                            pass


if __name__ == "__main__":
    unittest.main()
