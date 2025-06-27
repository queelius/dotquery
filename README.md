# `dotquery`: The Logic Engine for Nested Data

> "Logic is the anatomy of thought."
>
> — John Locke

**`dotquery` is the logic engine of the `dot` ecosystem.** It provides two powerful ways to ask complex, compositional questions about your data:

1.  A **programmatic, Pythonic API** for building queries by composing objects.
2.  A clean **Domain-Specific Language (DSL)** for expressing queries in a simple string format.

Both methods produce the same underlying, serializable **Abstract Syntax Tree (AST)**, allowing you to treat your logic as data.

## The Philosophy: Questions as Data, Built Your Way

`dotquery` is the culmination of the **Logic Pillar**. Where the **Addressing Pillar** (`dotget`, `dotselect`) is about *finding* data, the Logic Pillar is about *asking questions* about it.

-   **`dotexists`**: The simplest check: "Does this exact path exist?"**
-   **`dotany`, `dotall`**: The quantifiers that determine how conditions apply to multiple values.
-   **`dotquery`**: The complete engine: "Do `all` users in the `admin` group have `2-factor-auth` enabled?"

It is designed for validation, scripting, and building conditional workflows. You can choose the query-building method that best fits your use case.

## Programmatic API: Composable Python Objects

This is the most powerful and flexible way to use `dotquery`. You build queries by combining `Condition` objects using standard Python operators.

-   `&` for **AND**
-   `|` for **OR**
-   `~` for **NOT**

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

# You can inspect the generated AST
print(is_valid_user.ast)

# And check it against data
is_valid_user.check(some_user_document)
```

## DSL: Simple, Readable Strings

The DSL is a convenient, human-readable way to write queries. It's perfect for simple scripts, configuration, or command-line usage.

-   **Syntax**: `[quantifier] <operator> <path> [value]`
-   **Composition**: Use `and`, `or`, `not`, and parentheses `()`.

```python
from dotquery import Query

# The same query, expressed in the DSL
dsl_string = """
(
    (equals role 'admin' and greater login_count 10) or
    equals is_superuser true
) and
all tags[*] contains '^[a-z]+$'
"""

is_valid_user_from_dsl = Query(dsl_string)

# The generated AST is identical to the programmatic version
assert is_valid_user.ast == is_valid_user_from_dsl.ast
```

## The AST: The Unifying Core

Both the programmatic API and the DSL compile down to the same serializable JSON Abstract Syntax Tree. This makes your logic portable.

**Programmatic Query:** `equals('role', 'admin') & greater('login_count', 100)`

**DSL:** `"equals role 'admin' and greater login_count 100"`

**Resulting AST:**
```json
{
    "type": "and",
    "clauses": [
        {
            "type": "condition",
            "quantifier": "any",
            "op": "equals",
            "path": "role",
            "value": "admin"
        },
        {
            "type": "condition",
            "quantifier": "any",
            "op": "greater",
            "path": "login_count",
            "value": 100
        }
    ]
}
```

## Command-Line Usage

The CLI uses the DSL and is designed for shell scripting. It returns an exit code of `0` (true) or `1` (false).

```bash
# Check if any book costs less than 8.
$ cat books.json | dotquery "any store.book[*].price less 8"
$ echo $?
1

# Use it in a script
if cat package.json | dotquery "contains keywords[*] 'engine'"; then
  echo "This is an engine package."
fi
```

## Boundaries: When to Use `dotquery`

Use `dotquery` when you need to:
✅ Validate data against a schema of logical rules.
✅ Make decisions in a script based on the content of a JSON/YAML file.
✅ Programmatically build and evaluate complex logical assertions.

Do **not** use `dotquery` when you need to:
❌ Extract data. **Use `dotget`, `dotstar`, or `dotselect`**.
❌ Modify data. **Use `dotmod`**.
❌ Transform data into a new shape. **Use `dotpipe`**.

## Installation

```bash
pip install dotquery
```
