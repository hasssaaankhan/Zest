import io
import os
import random
import unittest

from zest.interpreter import Interpreter

EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "examples")

GOLDEN = {
    "hello": "Hello, world!\nNice to meet you, Ada.\n",
    "fizzbuzz": ("1\n2\nFizz\n4\nBuzz\nFizz\n7\n8\nFizz\nBuzz\n11\nFizz\n13\n14\nFizzBuzz\n"
                 "16\n17\nFizz\n19\nBuzz\n"),
    "fibonacci": "The first ten: 0, 1, 1, 2, 3, 5, 8, 13, 21, 34\nThe 90th: 2880067194370816120\n",
    "wordcount": ("brown 1\ndog 1\nend 1\nfox 1\njumps 1\nlazy 1\nover 1\nquick 1\nthe 3\n"),
    "bank": ("Balance: 150\nCould not withdraw: Not enough money: Ada has only 150.\n"
             "Balance now: 120\n"),
    "primes": "Primes up to 50: 2 3 5 7 11 13 17 19 23 29 31 37 41 43 47\n",
    "tour": (
        "Welcome to Zest version 1!\n10 4 21 3.5 1 1024\n0.3\nHELLO 5 h o\nhahaha\nell\n"
        '["red", "green", "blue", "pink"]\nred pink 4\ntrue\nAda 36\n["name", "age", "city"]\n'
        "adult\nI like red\nI like green\nI like blue\nI like pink\n3\n2\n1\nagain\nagain\n"
        "n is 1\nn is 3\n12 5\ncounted 3\ncaught: I can't divide by zero.\n"),
}


def run_example(name, stdin="", seed=None):
    out = io.StringIO()
    interpreter = Interpreter(write=out.write, read_line=io.StringIO(stdin).readline, flush=lambda: None)
    if seed is not None:
        interpreter.rng.seed(seed)
    interpreter.run_file(os.path.join(EXAMPLES, name + ".zest"))
    return out.getvalue()


class ExampleTests(unittest.TestCase):
    def test_every_example_has_a_golden_answer(self):
        found = {f[:-5] for f in os.listdir(EXAMPLES) if f.endswith(".zest")}
        self.assertEqual(found, set(GOLDEN) | {"guess"})

    def test_examples_print_what_they_should(self):
        for name, expected in GOLDEN.items():
            with self.subTest(example=name):
                self.assertEqual(run_example(name), expected)

    def test_guessing_game(self):
        secret = random.Random(4).randint(1, 20)
        self.assertEqual(secret, 8)
        answers = "abc\n3\n25\n8\n"
        expected = ("I am thinking of a number from 1 to 20.\n"
                    "Your guess? Please type a number.\n"
                    "Your guess? Too low.\n"
                    "Your guess? Too high.\n"
                    "Your guess? You got it in 3 tries!\n")
        self.assertEqual(run_example("guess", stdin=answers, seed=4), expected)


if __name__ == "__main__":
    unittest.main()
