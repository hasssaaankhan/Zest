# Zest

**A programming language you can read out loud.**

Zest is a small, complete programming language built for people who are meeting code for the first time, and for anyone who is tired of punctuation. There are no semicolons, no curly braces, no type declarations and no "truthy" surprises. Mistakes are explained in plain English, with a pointer to the exact spot and a hint for fixing them.

```zest
prices = {apple: 0.5, bread: 2.25, milk: 1.2}
cart = ["apple", "milk", "apple", "bread"]

total = 0
for each item in cart
  total += prices[item]
end

say "Items:", length(cart)
say "Total: {round(total, 2)}"
```

```text
Items: 4
Total: 4.45
```

It is written in pure Python with **no dependencies**. The whole interpreter is about 2,500 readable lines, covered by 250+ tests.

## Why Zest

- **Reads like a sentence.** `for each item in cart`, `repeat 3 times`, `to greet(name)`, `give result`, `say "Hello"`.
- **Few rules to remember.** Blocks end with `end`. Indenting never changes the meaning. One scope rule covers every name.
- **Honest about mistakes.** A typo, a missing `end`, a `=` where `==` was meant: each gets a clear message, the line, a pointer and a hint.
- **No hidden surprises.** Conditions must be `true` or `false`. Counting loops never silently count backwards. Whole numbers never overflow. Positions start at 1, like people count.
- **Complete.** Numbers, text, lists, maps, functions with defaults, closures, recursion, error handling, modules, files and a 41-function standard library.
- **Easy to understand and change.** Lexer, parser and interpreter are separate, small and documented, with the full grammar published.

## Install and run

You need Python 3.9 or newer. Download or clone this project, open a terminal in its folder, and run:

```
pip install .
zest examples/hello.zest
```

```text
Hello, world!
Nice to meet you, Ada.
```

You can also run it without installing: `python -m zest examples/hello.zest`.

| Command | What it does |
|---|---|
| `zest program.zest` | Run a program (the same as `zest run program.zest`). |
| `zest check program.zest` | Look for mistakes without running anything. |
| `zest repl` | A prompt where you type code and see the result at once. Plain `zest` does the same. |
| `zest builtins` | List every built-in function. |
| `zest --version` | Show the version. |

Programs can read what the person types (`ask`), so try the guessing game:

```
zest examples/guess.zest
```

### The prompt

```text
$ zest repl
Zest 1.0.0. Type code and press Enter.
Try:  say "Hello"      Leave with:  exit  (or press Ctrl-D)
zest> x = 5
zest> x * 2
10
zest> "Hello, " + "Ada"
"Hello, Ada"
zest> to square(n)
....>   give n * n
....> end
zest> square(12)
144
```

Blocks continue on the next line until you finish them with `end`. Names you create stay available for the rest of the session.

## The language in two minutes

```zest
# Names, numbers and text
name = "Ada"
age = 36
say "{name} will be {age + 1} next year."

# Lists count from 1
colors = ["red", "green", "blue"]
add(colors, "pink")
say colors[1], colors[-1], length(colors)    # red pink 4

# Maps
person = {name: "Ada", city: "London"}
person.age = 36
say person.name, person["city"]

# Decisions
if age >= 18 and age < 65
  say "adult"
else if age >= 65
  say "senior"
else
  say "child"
end

# Loops
for each color in colors
  say "I like", color
end
for each i in 5 to 1 by -1
  say i
end
repeat 3 times
  say "hip"
end

# Functions, with default values
to greet(who, greeting = "Hello")
  give "{greeting}, {who}!"
end
say greet("Ada")

# Problems you can catch
try
  say 10 / 0
catch problem
  say "Caught:", problem
end
```

Run the complete tour with `zest examples/tour.zest`. Every part of the language is explained in [docs/LANGUAGE.md](docs/LANGUAGE.md).

## Mistakes explain themselves

```text
Problem in typo.zest, line 2:
  I don't know anything called 'nmae'.

  2 | say nmae
    |     ^^^^

  Hint: Did you mean 'name'?
```

```text
Can't read equals.zest, line 2:
  I expected the line to end here, but found '='.

  2 | if age = 18
    |        ^

  Hint: To compare two values, use '=='. A single '=' stores a value.
```

A problem inside nested functions shows how it got there:

```text
Problem in trace.zest, line 2:
  I can't divide by zero.

  2 |   give n / 0
    |          ^

  (inside half(), called from line 5)
  (inside run(), called from line 7)
```

Words from other languages get a nudge: `print("hi")` says *Use say*, and `return`, `def`, `null`, `elif`, `let`, `break` and more do the same.

## If you already know a language

Python, JavaScript and C are mentioned only as a map to help you find your way; Zest copies none of them.

| Idea | Zest | Python | JavaScript | C |
|---|---|---|---|---|
| Show something | `say "hi"` | `print("hi")` | `console.log("hi")` | `printf("hi\n");` |
| Count 1 to 5 | `for each i in 1 to 5` | `for i in range(1, 6):` | `for (let i = 1; i <= 5; i++)` | `for (int i = 1; i <= 5; i++)` |
| Function | `to add(a, b)` ... `end` | `def add(a, b):` | `function add(a, b) {}` | `int add(int a, int b) {}` |
| No value | `nothing` | `None` | `null` | `NULL` |
| First item | `xs[1]` | `xs[0]` | `xs[0]` | `xs[0]` |

