# How Zest is designed

This document explains why Zest looks the way it does, how the interpreter works, and how to change it safely. For how to *use* the language, read [LANGUAGE.md](LANGUAGE.md).

## Goals

1. **Readable out loud.** Most lines should sound like a plain sentence.
2. **Few rules.** Every rule you must remember is a chance to get it wrong, so there are few.
3. **Mistakes explain themselves.** A beginner should never have to decode an error message.
4. **Small enough to understand.** The whole interpreter is about 2,500 lines of ordinary Python with no dependencies.

## Decisions and the reasons behind them

| Decision | Why | What it costs |
|---|---|---|
| Blocks end with `end` | Unlike indentation, a missing `end` is detected and reported. Unlike braces, it reads as a word. Pasted or badly indented code still works. | One more word per block. |
| Positions start at 1 | It matches how people count. `xs[1]` is the first item and `xs[-1]` is the last. Asking for `xs[0]` gets a message that explains this. | Differs from most programming languages, so people moving between languages must remember. |
| `if` and `while` only accept `true` or `false` | "Truthy" rules (is `0` false? is `"0"`?) are a famous source of bugs. A clear error is kinder than a surprise. | Writing `if length(name) > 0` instead of `if name`. |
| `for each i in 1 to n` counts up only; use `by -1` to count down | When the end comes from a calculation, a loop that silently turns around and counts backwards causes off-by-one disasters. Found while writing the prime-number example. | Counting down needs `by -1`. |
| One scope rule: setting a name updates the nearest existing one, or creates a new one in the current function | Easy to say, easy to predict, and no `var`/`let`/`global` words. | A typo in a name inside a function silently makes a new name; the "did you mean" hints soften this for reads. |
| Real closures, no classes | Closures plus maps cover what beginners need. Classes would double the size of the language. | No inheritance or method syntax. |
| `+` joins when either side is text | `"Score: " + 10` does what a person expects. | The only place Zest converts a value without being asked. |
| Whole numbers never overflow, `6 / 3` is `2` | One kind of number, with no surprises about size. | Slower than fixed-size integers. |
| Interpolation uses `{ }` | Short and familiar. | Real braces in text need `\{`. |
| `ask()` running out of input cannot be caught by `try` | Otherwise a loop that keeps asking (and catches the failure) never ends. This bug was found while testing the guessing game. | A program cannot recover from closed input. |
| Defaults are worked out on every call | Avoids the classic trap where one shared default list collects values across calls. | A tiny bit more work per call. |
| Map keys are text or numbers | Lists and maps as keys cannot be compared in a sensible, cheap way. Booleans would collide with 1 and 0. | Less flexible than some languages. |
| `use` runs a file once, in the shared scope | The simplest possible module system. | No namespaces; name clashes are possible. |
| Errors carry line, column, a pointer, a hint and a call trace | Checked by tests, so the quality cannot quietly decay. | More code in the interpreter. |
| Words from other languages get a hint (`print`, `return`, `elif`, `null`, ...) | People will type them. A nudge is faster than a manual. | A small table to maintain. |

## How it works

```
 source text
     |
     v
  Lexer          characters -> tokens (words, numbers, text, symbols, line ends)
     |            - tracks brackets, so lines can continue inside ( ) [ ] { }
     |            - splits text into plain pieces and {code} pieces
     v
  Parser         tokens -> a tree of statements and expressions (recursive descent)
     |            - checks give / stop / skip are in a sensible place
     |            - recognises words from other languages and suggests the Zest way
     v
  Interpreter    walks the tree and does what it says
     |            - Environment objects hold names (one per function call)
     |            - control flow (give, stop, skip) travels as private exceptions
     v
  output, or an error that is formatted for people (errors.py)
```

### The files

