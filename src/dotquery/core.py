from typing import Any, Callable, Dict, Iterable, List
import operator
import re

from dotpath import DotPath


def _re_match_op(v, r):
    """Internal helper for regex matching."""
    return bool(re.match(r, str(v)))


# --- Core Query and Expression Classes (AST) ---

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

    def __call__(self, data: Any) -> bool:
        """Allows the query to be called like a function."""
        return self.evaluate(data)

    def filter(self, data: Iterable[Any]) -> Iterable[Any]:
        """Filters an iterable of data objects, yielding matches."""
        return (item for item in data if self.evaluate(item))


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
            # Use dotpath to find all possible values at the given path
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
        OP_MAP = {
            "eq": operator.eq,
            "ne": operator.ne,
            "gt": operator.gt,
            "ge": operator.ge,
            "lt": operator.lt,
            "le": operator.le,
            "contains": operator.contains,
            "matches": _re_match_op,
        }
        QUANTIFIER_MAP = {"any": any, "all": all}

        op_name = data["op"]
        op_func = OP_MAP.get(op_name)
        if op_func is None:
            raise ValueError(f"Unknown operator function: {op_name}")

        quantifier_name = data.get("quantifier", "any") # Default to 'any'
        quantifier_func = QUANTIFIER_MAP.get(quantifier_name)
        if quantifier_func is None:
            raise ValueError(f"Unknown quantifier function: {quantifier_name}")

        return cls(
            path=data["path"],
            op=op_func,
            value=data["value"],
            quantifier=quantifier_func,
        )


# --- Fluent Query Builder ---

class Q:
    """
    A factory for creating Query objects in a fluent, Pythonic way.

    Provides a more intuitive and readable way to construct complex queries
    by chaining methods, for example:
    `Q("user.profile.tags").contains("python")`
    `Q("items.price").all().greater(10)`
    """

    def __init__(self, path: str, quantifier: Callable[[Iterable], bool] = any):
        self.path = path
        self.quantifier = quantifier

    def all(self) -> "Q":
        """
        Applies the 'all' quantifier to the next condition.
        This requires that *all* values found at the path satisfy the condition.
        If no values are found, it evaluates to True.
        """
        return Q(self.path, quantifier=all)

    def equals(self, value: Any) -> Query:
        """Checks if the value at path is equal to the given value."""
        return Query(Condition(self.path, operator.eq, value, self.quantifier))

    def not_equals(self, value: Any) -> Query:
        """Checks if the value at path is not equal to the given value."""
        return Query(Condition(self.path, operator.ne, value, self.quantifier))

    def greater(self, value: Any) -> Query:
        """Checks if the value at path is greater than the given value."""
        return Query(Condition(self.path, operator.gt, value, self.quantifier))

    def greater_equal(self, value: Any) -> Query:
        """Checks if the value at path is greater than or equal to the given value."""
        return Query(Condition(self.path, operator.ge, value, self.quantifier))

    def less(self, value: Any) -> Query:
        """Checks if the value at path is less than the given value."""
        return Query(Condition(self.path, operator.lt, value, self.quantifier))

    def less_equal(self, value: Any) -> Query:
        """Checks if the value at path is less than or equal to the given value."""
        return Query(Condition(self.path, operator.le, value, self.quantifier))

    def contains(self, value: Any) -> Query:
        """Checks if the collection at path contains the given value."""
        return Query(Condition(self.path, operator.contains, value, self.quantifier))

    def matches(self, regex: str) -> Query:
        """Checks if the string value at path matches the given regex."""
        return Query(Condition(self.path, _re_match_op, regex, self.quantifier))
