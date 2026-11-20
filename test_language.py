import unittest

from tests.helpers import Project, error_of, make_interpreter, run
from zest.errors import QuitProgram, ZestRuntimeError


class NamesAndScopeTests(unittest.TestCase):
    def test_assignment_inside_a_function_updates_an_outer_name(self):
        self.assertEqual(run("x = 1\nto f()\n  x = 2\nend\nf()\nsay x"), "2\n")

    def test_new_names_inside_a_function_stay_inside(self):
        error = error_of("to g()\n  y = 5\nend\ng()\nsay y")
        self.assertIn("'y'", error.message)

    def test_parameters_are_always_local(self):
        self.assertEqual(run("x = 1\nto f(x)\n  x = 99\nend\nf(5)\nsay x"), "1\n")

    def test_closures_remember_their_names(self):
        source = ("to make()\n  n = 0\n  to bump()\n    n += 1\n    give n\n  end\n  give bump\nend\n"
                  "a = make()\nb = make()\na()\na()\nsay a(), b()")
        self.assertEqual(run(source), "3 1\n")

    def test_functions_can_call_functions_defined_later(self):
        self.assertEqual(run("to a()\n  give b()\nend\nto b()\n  give 7\nend\nsay a()"), "7\n")

    def test_recursion(self):
        source = "to fact(n)\n  if n <= 1\n    give 1\n  end\n  give n * fact(n - 1)\nend\nsay fact(10)"
        self.assertEqual(run(source), "3628800\n")

    def test_recursion_has_a_depth_limit(self):
        error = error_of("to f(n)\n  give f(n + 1)\nend\nf(1)")
        self.assertIn("too many times", error.message)
        self.assertIn("way to stop", error.hint)

    def test_depth_just_under_the_limit_works(self):
        source = "to d(n)\n  if n == 0\n    give 0\n  end\n  give 1 + d(n - 1)\nend\nsay d(498)"
        self.assertEqual(run(source), "498\n")

    def test_default_values_are_fresh_on_every_call(self):
        source = "to f(items = [])\n  add(items, 1)\n  give length(items)\nend\nsay f(), f()"
        self.assertEqual(run(source), "1 1\n")

    def test_defaults_can_use_earlier_parameters(self):
        self.assertEqual(run("to f(a, b = a * 2)\n  give b\nend\nsay f(4), f(4, 1)"), "8 1\n")

    def test_function_without_give_returns_nothing(self):
        self.assertEqual(run("to f()\nend\nsay f()\nsay kind(f())"), "nothing\nnothing\n")

    def test_bare_give(self):
        self.assertEqual(run("to f()\n  give\nend\nsay f()"), "nothing\n")

    def test_give_stops_a_function_early(self):
        source = "to f()\n  for each i in 1 to 10\n    if i == 3\n      give i\n    end\n  end\n  give 0\nend\nsay f()"
        self.assertEqual(run(source), "3\n")

    def test_loop_variable_stays_after_the_loop(self):
        self.assertEqual(run("for each i in 1 to 3\nend\nsay i"), "3\n")

    def test_arity_errors(self):
        error = error_of("to f(a, b)\nend\nf(1)")
        self.assertIn("needs 2 values", error.message)
        self.assertIn("to f(a, b)", error.hint)
        self.assertIn("1 to 2", error_of("to f(a, b = 1)\nend\nf()").message)
        self.assertIn("gave 3", error_of("to f(a)\nend\nf(1, 2, 3)").message)

    def test_unknown_name_suggests_a_close_one(self):
        error = error_of("name = 1\nsay nmae")
        self.assertIn("Did you mean 'name'?", error.hint)
        self.assertEqual((error.line, error.col, error.length), (2, 5, 4))

    def test_unknown_name_with_other_language_word(self):
        self.assertIn("say", error_of("print(1)").hint)
        self.assertIn("nothing", error_of("say null").hint)

    def test_builtins_can_be_shadowed_without_changing_them(self):
        source = "length = 5\nsay length\nto f()\n  length = 7\nend\nf()\nsay length\nsay text(1)"
        self.assertEqual(run(source), "5\n7\n1\n")

    def test_calling_a_shadowed_builtin_explains_itself(self):
        error = error_of("length = 5\nsay length([1])")
        self.assertIn("like a function", error.message)
        self.assertIn("built-in", error.hint)

    def test_calling_something_that_is_not_a_function(self):
        error = error_of('x = "hi"\nx()')
        self.assertIn("a text", error.message)

    def test_globals_survive_between_runs(self):
        interpreter, out = make_interpreter()
        interpreter.run_source("x = 41", "a")
        interpreter.run_source("say x + 1", "b")
        self.assertEqual(out.getvalue(), "42\n")


