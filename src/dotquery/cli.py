import argparse
import json
import sys
import shlex

from .dsl import DSLParser
from .queryset import QuerySet
from .core import Query


def main():
    """CLI entry point for dotquery, supporting chainable queries."""
    parser = argparse.ArgumentParser(
        description="A chainable query tool for JSON data, powered by dotpath-x.",
        epilog="Example: dotquery query \"equals a.b 1\" docs/ | dotquery and \"greater c 10\" | dotquery resolve"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 'query' command: Start a new query chain
    query_parser = subparsers.add_parser("query", help="Start a new query chain.")
    query_parser.add_argument("dsl", help="The query DSL string.")
    query_parser.add_argument("sources", nargs='+', help="One or more data sources (file, dir, glob)." )

    # 'and' command: AND-combine with a query from stdin
    and_parser = subparsers.add_parser("and", help="Combine with the previous query using AND.")
    and_parser.add_argument("dsl", help="The query DSL string to add.")

    # 'or' command: OR-combine with a query from stdin
    or_parser = subparsers.add_parser("or", help="Combine with the previous query using OR.")
    or_parser.add_argument("dsl", help="The query DSL string to add.")

    # 'not' command: Negate the query from stdin
    subparsers.add_parser("not", help="Negate the previous query.")

    # 'resolve' command: Execute the query from stdin and print results
    subparsers.add_parser("resolve", help="Resolve the query and print matching documents.")

    args = parser.parse_args()

    # --- Command Handling ---

    if args.command == "query":
        tokens = shlex.split(args.dsl)
        query = DSLParser(tokens).parse()
        qs = QuerySet(query, args.sources)
        print(qs.to_json())
        sys.exit(0)

    # For all other commands, we expect a QuerySet from stdin
    if sys.stdin.isatty():
        print(f"Error: Command '{args.command}' requires a QuerySet piped from stdin.", file=sys.stderr)
        sys.exit(1)

    try:
        incoming_json = sys.stdin.read()
        qs = QuerySet.from_json(incoming_json)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error: Could not decode QuerySet from stdin. {e}", file=sys.stderr)
        sys.exit(1)

    if args.command == "and":
        tokens = shlex.split(args.dsl)
        new_query = DSLParser(tokens).parse()
        qs.query &= new_query
        print(qs.to_json())

    elif args.command == "or":
        tokens = shlex.split(args.dsl)
        new_query = DSLParser(tokens).parse()
        qs.query |= new_query
        print(qs.to_json())

    elif args.command == "not":
        qs.query = ~qs.query
        print(qs.to_json())

    elif args.command == "resolve":
        try:
            for doc in qs.resolve():
                print(json.dumps(doc))
        except Exception as e:
            print(f"Error during query resolution: {e}", file=sys.stderr)
            sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
