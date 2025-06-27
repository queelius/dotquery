import json
from typing import List

from .core import (
    Query,
    contains,
    equals,
    greater,
    less,
    matches,
    all_contains,
    all_equals,
    all_greater,
    all_less,
    all_matches,
)

# Mapping from DSL operator to core function
OPERATORS = {
    "equals": equals,
    "contains": contains,
    "greater": greater,
    "less": less,
    "matches": matches,
}

ALL_OPERATORS = {
    "equals": all_equals,
    "contains": all_contains,
    "greater": all_greater,
    "less": all_less,
    "matches": all_matches,
}

class DSLParser:
    """
    Parses the dotquery DSL into a Query object.
    Handles logical operators (and, or, not), parentheses, and conditions.

    Grammar:
    expression ::= term | expression 'or' term
    term       ::= factor | term 'and' factor
    factor     ::= condition | 'not' factor | '(' expression ')'
    condition  ::= [quantifier] operator path value
    quantifier ::= 'any' | 'all'
    operator   ::= 'equals' | 'contains' | 'greater' | 'less' | 'matches'
    """
    def __init__(self, tokens: List[str]):
        self.tokens = tokens
        self.pos = 0

    def parse(self) -> Query:
        """Runs the parser and returns a single Query object."""
        if not self.tokens:
            raise ValueError("Query cannot be empty.")
        query = self.parse_expression()
        if self.current_token() is not None:
            raise ValueError(f"Unexpected token at end of query: {self.current_token()}")
        return query

    def current_token(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def advance(self):
        self.pos += 1

    def parse_expression(self):
        node = self.parse_term()
        while self.current_token() == "or":
            self.advance()
            node |= self.parse_term()
        return node

    def parse_term(self):
        node = self.parse_factor()
        while self.current_token() == "and":
            self.advance()
            node &= self.parse_factor()
        return node

    def parse_factor(self):
        token = self.current_token()
        if token == "not":
            self.advance()
            return ~self.parse_factor()
        elif token == "(":
            self.advance()
            expr = self.parse_expression()
            if self.current_token() != ")":
                raise ValueError("Mismatched parentheses: expected ')'")
            self.advance()
            return expr
        else:
            return self.parse_condition()

    def parse_condition(self) -> Query:
        quantifier = "any"
        token = self.current_token()
        if token in ("any", "all"):
            quantifier = token
            self.advance()

        operator_str = self.current_token()
        if operator_str not in OPERATORS:
            raise ValueError(f"Unknown operator: '{operator_str}'. Expected one of {list(OPERATORS.keys())}")
        self.advance()

        path = self.current_token()
        if path is None:
            raise ValueError(f"Operator '{operator_str}' requires a path argument.")
        self.advance()

        value_str = self.current_token()
        if value_str is None:
            raise ValueError(f"Operator '{operator_str}' requires a value argument.")
        self.advance()

        # Try to convert value to a number or bool, otherwise treat as string
        try:
            value = json.loads(value_str)
        except json.JSONDecodeError:
            value = value_str

        if quantifier == "all":
            op_func = ALL_OPERATORS[operator_str]
        else:
            op_func = OPERATORS[operator_str]

        return op_func(path, value)
