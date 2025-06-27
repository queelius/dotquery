# `dotquery`: The Logic Engine

> "Logic is the anatomy of thought."
>
> — John Locke

`dotquery` is the logic engine of the `dot` ecosystem. It does not find or retrieve data. Instead, it asks complex, compositional questions *about* your data and returns a simple, boolean answer: `True` or `False`.

It is designed for validation, scripting, and building conditional workflows where you need to know *if* your data meets a certain set of criteria.

## Powered by `dotpath-x`

`dotquery`'s power comes from its use of `dotpath-x` as its addressing engine. Every path you provide to a `dotquery` condition is a full-featured `dotpath-x` expression. This means you can use wildcards, descendants, filters, and any other `dotpath-x` segment to select the data you want to ask questions about.

## Core Concepts

`dotquery` is built on three simple ideas:

1.  **Conditions:** These are the basic questions you can ask (e.g., `equals`, `greater`, `contains`). They take a `dotpath-x` path and a value to check against.
2.  **Quantifiers:** These determine *how* a condition is applied when a path returns multiple values.
    *   `any(...)`: Returns `True` if the condition is met for **at least one** of the values. (This is the default).
    *   `all(...)`: Returns `True` only if the condition is met for **all** of the values.
3.  **Composition:** You can combine any number of conditions using standard Python operators to form complex logical expressions:
    *   `&` for **AND**
    *   `|` for **OR**
    *   `~` for **NOT**

## Programmatic Usage

The programmatic API allows you to build reusable, complex queries.

### Example 1: Simple Checks

```python
from dotquery import Query, equals, contains
import my_data

# Is the project version 1.0.0?
q1 = Query(equals('version', '1.0.0'))
q1.check(my_data) # => True

# Does the description contain the word "engine"?
q2 = Query(contains('description', 'engine'))
q2.check(my_data) # => True
```

### Example 2: Using Quantifiers with `dotpath-x`

This is where the power of `dotpath-x` shines.

```python
from dotquery import Query, all, any, greater

# Are ALL of the books in the store priced above 5?
q_all = Query(all('store.book[*].price', greater(5)))
q_all.check(my_data) # => True

# Is ANY book written by "Herman Melville"?
q_any = Query(any('store.book[*].author', equals('Herman Melville')))
q_any.check(my_data) # => True
```

### Example 3: Complex Composition

Combine conditions to create sophisticated validation logic.

```python
from dotquery import Query, equals, greater, all, contains

# The query is valid if:
# (The user is an 'admin' AND has more than 10 logins)
# OR (The user is a 'superuser')
# AND (ALL of their tags are lowercase)
is_valid_user = Query(
    (
        (equals('role', 'admin') & greater('login_count', 10)) |
        equals('is_superuser', True)
    ) &
    all('tags[*]', contains(r'^[a-z]+$')) # contains can also take a regex
)

is_valid_user.check(some_user_document)
```

## Command-Line Usage

The `dotquery` CLI is designed for shell scripting. It prints nothing on success, and returns an exit code of `0` for `True` and `1` for `False`.

```bash
# Check if the version is 1.0.0.
$ cat package.json | dotquery equals version 1.0.0
$ echo $?
0

# Check if any book costs less than 8.
$ cat books.json | dotquery any 'store.book[*].price' less 8
$ echo $?
1

# Use it in a script
if cat package.json | dotquery contains 'keywords[*]' 'engine'; then
  echo "This is an engine package."
else
  echo "This is not an engine package."
fi
```

## Installation

```bash
pip install dotquery
```