| File | Job |
|---|---|
| `zest/lexer.py` | Turns text into tokens. Keeps line and column for every token. Handles text escapes and `{ }` pieces. |
| `zest/parser.py` | Recursive descent. One method per grammar rule, so the code reads like the grammar below. |
| `zest/nodes.py` | Plain data classes for every kind of statement and expression. |
| `zest/interpreter.py` | `Environment` (where names live) and `Interpreter` (runs the tree). |
| `zest/values.py` | How values are shown, compared and described; list positions; counting ranges. |
| `zest/builtins.py` | The built-in functions, registered with one decorator each. |
| `zest/errors.py` | The error classes and `format_error`, which turns an error into the message a person sees. |
| `zest/cli.py` | The `zest` command: run, check, repl, builtins. |

### Values

Zest values are plain Python values, which keeps the interpreter small:

| Zest | Python |
|---|---|
| number | `int` or `float` (booleans are not numbers) |
| text | `str` |
| boolean | `bool` |
| nothing | `None` |
| list | `list` |
| map | `dict` |
| function | `Function` (made with `to`) or `Builtin` |

Because `bool` is a kind of `int` in Python, every number check in the code goes through `is_number`, which excludes booleans. A test makes sure `true == 1` is `false`.

### How errors find their place

Every node in the tree knows its line and column. The code that evaluates a node is wrapped so that if a problem is raised without a location, the node being evaluated fills it in. Because the innermost node is wrapped first, the location is always as specific as possible. Built-in functions and operators can therefore raise plain errors without knowing where they are.

When a problem passes out of a function call, that call is added to the error's trace. The formatter collapses identical neighbours, so a runaway recursion prints one line saying "400 times in a row", not four hundred.

### Scope

Each function call gets a fresh `Environment` whose parent is the environment where the function was *made* (that is what makes closures work). Blocks such as `if` and loops do not create a scope. Built-in functions live in a root environment that assignment never writes to, so `length = 5` creates a new name instead of damaging the built-in.

### Calls and the depth limit

A call allows up to 500 levels of nesting (`MAX_DEPTH`). Each level uses roughly a dozen Python frames, so the interpreter raises Python's recursion limit to 12,000 when it starts. The depth is tracked with `try/finally`, so it is always correct after a problem unwinds the stack.

## Grammar

This is the complete grammar, in a simple notation: `{ x }` means zero or more, `[ x ]` means optional, and `|` means "or". `NEWLINE` is the end of a line. Blank lines and comments are removed before parsing, and line ends inside brackets are ignored.

```text
program     = { statement } ;

statement   = say | def | give | if | while | repeat | for
            | stop | skip | try | fail | use | simple ;

say         = "say" [ expression { "," expression } ] NEWLINE ;
def         = "to" NAME "(" [ param { "," param } ] ")" NEWLINE block "end" NEWLINE ;
param       = NAME [ "=" expression ] ;
give        = "give" [ expression ] NEWLINE ;
if          = "if" expression NEWLINE block
              { "else" "if" expression NEWLINE block }
              [ "else" NEWLINE block ] "end" NEWLINE ;
while       = "while" expression NEWLINE block "end" NEWLINE ;
repeat      = "repeat" expression "times" NEWLINE block "end" NEWLINE ;
for         = "for" "each" NAME "in" expression [ "to" expression [ "by" expression ] ]
              NEWLINE block "end" NEWLINE ;
stop        = "stop" NEWLINE ;
skip        = "skip" NEWLINE ;
try         = "try" NEWLINE block "catch" [ NAME ] NEWLINE block "end" NEWLINE ;
fail        = "fail" expression NEWLINE ;
use         = "use" TEXT NEWLINE ;
simple      = expression [ ( "=" | "+=" | "-=" | "*=" | "/=" ) expression ] NEWLINE ;

block       = { statement } ;

expression  = or ;
or          = and { "or" and } ;
and         = not { "and" not } ;
not         = "not" not | comparison ;
comparison  = sum [ ( "==" | "!=" | "<" | ">" | "<=" | ">=" | "in" ) sum ] ;
sum         = product { ( "+" | "-" ) product } ;
product     = unary { ( "*" | "/" | "%" ) unary } ;
unary       = "-" unary | power ;
power       = postfix [ "^" unary ] ;
postfix     = primary { "(" [ args ] ")" | "[" expression "]" | "." NAME } ;
args        = expression { "," expression } [ "," ] ;
primary     = NUMBER | TEXT | "true" | "false" | "nothing" | NAME
            | "(" expression ")" | list | map ;
list        = "[" [ expression { "," expression } [ "," ] ] "]" ;
map         = "{" [ entry { "," entry } [ "," ] ] "}" ;
entry       = ( NAME | expression ) ":" expression ;
```