The full comparison is in [docs/LANGUAGE.md](docs/LANGUAGE.md#coming-from-another-language), including the five places where Zest deliberately does things differently.

## Use it from Python

```python
from zest import Interpreter, ZestError, format_error

output = []
interpreter = Interpreter(write=output.append)
try:
    interpreter.run_source('say "Hello from Zest"\nsay 6 * 7', "inline.zest")
except ZestError as error:
    print(format_error(error, interpreter.sources))

print("".join(output))
```

```text
Hello from Zest
42
```

`Interpreter(write=..., read_line=...)` lets you capture output and provide input, which is how the test suite runs programs. Names survive between calls to `run_source`, so one interpreter can run a program in pieces.

## Standard library

Forty-one built-in functions cover the everyday work, and `zest builtins` lists them with a one-line description each:

| Area | Functions |
|---|---|
| Show, ask, convert | `ask` `text` `number` `kind` |
| Lists and maps | `length` `add` `insert` `remove` `keys` `values` `copy` `sorted` `reversed` `range` `slice` `find` |
| Text | `split` `join` `replace` `upper` `lower` `trim` `starts_with` `ends_with` |
| Numbers | `abs` `round` `floor` `ceiling` `sqrt` `min` `max` `sum` `random` `pick` `seed` |
| Time, files, quitting | `now` `wait` `read_file` `write_file` `file_exists` `quit` |

`round` rounds halves up, the way people expect: `round(2.5)` is `3`.

## Examples

| File | What it shows |
|---|---|
| `examples/hello.zest` | The first program. |
| `examples/tour.zest` | A tour of the whole language. |
| `examples/fizzbuzz.zest` | Decisions inside a loop. |
| `examples/fibonacci.zest` | Recursion, and a faster loop. |
| `examples/primes.zest` | Functions, counting loops and early `give`. |
| `examples/wordcount.zest` | Maps, `split` and `sorted`. |
| `examples/bank.zest` | Functions, maps, `fail` and `try`. |
| `examples/guess.zest` | A game with input, `random` and `stop`. |

The tests run every example and compare it with its expected output.

## Speed

Zest is a tree-walking interpreter written in Python, so it is much slower than Python itself. Measured on one machine with Python 3.12:

| Program | Zest | Plain Python |
|---|---|---|
| `fib(24)`, about 150,000 function calls | 0.75 s | 0.005 s |
| A loop of 1,000,000 additions | 1.6 s | not measured |

That is roughly 150 times slower for call-heavy code. It is fine for learning, scripts and small tools, and not suitable for heavy computation. Your numbers will differ.

## Limits

- No classes or inheritance. Maps and functions cover the same ground at this size.
- No named arguments in calls; values go in order.
- No sandbox. `read_file`, `write_file` and `use` can reach any file the person running Zest can reach, so only run programs you trust.
- Function calls can nest 500 levels deep. Past that, Zest stops with an explanation.
- Programs are read as UTF-8 text.
- There is no formatter or editor support yet.

## Project layout

```
zest/
  lexer.py        text -> tokens
  parser.py       tokens -> program tree (recursive descent)
  nodes.py        the shapes of the tree
  interpreter.py  runs the tree
  values.py       showing, comparing and describing values
  builtins.py     the standard library
  errors.py       error classes and message layout
  cli.py          the zest command
examples/         eight programs, all tested
docs/
  LANGUAGE.md     the complete language reference
  DESIGN.md       why it is built this way, and the full grammar
tests/            250+ tests
tools/
  mutation_check.py   breaks the interpreter on purpose to test the tests
```

## Development

Run the tests:

```
python -m unittest
```

They cover the lexer, the parser, the language itself, every built-in (including a stress run that throws odd values at all of them), the exact layout of error messages, the command line and the prompt, every example, and the documentation (every built-in is documented, every code block parses, and the error messages shown in the docs are the real ones).

To check that the tests are strong, run the mutation check:

```
python tools/mutation_check.py
```

It breaks the interpreter on a throwaway copy in about twenty different ways, such as making positions start at 0 or letting `if` accept any value, and reports any break that no test notices. It should end with `survivors: []`. Your files are never touched.

The tests run on Python 3.9 to 3.13 through GitHub Actions (see `.github/workflows/tests.yml`).

## Documentation

- [docs/LANGUAGE.md](docs/LANGUAGE.md): every feature, with examples.
- [docs/DESIGN.md](docs/DESIGN.md): the design decisions, how the interpreter works, the full grammar, and how to add a built-in.

## Contributing

Issues and pull requests are welcome. Please keep Zest small and dependency-free, add a test with every change, update the documentation when behaviour changes, and run `python -m unittest` and `python tools/mutation_check.py` before you open a pull request.

## License

MIT. See the `LICENSE` file.
