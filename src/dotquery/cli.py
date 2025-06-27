import argparse
import json
import shlex
import sys

from .dsl import DSLParser
from .queryset import QuerySet


def main():
    """CLI entry point for dotquery."""
    parser = argparse.ArgumentParser(
        description="Query and filter JSON/JSONL data using a fluent Python API or a powerful, chainable CLI.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""Examples:

# Start a new query to find users who are not admins
$ dotquery query "not_equals user.is_admin true" data/

# Chain queries: find active users with more than 100 followers
$ dotquery query "equals status 'active'" users.jsonl | dotquery and "greater followers 100"

# Use the 'all' quantifier: find posts where all tags are lowercase
$ dotquery query "all matches tags '^[a-z]+$'" posts.json

# Resolve a query (execute and print results)
$ ... | dotquery resolve
"""
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 'query' command: Start a new query chain
    query_parser = subparsers.add_parser("query", help="Start a new query chain.")
    query_parser.add_argument("dsl", help="The query DSL string (e.g., \"equals path.to.key 'value'\").")
    query_parser.add_argument(
        "sources",
        nargs='+',
        help="One or more data sources (file, dir, glob, or '-' for stdin)."
    )

    # 'and' command: AND-combine with a query from stdin
    and_parser = subparsers.add_parser("and", help="Combine with the previous query using AND.")
    and_parser.add_argument("dsl", help="The query DSL string to add.")

    # 'or' command: OR-combine with a query from stdin
    or_parser = subparsers.add_parser("or", help="Combine with the previous query using OR.")
    or_parser.add_argument("dsl", help="The query DSL string to add.")

    # 'not' command: Negate the query from stdin
    subparsers.add_parser("not", help="Negate the previous query.")

    # 'resolve' command: Execute the query from stdin and print results
    resolve_parser = subparsers.add_parser("resolve", help="Resolve the query and print matching documents.")
    resolve_parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print the output JSON."
    )


    args = parser.parse_args()

    # --- Command Handling ---

    # Handle stdin source for the initial query command
    if args.command == "query" and args.sources == ["-"]:
        if sys.stdin.isatty():
            print("Error: Reading from stdin was specified ('-') but no data was piped.", file=sys.stderr)
            sys.exit(1)
        # The QuerySet will be created from stdin later
        pass
    elif args.command == "query":
        tokens = shlex.split(args.dsl)
        query = DSLParser(tokens).parse()
        qs = QuerySet(query, args.sources)
        print(qs.to_json())
        sys.exit(0)

    # For all other commands, or a query starting from stdin,
    # we expect a QuerySet from stdin.
    if sys.stdin.isatty():
        print(f"Error: Command '{args.command}' requires a QuerySet piped from stdin.", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    incoming_json = sys.stdin.read()

    # If the command is 'query', we are starting a chain from stdin data
    if args.command == "query":
        # We don't have a QuerySet yet, just raw data.
        # We need to construct a query and then we can't really filter... this path is tricky.
        # Let's assume for now that if `query` is used with stdin, it implies `resolve`.
        # A better design might be needed here.
        # For now, let's make it an error to use `query` with stdin data this way.
        print("Error: Cannot start a new 'query' from a data pipe. Use 'sources' argument or pipe to 'resolve'.", file=sys.stderr)
        sys.exit(1)

    try:
        qs = QuerySet.from_json(incoming_json)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error: Could not decode QuerySet from stdin. Ensure you are piping from another dotquery command. Details: {e}", file=sys.stderr)
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
            # If the original source was stdin, we need to re-read it.
            # This is a limitation of this CLI design. A single process would be better.
            # For now, we assume sources are file-based when chaining.
            for doc in qs:
                if args.pretty:
                    print(json.dumps(doc, indent=2))
                else:
                    print(json.dumps(doc))
        except Exception as e:
            print(f"Error during query resolution: {e}", file=sys.stderr)
            sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