class ListTests(unittest.TestCase):
    def test_positions_start_at_one(self):
        self.assertEqual(run("xs = [10, 20, 30]\nsay xs[1], xs[3], xs[-1], xs[-3]"), "10 30 30 10\n")

    def test_zero_is_explained(self):
        error = error_of("xs = [1]\nsay xs[0]")
        self.assertIn("start at 1", error.message)
        self.assertIn("[-1]", error.hint)

    def test_out_of_range(self):
        self.assertIn("no item 5: this has 3 items", error_of("say [1, 2, 3][5]").message)
        self.assertIn("no item -4", error_of("say [1, 2, 3][-4]").message)
        self.assertIn("this has 1 item.", error_of("say [1][2]").message)
        self.assertIn("this is empty", error_of("say [][1]").message)

    def test_positions_must_be_whole_numbers(self):
        self.assertIn("whole number", error_of("say [1, 2][1.5]").message)
        self.assertIn("whole number", error_of('say [1, 2]["a"]').message)
        self.assertEqual(run("say [5, 6][2.0]"), "6\n")

    def test_set_by_position(self):
        self.assertEqual(run("xs = [1, 2, 3]\nxs[2] = \"x\"\nxs[-1] = 9\nsay xs"), '[1, "x", 9]\n')
        self.assertIn("no item 4", error_of("xs = [1, 2, 3]\nxs[4] = 1").message)

    def test_lists_are_shared_not_copied(self):
        self.assertEqual(run("a = [1]\nb = a\nadd(b, 2)\nsay a"), "[1, 2]\n")
        self.assertEqual(run("a = [1]\nb = copy(a)\nadd(b, 2)\nsay a, b"), "[1] [1, 2]\n")

    def test_joining_lists(self):
        self.assertEqual(run("say [1] + [2, 3]"), "[1, 2, 3]\n")

    def test_changing_a_list_while_looping_is_safe(self):
        self.assertEqual(run("xs = [1, 2, 3]\nfor each x in xs\n  add(xs, x)\nend\nsay length(xs)"), "6\n")

    def test_nested_lists_and_aliasing_inside(self):
        self.assertEqual(run("g = [[1, 2], [3, 4]]\ng[2][1] = 9\nsay g"), "[[1, 2], [9, 4]]\n")

    def test_indexing_something_else(self):
        self.assertIn("Square brackets", error_of("x = 5\nsay x[1]").message)


