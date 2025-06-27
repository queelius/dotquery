from typing import Any, Callable, Dict, Iterable

from dotpath_x import DotPath


class Query:
    """
    Represents a query that can be evaluated against a data object.
    The core building block for creating compositional, reusable queries.
    """

    def __init__(self, expression: "Expression"):
        self.expression = expression

    def evaluate(self, data: Any) -> bool:
        """
        Evaluates the query expression against the given data object.

        Args:
            data: The dict or list to evaluate against.

        Returns:
            True if the query matches, False otherwise.
        """
        return self.expression.evaluate(data)

    def __and__(self, other: "Query") -> "Query":
        """Combines this query with another using a logical AND."""
        return Query(And(self.expression, other.expression))

    def __or__(self, other: "Query") -> "Query":
        """Combines this query with another using a logical OR."""
        return Query(Or(self.expression, other.expression))

    def __invert__(self) -> "Query":
        """Negates this query."""
        return Query(Not(self.expression))


class Expression:
    """Base class for all query expressions (AST nodes)."""

    def evaluate(self, data: Any) -> bool:
        """Evaluates the expression against a data object."""
        raise NotImplementedError

    def __and__(self, other: "Expression") -> "And":
        """Creates an AND expression."""
        return And(self, other)

    def __or__(self, other: "Expression") -> "Or":
        """Creates an OR expression."""
        return Or(self, other)

    def __invert__(self) -> "Not":
        """Creates a NOT expression."""
        return Not(self)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the expression to a dictionary."""
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Expression":
        """Deserializes a dictionary into an Expression object."""
        node_type = data.pop("type")
        if node_type == "and":
            return And.from_dict(data)
        elif node_type == "or":
            return Or.from_dict(data)
        elif node_type == "not":
            return Not.from_dict(data)
        elif node_type == "condition":
            return Condition.from_dict(data)
        else:
            raise ValueError(f"Unknown expression type: {node_type}")


class And(Expression):
    """Represents a logical AND operation between two expressions."""

    def __init__(self, left: Expression, right: Expression):
        self.left = left
        self.right = right

    def evaluate(self, data: Any) -> bool:
        """Evaluates both sides and returns True if both are True."""
        return self.left.evaluate(data) and self.right.evaluate(data)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "and",
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "And":
        left = Expression.from_dict(data["left"])
        right = Expression.from_dict(data["right"])
        return cls(left, right)


class Or(Expression):
    """Represents a logical OR operation between two expressions."""

    def __init__(self, left: Expression, right: Expression):
        self.left = left
        self.right = right

    def evaluate(self, data: Any) -> bool:
        """Evaluates both sides and returns True if either is True."""
        return self.left.evaluate(data) or self.right.evaluate(data)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "or",
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Or":
        left = Expression.from_dict(data["left"])
        right = Expression.from_dict(data["right"])
        return cls(left, right)


class Not(Expression):
    """Represents a logical NOT operation on an expression."""

    def __init__(self, expression: Expression):
        self.expression = expression

    def evaluate(self, data: Any) -> bool:
        """Returns the negated result of the inner expression."""
        return not self.expression.evaluate(data)

    def to_dict(self) -> Dict[str, Any]:
        return {"type": "not", "expression": self.expression.to_dict()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Not":
        expression = Expression.from_dict(data["expression"])
        return cls(expression)


class Condition(Expression):
    """
    Represents a leaf condition in the query AST.
    It checks if a value extracted via a dotpath satisfies a given operator.
    """

    def __init__(
        self,
        path: str,
        op: Callable[[Any, Any], bool],
        value: Any,
        quantifier: Callable[[Iterable], bool] = any,
    ):
        self.path = path
        self.op = op
        self.value = value
        self.quantifier = quantifier

    def evaluate(self, data: Any) -> bool:
        """
        Evaluates the condition.
        The result depends on the quantifier (`any` or `all`).
        If no values are found at the path, the condition is False.
        """
        try:
            # Use dotpath-x to find all possible values at the given path
            values = list(DotPath(self.path).find(data))
            if not values:
                return False  # No values found, so condition cannot be met
            # Return True if the operator holds for any/all of the found values
            return self.quantifier(self.op(v, self.value) for v in values)
        except Exception:
            # If path traversal fails (e.g., parse error, invalid segment),
            # it's treated as not found.
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "condition",
            "path": self.path,
            "op": self.op.__name__,
            "value": self.value,
            "quantifier": self.quantifier.__name__,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Condition":
        import operator
        import re

        def _re_match_op(v, r):
            return bool(re.match(r, str(v)))

        OP_MAP = {
            "eq": operator.eq,
            "contains": operator.contains,
            "gt": operator.gt,
            "lt": operator.lt,
            "_re_match_op": _re_match_op,
        }
        QUANTIFIER_MAP = {"any": any, "all": all}

        op_name = data["op"]
        op_func = OP_MAP.get(op_name)
        if op_func is None:
            raise ValueError(f"Unknown operator function: {op_name}")

        quantifier_name = data["quantifier"]
        quantifier_func = QUANTIFIER_MAP.get(quantifier_name)
        if quantifier_func is None:
            raise ValueError(f"Unknown quantifier function: {quantifier_name}")

        return cls(
            path=data["path"],
            op=op_func,
            value=data["value"],
            quantifier=quantifier_func,
        )


# --- Factory functions for creating condition Queries ---


def equals(path: str, value: Any) -> Query:
    """
    Creates a Query that checks if *any* value at `path` equals `value`.
    """
    import operator

    return Query(Condition(path, operator.eq, value, quantifier=any))


def contains(path: str, value: Any) -> Query:
    """
    Creates a Query that checks if *any* collection at `path` contains `value`.
    """
    import operator

    return Query(Condition(path, operator.contains, value, quantifier=any))


def greater(path: str, value: Any) -> Query:
    """
    Creates a Query that checks if *any* value at `path` is greater than `value`.
    """
    import operator

    return Query(Condition(path, operator.gt, value, quantifier=any))


def less(path: str, value: Any) -> Query:
    """
    Creates a Query that checks if *any* value at `path` is less than `value`.
    """
    import operator

    return Query(Condition(path, operator.lt, value, quantifier=any))


# --- 'All' Quantifier Factory Functions ---


def all_equals(path: str, value: Any) -> Query:
    """
    Creates a Query that checks if *all* values at `path` equal `value`.
    """
    import operator

    return Query(Condition(path, operator.eq, value, quantifier=all))


def all_contains(path: str, value: Any) -> Query:
    """
    Creates a Query that checks if *all* collections at `path` contain `value`.
    """
    import operator

    return Query(Condition(path, operator.contains, value, quantifier=all))


def all_greater(path: str, value: Any) -> Query:
    """
    Creates a Query that checks if *all* values at `path` are greater than `value`.
    """
    import operator

    return Query(Condition(path, operator.gt, value, quantifier=all))


def all_less(path: str, value: Any) -> Query:
    """
    Creates a Query that checks if *all* values at `path` are less than `value`.
    """
    import operator

    return Query(Condition(path, operator.lt, value, quantifier=all))


def _re_match_op(v, r):
    import re

    return bool(re.match(r, str(v)))


def matches(path: str, regex: str) -> Query:
    """
    Creates a Query that checks if *any* string value at `path` matches the `regex`.
    """
    return Query(Condition(path, _re_match_op, regex, quantifier=any))


def all_matches(path: str, regex: str) -> Query:
    """
    Creates a Query that checks if *all* string values at `path` match the `regex`.
    """
    return Query(Condition(path, _re_match_op, regex, quantifier=all))