Rules the grammar cannot show:

- In `simple`, an assignment target must be a name, a position (`xs[1]`) or a field (`p.name`). Without an assignment, the expression must be a call (the prompt, `zest repl`, also accepts bare values).
- In `entry`, a plain `NAME` followed by `:` is a text key. Any other key is an expression.
- Comparisons do not chain: `a < b < c` is a syntax error with a hint.
- `give` is only allowed inside a function. `stop` and `skip` are only allowed inside a loop, and a function body starts a fresh "not in a loop" context.
- `times`, `each` and `by` are ordinary names that act as special words only in the spot shown above.
- Text can contain `{ expression }` pieces, which are parsed with the same grammar.

## Adding a built-in function

1. Write a function in `zest/builtins.py` and register it. The first argument is always the interpreter (use it for input, output and random numbers):

   ```python
   @builtin("shout", "shout(text)", "The text in capitals with an exclamation mark.", 1, 1)
   def _shout(ctx, text):
       return _text("shout", text).upper() + "!"
   ```

2. Check argument kinds with the `_text`, `_number`, `_whole`, `_list` and `_map` helpers, and raise `ZestRuntimeError` (through `_fail`) with a plain-English message. Never let a Python exception escape; a test throws odd values at every built-in to make sure none does.
3. Add a row to the right table in `docs/LANGUAGE.md` using exactly the usage text, and add tests. The docs test fails until the function is documented.

## Testing

Run everything with `python -m unittest`. The tests are grouped by what they protect:

| File | What it checks |
|---|---|
| `tests/test_lexer.py` | Tokens, text escapes, `{ }` pieces, and every lexing problem message. |
| `tests/test_parser.py` | Precedence, shapes, and every syntax problem with its hint. |
| `tests/test_language.py` | The behaviour of the language: scope, closures, lists, maps, operators, loops, `try`, modules. |
| `tests/test_builtins.py` | Every built-in, its limits, and a stress run that throws odd values at all of them. |
| `tests/test_errors.py` | The exact layout of error messages. |
| `tests/test_cli.py` | The command line and the interactive prompt. |
| `tests/test_examples.py` | Every program in `examples/` against its expected output. |
| `tests/test_docs.py` | Every built-in is documented, every code block in the docs is valid Zest, and the error messages shown in the docs are the real ones. |

`tools/mutation_check.py` goes one step further. It breaks the interpreter on purpose in about twenty ways (for example, making positions start at 0, or letting `if` accept any value), on a throwaway copy, and reports any break the tests fail to notice. It found real gaps while this project was being built, and it should report `survivors: []`.

## Performance

Zest is a tree-walking interpreter written in Python, so it is much slower than Python itself. Measured on one machine with Python 3.12: `fib(24)` (about 150,000 calls) takes 0.75 seconds in Zest and about 0.005 seconds in plain Python; a loop of one million additions takes about 1.6 seconds. Speed was traded for clarity on purpose. If speed ever matters, the natural next step is to compile the tree into Python closures, which keeps the same grammar and behaviour.

## Ideas that are deliberately not built

- Classes, inheritance and modules with their own names.
- Named arguments for function calls.
- A formatter and editor support (syntax highlighting, a language server).
- A compiler to bytecode or to Python for speed.