class TextTests(unittest.TestCase):
    def test_indexing_text(self):
        self.assertEqual(run('w = "hello"\nsay w[1], w[-1], w[3]'), "h o l\n")
        self.assertIn("no character 9: this has 5 characters", error_of('say "hello"[9]').message)

    def test_text_cannot_be_changed_in_place(self):
        error = error_of('w = "hi"\nw[1] = "H"')
        self.assertIn("can't be changed", error.message)
        self.assertIn("slice", error.hint)

    def test_plus_joins_when_either_side_is_text(self):
        self.assertEqual(run('say "a" + 1, 1 + "a", "x" + true, "n:" + nothing, "l" + [1]'),
                         "a1 1a xtrue n:nothing l[1]\n")

    def test_repeating_text(self):
        self.assertEqual(run('say "ab" * 3, 2 * "x", "q" * 0'), "ababab xx \n")
        self.assertIn("whole number", error_of('say "a" * 1.5').message)
        self.assertIn("whole number", error_of('say "a" * -1').message)

    def test_interpolation(self):
        source = 'n = "Ada"\np = {name: "Bo", tags: ["x"]}\nsay "{n} {1 + 2} {p["name"]} {p.tags[1]} {upper(n)} {n == "Ada"}"'
        self.assertEqual(run(source), "Ada 3 Bo x ADA true\n")

    def test_escaped_braces_are_plain_text(self):
        self.assertEqual(run(r'say "\{not code\}"'), "{not code}\n")

    def test_escapes(self):
        self.assertEqual(run(r'say "a\tb"'), "a\tb\n")
        self.assertEqual(run('say "line1\\nline2"'), "line1\nline2\n")

    def test_error_inside_interpolation_points_at_the_name(self):
        error = error_of('say "x {nope}"')
        self.assertEqual((error.line, error.col), (1, 9))


class MapTests(unittest.TestCase):
    def test_fields_and_keys(self):
        source = 'p = {name: "Ada"}\np.age = 36\np["city"] = "London"\nsay p.name, p["age"], p.city\nsay p'
        self.assertEqual(run(source), 'Ada 36 London\n{"name": "Ada", "age": 36, "city": "London"}\n')

    def test_keys_keep_their_order(self):
        self.assertEqual(run('m = {}\nm.b = 1\nm.a = 2\nsay keys(m)'), '["b", "a"]\n')

    def test_number_keys(self):
        self.assertEqual(run('m = {}\nm[1] = "one"\nm[2.0] = "two"\nsay m[1], m[2]'), "one two\n")

    def test_missing_key_suggests(self):
        error = error_of('p = {name: 1}\nsay p.nmae')
        self.assertIn("no key \"nmae\"", error.message)
        self.assertIn('"name"', error.hint)
        self.assertIn("if key in map", error_of('p = {}\nsay p["zzz"]').hint)

    def test_bad_keys(self):
        self.assertIn("text or numbers", error_of("m = {}\nm[[1]] = 2").message)
        self.assertIn("text or numbers", error_of("m = {}\nm[true] = 2").message)

    def test_fields_need_a_map(self):
        error = error_of("x = [1]\nsay x.size")
        self.assertIn("Only maps have fields", error.message)

    def test_maps_are_shared(self):
        self.assertEqual(run("a = {n: 1}\nb = a\nb.n = 2\nsay a.n"), "2\n")

    def test_in_checks_keys(self):
        self.assertEqual(run('m = {a: 1}\nsay "a" in m, "b" in m, 1 in m'), "true false false\n")


