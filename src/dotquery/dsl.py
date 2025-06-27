import json
from typing import List

from .core import Q, Query


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
    operator   ::= 'equals' | 'not_equals' | 'greater' | 'greater_equal' | 'less' | 'less_equal' | 'contains' | 'matches'
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
        if token in ["any", "all"]:
            quantifier = token
            self.advance()

        operator = self.current_token()
        if operator is None:
            raise ValueError("Unexpected end of query: expected operator")
        self.advance()

        path = self.current_token()
        if path is None:
            raise ValueError("Unexpected end of query: expected path")
        self.advance()

        value_str = self.current_token()
        if value_str is None:
            raise ValueError("Unexpected end of query: expected value")
        self.advance()

        try:
            # Try to parse value as JSON (handles numbers, booleans, null, strings)
            value = json.loads(value_str)
        except (json.JSONDecodeError, TypeError):
            # Fallback for unquoted strings
            value = value_str

        # Create query using the fluent Q builder
        q_builder = Q(path)
        if quantifier == "all":
            q_builder = q_builder.all()

        # Map operator string to Q method
        op_method = getattr(q_builder, operator, None)
        if op_method and callable(op_method):
            return op_method(value)
        else:
            raise ValueError(f"Invalid operator: {operator}")
