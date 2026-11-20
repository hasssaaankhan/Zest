# The Zest language

This is the complete reference. Everything here works exactly as written, and the examples are checked by the project's tests.

If you are new to programming, read it top to bottom. If you already program, jump to [Coming from another language](#coming-from-another-language).

## Contents

1. [Hello](#hello)
2. [Values](#values)
3. [Names](#names)
4. [Numbers and operators](#numbers-and-operators)
5. [Text](#text)
6. [Lists](#lists)
7. [Maps](#maps)
8. [Decisions](#decisions)
9. [Loops](#loops)
10. [Functions](#functions)
11. [Problems you can catch](#problems-you-can-catch)
12. [Splitting a program into files](#splitting-a-program-into-files)
13. [Built-in functions](#built-in-functions)
14. [Special words](#special-words)
15. [Friendly problem messages](#friendly-problem-messages)
16. [Coming from another language](#coming-from-another-language)
17. [Limits](#limits)

## Hello

```zest
say "Hello, world!"
```

A program is a list of lines. Each line does one thing. There are no semicolons, no curly braces and no types to write. A line that starts with `#` is a comment, and Zest ignores it:

```zest
# This is a comment
say "This runs"   # so does this, and this comment is ignored
```

Blocks (the lines inside an `if`, a loop or a function) end with the word `end`. Indenting is not required, but two spaces make programs easier to read.

## Values

| Kind | Examples | Notes |
|---|---|---|
| number | `42`, `3.5`, `-7`, `1e3` | Whole numbers can be as big as you like. |
| text | `"hello"`, `'hello'` | Either kind of quote works. |
| boolean | `true`, `false` | The only values `if` and `while` accept. |
| list | `[1, 2, 3]` | An ordered row of values. |
| map | `{name: "Ada", age: 36}` | Values stored under names (keys). |
| function | made with `to` | Functions are values, so you can store and pass them. |
| nothing | `nothing` | "No value here". A function with no `give` returns it. |

Ask what kind a value is with `kind(value)`.

## Names

A name holds a value. Create or change one with `=`:

```zest
score = 10
score = score + 5
name = "Ada"
```

Names start with a letter or `_` and can contain letters, digits and `_`. Letters from any language work. Names are case sensitive: `Score` and `score` are different.

The compound forms change a name in place:

```zest
score += 1    # same as: score = score + 1
score -= 2
score *= 3
score /= 4
```

### Where names live (scope)

Names made inside a function belong to that function. One rule decides everything:

> Setting a name **updates the nearest existing name** with that spelling, or **creates a new one** in the current function.

```zest
total = 0

to add_to_total(amount)
  total += amount      # total already exists outside, so this updates it
  note = "added"       # note is new, so it only exists inside this function
end

add_to_total(5)
say total              # 5
```

Function parameters are always new names inside the function. Built-in functions can never be changed by accident: if you write `length = 5`, you get your own `length`, and the built-in one is untouched.

## Numbers and operators

| Operator | Meaning | Example | Result |
|---|---|---|---|
| `+` | add | `7 + 3` | `10` |
| `-` | subtract | `7 - 3` | `4` |
| `*` | multiply | `7 * 3` | `21` |
| `/` | divide | `7 / 2` | `3.5` |
| `%` | remainder | `7 % 3` | `1` |
| `^` | power | `2 ^ 10` | `1024` |

Good to know:

- `6 / 3` is `2`, not `2.0`. Whole results stay whole, and whole numbers never lose digits.
- `%` follows the sign of the number on the right: `-7 % 3` is `2`.
- Dividing by zero is a problem you can read and catch, not a crash.
- Decimal results are shown with up to 15 digits, so `0.1 + 0.2` shows `0.3`.

### Order of operations

From first to last:

| Order | Operators |
|---|---|
| 1 | brackets `( )`, calls `f(x)`, positions `x[1]`, fields `x.name` |
| 2 | `^` (right to left: `2 ^ 3 ^ 2` is `512`) |
| 3 | unary minus `-x` (so `-2 ^ 2` is `-4`) |
| 4 | `*` `/` `%` |
| 5 | `+` `-` |
| 6 | `==` `!=` `<` `>` `<=` `>=` `in` |
| 7 | `not` |
| 8 | `and` |
| 9 | `or` |

When in doubt, add brackets.

## Text

Write text in double or single quotes. Use the other kind of quote to put a quote inside:

```zest
say "It's easy"
say 'She said "hi"'
```

### Putting values into text

Put any calculation inside `{ }`:

```zest
name = "Ada"
age = 36
say "{name} will be {age + 1} next year."
say "Shout: {upper(name)}!"
say "Total: {price * count}"
```

To write a real brace, put a backslash before it: `"\{like this\}"`.

### Escapes

| Write | Get |
|---|---|
| `\n` | a new line |
| `\t` | a tab |
| `\"` and `\'` | a quote |
| `\\` | a backslash |
| `\{` and `\}` | a curly brace |

### Joining and repeating

```zest
say "Hello, " + "world"      # Hello, world
say "Score: " + 10           # Score: 10   (if either side is text, the result is text)
say "ha" * 3                 # hahaha
```

### Letters by position

Positions start at 1. Negative positions count from the end:

```zest
word = "hello"
say word[1]      # h
say word[-1]     # o
say slice(word, 2, 4)    # ell
```

Text cannot be changed letter by letter. Build a new text instead:

```zest
word = "J" + slice(word, 2, -1)
```

## Lists

```zest
colors = ["red", "green", "blue"]
say colors[1]            # red   (positions start at 1)
say colors[-1]           # blue  (negative counts from the end)
colors[2] = "yellow"     # change an item
add(colors, "pink")      # add at the end
say length(colors)       # 4
say "red" in colors      # true
```

**Why positions start at 1.** It matches how people count: the first item is item 1, and the last is `[-1]`. Asking for position 0 gives a message that explains this.

Lists are shared, not copied. If two names point at one list, a change through either name shows through both:

```zest
a = [1, 2]
b = a
add(b, 3)
say a          # [1, 2, 3]

c = copy(a)    # c is a separate list now
add(c, 4)
say a          # still [1, 2, 3]
```

Joining lists with `+` makes a new list: `[1] + [2, 3]` is `[1, 2, 3]`.

## Maps

A map stores values under keys. Keys are text or numbers.

```zest
person = {name: "Ada", age: 36}
say person.name              # Ada
say person["age"]            # 36
person.city = "London"       # add or change a field
person.age += 1
say keys(person)             # ["name", "age", "city"]
say "name" in person         # true
```

In a map literal, a plain word before the `:` is the key as text. For other keys, write a quoted text or number, or put a calculation in brackets:

```zest
key = "color"
settings = {"font size": 12, 7: "seven", (key): "blue"}
```

Reading a key that is not there gives a clear message, and suggests a close match if there is one. Check first with `in`:

```zest
if "email" in person
  say person.email
end
```

Maps keep their keys in the order you added them.

## Decisions

```zest
if age >= 18
  say "adult"
else if age >= 13
  say "teenager"
else
  say "child"
end
```

There is one `end` for the whole chain.

Conditions must be exactly `true` or `false`. Zest does not guess that `0` or `""` means "no". Write the comparison you mean:

```zest
if length(name) > 0
  say "Hello, {name}"
end
```

### Comparing

| Write | Meaning |
|---|---|
| `a == b` | equal |
| `a != b` | not equal |
| `a < b`, `a > b`, `a <= b`, `a >= b` | order (two numbers or two texts) |
| `x in things` | `x` is in the list, text or map |

`==` never mixes kinds: `1 == "1"` and `1 == true` are both `false`. Lists and maps are equal when their contents are equal.

Comparisons do not chain. Write `x > 1 and x < 10`, not `1 < x < 10`.

### And, or, not

```zest
if age >= 18 and has_ticket
  say "Welcome"
end
if not has_ticket or banned
  say "Sorry"
end
```

`and` and `or` stop as soon as the answer is known, so `false and (1 / 0 == 1)` is `false` with no problem.

## Loops

### repeat

```zest
repeat 3 times
  say "hello"
end
```

### while

```zest
n = 0
while n < 3
  n += 1
end
```

### for each

Go through a list, the letters of a text, or the keys of a map:

```zest
for each color in ["red", "green"]
  say color
end

for each letter in "abc"
  say letter
end

for each key in {a: 1, b: 2}
  say key
end
```

The loop works on a copy of the list, so adding to the list inside the loop is safe.

### Counting

```zest
for each i in 1 to 5
  say i
end
```

Both ends are included. Counting goes **up only**. To count down, say how with a negative step. To skip numbers, use `by`:

```zest
for each i in 5 to 1 by -1
  say i
end

for each i in 0 to 100 by 25
  say i          # 0, 25, 50, 75, 100
end

for each i in 5 to 1
  say i          # runs zero times: 5 is already past 1
end
```

A loop that runs zero times is deliberate. When the end comes from a calculation (`2 to floor(sqrt(n))`), it must not silently turn around and count the other way.

`range(from, to)` gives the same numbers as a list.

### stop and skip

`stop` leaves the loop. `skip` jumps to the next round:

```zest
for each n in 1 to 10
  if n % 2 == 0
    skip
  end
  if n > 7
    stop
  end
  say n          # 1, 3, 5, 7
end
```

`stop` and `skip` only work inside a loop, and only affect the loop they are in.

## Functions

Make a function with `to`. Give a value back with `give`:

```zest
to area(width, height)
  give width * height
end

say area(3, 4)     # 12
```

A function that reaches its `end` without `give` returns `nothing`.

### Default values

```zest
to greet(name, greeting = "Hello")
  say "{greeting}, {name}!"
end

greet("Ada")             # Hello, Ada!
greet("Ada", "Welcome")  # Welcome, Ada!
```

Parameters with defaults must come last. A default is worked out fresh on each call, so `items = []` is a new empty list every time.

### Functions are values

```zest
to twice(f, x)
  give f(f(x))
end

to add_one(n)
  give n + 1
end

say twice(add_one, 5)    # 7
```

A function remembers the names around the place where it was made (a closure):

```zest
to make_counter()
  count = 0
  to next()
    count += 1
    give count
  end
  give next
end

counter = make_counter()
counter()
counter()
say counter()      # 3
```

### Functions that call themselves

```zest
to factorial(n)
  if n <= 1
    give 1
  end
  give n * factorial(n - 1)
end

say factorial(20)    # 2432902008176640000
```

A function can call itself up to 500 levels deep. Past that, Zest stops with a message that explains the likely cause (usually a missing stopping `if`).

## Problems you can catch

```zest
try
  say 10 / 0
catch problem
  say "That did not work: {problem}"
end
```

If anything inside `try` goes wrong, Zest jumps to `catch` and puts the message in the name you chose (the name is optional). Problems from functions called inside the `try` are caught too.

Raise your own problem with `fail`:

```zest
to withdraw(balance, amount)
  if amount > balance
    fail "Not enough money."
  end
  give balance - amount
end
```

Two things `try` does **not** hide:

- `give`, `stop` and `skip` work as normal inside a `try`.
- Running out of input in `ask()` always ends the program. Otherwise a loop that keeps asking could never finish.

## Splitting a program into files

```zest
use "helpers"          # runs helpers.zest (the .zest ending is optional)
use "lib/tools.zest"   # folders work too
```

- Paths are relative to the file that contains the `use`.
- The file runs once, even if several files use it.
- Everything the file defines becomes available to the program.

## Built-in functions

Zest comes with these functions. List them any time with `zest builtins`.

### Show, ask and convert

| Function | What it does |
|---|---|
| `ask(question)` | Show a question, wait for the person to type, and give back what they typed as text. |
| `text(value)` | Turn any value into text. |
| `number(value)` | Turn text such as "42" into a number. |
| `kind(value)` | The kind of a value: number, text, boolean, list, map, function or nothing. |

### Lists and maps

| Function | What it does |
|---|---|
| `length(thing)` | How many characters in text, items in a list, or entries in a map. |
| `add(list, item)` | Put an item at the end of a list. |
| `insert(list, position, item)` | Put an item into a list at a position (1 is the front). |
| `remove(thing, where)` | Take an item out of a list (by position) or a map (by key), and give it back. |
| `keys(map)` | A list of the keys in a map. |
| `values(map)` | A list of the values in a map. |
| `copy(thing)` | Make a separate copy of a list or map. |
| `sorted(list)` | A new list with the items in order (all numbers or all text). |
| `reversed(thing)` | A new list, or text, in the opposite order. |
| `range(from, to)  or  range(from, to, step)` | A list of numbers from one number to another, both included. Use a negative step to count down. |
| `slice(thing, from, to)` | Part of a list or text, from one position to another, both included. |
| `find(thing, item)` | The position of an item in a list, or of a piece of text in text. 0 means not found. |

### Text

| Function | What it does |
|---|---|
| `split(text)  or  split(text, separator)` | Cut text into a list of pieces. With no separator it cuts at spaces. |
| `join(list)  or  join(list, separator)` | Glue the items of a list into one text. |
| `replace(text, old, new)` | Swap every old piece of text for a new one. |
| `upper(text)` | The text in CAPITAL letters. |
| `lower(text)` | The text in small letters. |
| `trim(text)` | The text without spaces at the start and end. |
| `starts_with(text, start)` | True if the text begins with the given piece. |
| `ends_with(text, end)` | True if the text finishes with the given piece. |

### Numbers

| Function | What it does |
|---|---|
| `abs(number)` | The number without its minus sign. |
| `round(number)  or  round(number, places)` | Round to the nearest whole number, or to some decimal places. Halves round up. |
| `floor(number)` | Round down to a whole number. |
| `ceiling(number)` | Round up to a whole number. |
| `sqrt(number)` | The square root of a number. |
| `min(list)  or  min(a, b, ...)` | The smallest value. |
| `max(list)  or  max(a, b, ...)` | The biggest value. |
| `sum(list)` | Add up all the numbers in a list. |
| `random()  or  random(from, to)` | A random decimal between 0 and 1, or a random whole number from one number to another (both included). |
| `pick(list)` | A random item from a list. |
| `seed(number)` | Make random numbers repeat the same way every run. |

### Time, files and quitting

| Function | What it does |
|---|---|
| `now()` | The current time, as the number of seconds since 1970. |
| `wait(seconds)` | Pause the program for some seconds. |
| `read_file(path)` | All the text inside a file. |
| `write_file(path, text)` | Save text into a file (replacing what was there). |
| `file_exists(path)` | True if a file or folder with that name exists. |
| `quit()  or  quit(code)` | Stop the program right now. |

## Special words

These cannot be used as names:

`say` `to` `give` `if` `else` `end` `repeat` `while` `for` `stop` `skip` `and` `or` `not` `true` `false` `nothing` `try` `catch` `fail` `use` `in`

Three more words are special only in one place, so you can still use them as names elsewhere: `times` (in `repeat 3 times`), `each` (in `for each`) and `by` (in `1 to 10 by 2`).

## Friendly problem messages

Every problem says what happened, shows the line, points at the spot, and suggests a fix when it can.

A typo:

```text
Problem in typo.zest, line 2:
  I don't know anything called 'nmae'.

  2 | say nmae
    |     ^^^^

  Hint: Did you mean 'name'?
```

`=` where `==` was meant:

```text
Can't read equals.zest, line 2:
  I expected the line to end here, but found '='.

  2 | if age = 18
    |        ^

  Hint: To compare two values, use '=='. A single '=' stores a value.
```

The wrong number of values:

```text
Problem in arity.zest, line 4:
  area() needs 2 values, but you gave 1.

  4 | say area(3)
    |     ^^^^

  Hint: It was made like this: to area(w, h)
```

A problem deep inside functions shows how it got there:

```text
Problem in trace.zest, line 2:
  I can't divide by zero.

  2 |   give n / 0
    |          ^

  (inside half(), called from line 5)
  (inside run(), called from line 7)
```

Words from other languages get a nudge. `print("hi")` says: *Use say: say "Hello"*. `return`, `def`, `null`, `elif`, `let`, `break` and many more do the same.

## Coming from another language

Python, JavaScript and C are the three languages Zest is most often compared with. They are shown here only as a map: Zest copies none of them. These rows are approximate; they show the idea, not every detail.

| Idea | Zest | Python | JavaScript | C |
|---|---|---|---|---|
| Show something | `say "hi"` | `print("hi")` | `console.log("hi")` | `printf("hi\n");` |
| Make a name | `x = 5` | `x = 5` | `let x = 5;` | `int x = 5;` |
| Comment | `# note` | `# note` | `// note` | `// note` |
| Decision | `if x > 3` ... `end` | `if x > 3:` | `if (x > 3) { }` | `if (x > 3) { }` |
| Another way | `else if` | `elif` | `else if` | `else if` |
| Count 1 to 5 | `for each i in 1 to 5` | `for i in range(1, 6):` | `for (let i = 1; i <= 5; i++)` | `for (int i = 1; i <= 5; i++)` |
| Each item | `for each x in xs` | `for x in xs:` | `for (const x of xs)` | index loop |
| Repeat | `repeat 3 times` | `for _ in range(3):` | `for (let i = 0; i < 3; i++)` | index loop |
| Function | `to add(a, b)` ... `give a + b` ... `end` | `def add(a, b): return a + b` | `function add(a, b) { return a + b; }` | `int add(int a, int b) { return a + b; }` |
| And, or, not | `and` `or` `not` | `and` `or` `not` | `&&` `\|\|` `!` | `&&` `\|\|` `!` |
| No value | `nothing` | `None` | `null` | `NULL` |
| First item | `xs[1]` | `xs[0]` | `xs[0]` | `xs[0]` |
| Last item | `xs[-1]` | `xs[-1]` | `xs[xs.length - 1]` | `xs[n - 1]` |
| Length | `length(xs)` | `len(xs)` | `xs.length` | by hand |
| Put in text | `"Hi {name}"` | `f"Hi {name}"` | `` `Hi ${name}` `` | `printf("Hi %s", name)` |
| Key and value | `{name: "Ada"}`, `p.name` | `{"name": "Ada"}`, `p["name"]` | `{name: "Ada"}`, `p.name` | a `struct` |
| Problems | `try` `catch` `fail` | `try` `except` `raise` | `try` `catch` `throw` | return codes |
| Read a line | `ask("Name? ")` | `input("Name? ")` | `prompt("Name? ")` | `fgets(...)` |

Things that work differently from all three:

- Positions start at **1**.
- Conditions must be `true` or `false` (no "truthy" values).
- A `for each ... to` loop never counts down unless you give a negative `by`.
- Blocks end with `end`; there are no braces and indenting never changes the meaning.
- One kind of number: whole numbers never overflow, and `6 / 3` is `2`.

## Limits

Zest is a learning-sized language, and honest about it:

- It is slower than Python (see the README for measured numbers), so it suits small programs, not heavy computation.
- There are no classes. Maps and functions cover the same ground at this size.
- There is no way to put real braces in text except `\{` and `\}`.
- Function calls use positional values only (no `name = value` arguments).
- Text is Unicode and files are read and written as UTF-8.
- Programs are not sandboxed: `read_file`, `write_file` and `use` can touch any file the person running Zest can touch. Only run programs you trust.