class OperatorTests(unittest.TestCase):
    def test_arithmetic(self):
        self.assertEqual(run("say 7 + 3, 7 - 3, 7 * 3, 7 / 2, 7 % 3, 2 ^ 10"), "10 4 21 3.5 1 1024\n")

    def test_division_keeps_whole_results_whole(self):
        self.assertEqual(run("say 6 / 3, 10 / 4, 1 / 3"), "2 2.5 0.333333333333333\n")
        self.assertEqual(run("say (10 ^ 30) / 10"), "100000000000000000000000000000\n")

    def test_remainder_follows_the_divisor(self):
        self.assertEqual(run("say -7 % 3, 7 % -3, 7.5 % 2"), "2 -2 1.5\n")

    def test_powers(self):
        self.assertEqual(run("say 2 ^ 0.5 * 2 ^ 0.5, 10 ^ -2, 4 ^ 0.5, 0 ^ 0"), "2 0.01 2 1\n")

    def test_division_by_zero(self):
        self.assertIn("divide by zero", error_of("say 1 / 0").message)
        self.assertIn("divide by zero", error_of("say 1 % 0").message)
        self.assertIn("zero to a negative", error_of("say 0 ^ -1").message)

    def test_impossible_powers(self):
        self.assertIn("negative number", error_of("say (-8) ^ 0.5").message)
        self.assertIn("too big", error_of("say 2 ^ 100000000").message)
        self.assertIn("too big", error_of("say 10.0 ^ 1000").message)

    def test_big_numbers_are_exact(self):
        source = "n = 1\nfor each i in 1 to 25\n  n *= i\nend\nsay n"
        self.assertEqual(run(source), "15511210043330985984000000\n")

    def test_huge_numbers_print_in_full(self):
        source = "n = 1\nfor each i in 1 to 2000\n  n *= i\nend\nsay length(text(n))"
        self.assertEqual(run(source), "5736\n")

    def test_number_display(self):
        self.assertEqual(run("say 0.1 + 0.2, 1e3, 2.50, 10 ^ 15, 1e15, 1.5e-7, 100 * 1.1"),
                         "0.3 1000 2.5 1000000000000000 1e15 1.5e-7 110\n")
        self.assertEqual(run("say 1e999, -1e999"), "infinity -infinity\n")

    def test_wrong_types_explain_themselves(self):
        error = error_of('say "a" - 1')
        self.assertIn("I can only subtract numbers", error.message)
        self.assertIn('a text ("a")', error.message)
        self.assertIn("a number (1)", error.message)
        self.assertIn("multiply", error_of("say [1] * [2]").message)
        self.assertIn("can't add", error_of("say [1] + 1").message)
        self.assertIn("can't add", error_of("say nothing + 1").message)
        self.assertIn("minus sign", error_of('say -"a"').message)

    def test_compound_assignment(self):
        source = 'x = 10\nx += 5\nx -= 3\nx *= 2\nx /= 4\ns = "a"\ns += "b"\nxs = [1, 2]\nxs[2] += 5\np = {n: 1}\np.n -= 4\nsay x, s, xs, p.n'
        self.assertEqual(run(source), "6 ab [1, 7] -3\n")

    def test_compound_assignment_needs_an_existing_name(self):
        self.assertIn("'nope'", error_of("nope += 1").message)


class EqualityAndLogicTests(unittest.TestCase):
    def test_equality(self):
        self.assertEqual(run('say 1 == 1.0, 1 == true, "1" == 1, nothing == nothing, nothing == false, "a" == "a"'),
                         "true false false true false true\n")

    def test_deep_equality(self):
        self.assertEqual(run("say [1, [2]] == [1, [2]], [1] == [2], {a: 1} == {a: 1}, {a: 1} == {a: 2}, [] == {}"),
                         "true false true false false\n")

    def test_different_is_not_equal(self):
        self.assertEqual(run('say 1 != 2, "a" != "a"'), "true false\n")

    def test_ordering(self):
        self.assertEqual(run('say 1 < 2, 2 <= 2, 3 > 4, 3 >= 3, "apple" < "banana", "b" > "a"'),
                         "true true false true true true\n")

    def test_ordering_needs_matching_kinds(self):
        error = error_of('say 1 < "a"')
        self.assertIn("two numbers or two texts", error.message)
        self.assertIn("two numbers or two texts", error_of("say [1] < [2]").message)

    def test_conditions_must_be_true_or_false(self):
        self.assertIn("'if' needs true or false", error_of("if 1\nend").message)
        self.assertIn("'while' needs true or false", error_of('while "yes"\nend').message)
        self.assertIn("'not' needs true or false", error_of("say not 5").message)
        self.assertIn("'and' needs true or false", error_of("say 1 and true").message)
        self.assertIn("'or' needs true or false", error_of("say false or 1").message)
        self.assertIn("comparison", error_of("if nothing\nend").hint)

    def test_and_or_short_circuit(self):
        self.assertEqual(run("say false and 1 / 0 == 1, true or 1 / 0 == 1"), "false true\n")

    def test_in(self):
        self.assertEqual(run('say 2 in [1, 2], 5 in [1, 2], "ell" in "hello", "z" in "hello", [1] in [[1]]'),
                         "true false true false true\n")
        self.assertIn("looks inside", error_of("say 1 in 5").message)
        self.assertIn("text on the left", error_of('say 1 in "abc"').message)


class LoopTests(unittest.TestCase):
    def test_repeat(self):
        self.assertEqual(run('repeat 3 times\n  say "x"\nend'), "x\nx\nx\n")
        self.assertEqual(run("repeat 0 times\n  say 1\nend\nsay 2"), "2\n")
        self.assertEqual(run("n = 2\nrepeat n * 2 times\n  say 1\nend"), "1\n1\n1\n1\n")

    def test_repeat_needs_a_good_number(self):
        self.assertIn("whole number", error_of("repeat 2.5 times\nend").message)
        self.assertIn("not negative", error_of("repeat -1 times\nend").message)
        self.assertIn("whole number", error_of('repeat "a" times\nend').message)

    def test_while(self):
        self.assertEqual(run("n = 0\nwhile n < 3\n  n += 1\nend\nsay n"), "3\n")

    def test_for_each_over_lists_text_and_maps(self):
        self.assertEqual(run('for each c in "abc"\n  say c\nend'), "a\nb\nc\n")
        self.assertEqual(run("for each k in {x: 1, y: 2}\n  say k\nend"), "x\ny\n")
        self.assertEqual(run("for each x in []\n  say x\nend\nsay 0"), "0\n")

    def test_for_each_needs_something_to_loop_over(self):
        error = error_of("for each i in 5\nend")
        self.assertIn("'for each'", error.message)
        self.assertIn("1 to 5", error.hint)
        self.assertIn("a boolean", error_of("for each i in true\nend").message)

    def test_counting(self):
        self.assertEqual(run("for each i in 1 to 4\n  say i\nend"), "1\n2\n3\n4\n")
        self.assertEqual(run("for each i in 3 to 3\n  say i\nend"), "3\n")

    def test_counting_down_needs_a_negative_step(self):
        self.assertEqual(run("for each i in 10 to 1 by -3\n  say i\nend"), "10\n7\n4\n1\n")
        self.assertEqual(run("for each i in 5 to 1\n  say i\nend\nsay \"done\""), "done\n")

    def test_counting_by_steps_and_decimals(self):
        self.assertEqual(run("for each i in 1 to 10 by 4\n  say i\nend"), "1\n5\n9\n")
        self.assertEqual(run("for each x in 0 to 1 by 0.5\n  say x\nend"), "0\n0.5\n1\n")
        self.assertEqual(run("n = 0\nfor each x in 0 to 1 by 0.1\n  n += 1\nend\nsay n"), "11\n")

    def test_counting_with_decimals_up_and_down(self):
        self.assertEqual(run("for each x in 1 to 0 by 0.5\n  say x\nend\nsay \"none\""), "none\n")
        self.assertEqual(run("for each x in 1 to 0 by -0.5\n  say x\nend"), "1\n0.5\n0\n")
        self.assertEqual(run("say range(1, 0, 0.5), range(1, 0, -0.5)"), "[] [1, 0.5, 0]\n")

    def test_counting_problems(self):
        self.assertIn("can't be 0", error_of("for each i in 1 to 5 by 0\nend").message)
        self.assertIn("must be a number", error_of('for each i in 1 to "x"\nend').message)
        self.assertIn("infinity", error_of("for each i in 1 to 1e999\nend").message)

    def test_stop_and_skip(self):
        source = "for each i in 1 to 10\n  if i == 2\n    skip\n  end\n  if i == 5\n    stop\n  end\n  say i\nend"
        self.assertEqual(run(source), "1\n3\n4\n")

    def test_stop_only_leaves_the_inner_loop(self):
        source = "for each i in 1 to 2\n  for each j in 1 to 5\n    if j == 2\n      stop\n    end\n    say i, j\n  end\nend"
        self.assertEqual(run(source), "1 1\n2 1\n")

    def test_stop_and_skip_in_while_and_repeat(self):
        self.assertEqual(run("n = 0\nwhile true\n  n += 1\n  if n > 3\n    stop\n  end\nend\nsay n"), "4\n")
        self.assertEqual(run("n = 0\nrepeat 5 times\n  n += 1\n  if n < 4\n    skip\n  end\n  say n\nend"), "4\n5\n")


class ErrorHandlingTests(unittest.TestCase):
    def test_try_catches_problems(self):
        source = 'try\n  say 1 / 0\ncatch problem\n  say "caught:", problem\nend\nsay "after"'
        self.assertEqual(run(source), "caught: I can't divide by zero.\nafter\n")

    def test_catch_without_a_name(self):
        self.assertEqual(run('try\n  say [][1]\ncatch\n  say "nope"\nend'), "nope\n")

    def test_fail(self):
        self.assertEqual(run('try\n  fail "custom"\ncatch e\n  say e\nend'), "custom\n")
        self.assertEqual(run("try\n  fail 42\ncatch e\n  say e\nend"), "42\n")
        error = error_of('fail "boom"')
        self.assertEqual(error.message, "boom")
        self.assertEqual(error.line, 1)

    def test_try_without_a_problem_skips_the_catch(self):
        self.assertEqual(run('try\n  say "fine"\ncatch\n  say "bad"\nend'), "fine\n")

    def test_problems_inside_functions_are_caught(self):
        source = "to f()\n  give 1 / 0\nend\ntry\n  f()\ncatch e\n  say e\nend"
        self.assertEqual(run(source), "I can't divide by zero.\n")

    def test_nested_try(self):
        source = 'try\n  try\n    fail "inner"\n  catch a\n    fail "outer after " + a\n  end\ncatch b\n  say b\nend'
        self.assertEqual(run(source), "outer after inner\n")

    def test_catching_runaway_recursion_leaves_things_working(self):
        source = "to f(n)\n  give f(n + 1)\nend\ntry\n  f(1)\ncatch e\n  say \"caught\"\nend\nto g()\n  give 7\nend\nsay g()"
        self.assertEqual(run(source), "caught\n7\n")

    def test_give_stop_and_skip_pass_through_try(self):
        self.assertEqual(run("to f()\n  try\n    give 1\n  catch\n    give 2\n  end\nend\nsay f()"), "1\n")
        self.assertEqual(run("for each i in 1 to 3\n  try\n    if i == 2\n      skip\n    end\n    say i\n  catch\n  end\nend"), "1\n3\n")
        self.assertEqual(run("for each i in 1 to 3\n  try\n    stop\n  catch\n  end\nend\nsay \"ok\""), "ok\n")

    def test_running_out_of_input_cannot_be_hidden(self):
        error = error_of('try\n  x = ask("?")\ncatch\n  say "hidden"\nend')
        self.assertIn("no more input", error.message)
        self.assertFalse(error.catchable)

    def test_problems_know_where_they_happened(self):
        error = error_of("say 1\nsay 2\nsay [][1]")
        self.assertEqual((error.line, error.filename), (3, "test.zest"))

    def test_trace_lists_the_calls(self):
        source = "to inner()\n  give 1 / 0\nend\nto outer()\n  give inner()\nend\nouter()"
        error = error_of(source)
        self.assertEqual([(name, line) for name, line, _ in error.trace], [("inner", 5), ("outer", 7)])
        self.assertEqual(error.line, 2)

    def test_quit(self):
        with self.assertRaises(QuitProgram) as caught:
            run("say 1\nquit(3)\nsay 2")
        self.assertEqual(caught.exception.code, 3)


class ShowTests(unittest.TestCase):
    def test_nested_values_are_written_like_code(self):
        self.assertEqual(run('say ["a", 1, true, nothing, [2], {k: "v"}]'), '["a", 1, true, nothing, [2], {"k": "v"}]\n')

    def test_quotes_inside_nested_text_are_escaped(self):
        self.assertEqual(run('say ["he said \\"hi\\""]'), '["he said \\"hi\\""]\n')

    def test_functions_print_their_names(self):
        self.assertEqual(run("to f()\nend\nsay f, length"), "<function f> <built-in length>\n")

    def test_lists_that_contain_themselves(self):
        self.assertEqual(run("a = [1]\nadd(a, a)\nsay a"), "[1, [...]]\n")

    def test_say_joins_with_spaces(self):
        self.assertEqual(run('say "a", 1, [2], nothing'), "a 1 [2] nothing\n")

    def test_text_is_plain_at_top_level_and_quoted_inside_lists(self):
        self.assertEqual(run('say "hi"\nsay ["hi"]'), 'hi\n["hi"]\n')


class ModuleTests(unittest.TestCase):
    def setUp(self):
        self.projects = []

    def tearDown(self):
        for project in self.projects:
            project.cleanup()

    def project(self, files):
        project = Project(files)
        self.projects.append(project)
        return project

    def test_use_runs_another_file(self):
        project = self.project({
            "main.zest": 'use "helpers"\nsay double(21)\n',
            "helpers.zest": "to double(n)\n  give n * 2\nend\n",
        })
        self.assertEqual(project.run("main.zest"), "42\n")

    def test_use_accepts_a_full_file_name_and_folders(self):
        project = self.project({
            "main.zest": 'use "lib/tools.zest"\nsay tool()\n',
            "lib/tools.zest": 'to tool()\n  give "tool!"\nend\n',
        })
        self.assertEqual(project.run("main.zest"), "tool!\n")

    def test_paths_are_relative_to_the_file_that_uses_them(self):
        project = self.project({
            "main.zest": 'use "lib/a"\nsay a()\n',
            "lib/a.zest": 'use "b"\nto a()\n  give b() + "a"\nend\n',
            "lib/b.zest": 'to b()\n  give "b"\nend\n',
        })
        self.assertEqual(project.run("main.zest"), "ba\n")

    def test_a_file_only_runs_once(self):
        project = self.project({
            "main.zest": 'use "once"\nuse "once"\nsay "main"\n',
            "once.zest": 'say "loaded"\n',
        })
        self.assertEqual(project.run("main.zest"), "loaded\nmain\n")

    def test_files_that_use_each_other_do_not_loop(self):
        project = self.project({
            "a.zest": 'use "b"\nsay "a"\n',
            "b.zest": 'use "a"\nsay "b"\n',
        })
        self.assertEqual(project.run("a.zest"), "b\na\n")

    def test_missing_file(self):
        project = self.project({"main.zest": 'use "nothing_here"\n'})
        with self.assertRaises(ZestRuntimeError) as caught:
            project.run("main.zest")
        self.assertIn("couldn't find the file 'nothing_here'", caught.exception.message)

    def test_problems_name_the_right_file_and_line(self):
        project = self.project({
            "main.zest": 'use "broken"\nbroken()\n',
            "broken.zest": "# header\nto broken()\n  give 1 / 0\nend\n",
        })
        with self.assertRaises(ZestRuntimeError) as caught:
            project.run("main.zest")
        error = caught.exception
        self.assertTrue(error.filename.endswith("broken.zest"))
        self.assertEqual(error.line, 3)
        self.assertEqual(error.trace[0][0], "broken")
        self.assertTrue(error.trace[0][2].endswith("main.zest"))
        self.assertIn(error.filename, project.interpreter.sources)


class DepthSettingTests(unittest.TestCase):
    def test_depth_limit_can_be_changed(self):
        interpreter, out = make_interpreter(max_depth=5)
        with self.assertRaises(ZestRuntimeError):
            interpreter.run_source("to f(n)\n  if n == 0\n    give 0\n  end\n  give f(n - 1)\nend\nf(10)", "x")


if __name__ == "__main__":
    unittest.main()
