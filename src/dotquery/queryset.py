import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Union

from .core import Expression, Query


class QuerySet:
    """
    Represents a lazily evaluated, iterable, and serializable query result.

    A QuerySet encapsulates a query and its data sources. It doesn't fetch
    data or run the query until you iterate over it. This allows for
    efficient processing of large datasets and enables queries to be
    defined, passed around, and combined before execution.

    QuerySets can be serialized to JSON, allowing them to be stored or
    passed between processes.
    """

    def __init__(self, query: Query, sources: List[str]):
        if not isinstance(query, Query):
            raise TypeError("query must be a Query object")
        self.query = query
        self.sources = sources
        self._resolved_data = None

    def __iter__(self) -> Iterator[Any]:
        """Makes the QuerySet iterable, executing the query lazily."""
        return self.resolve()

    def to_json(self) -> str:
        """Serializes the QuerySet to a JSON string."""
        return json.dumps({
            "query_ast": self.query.expression.to_dict(),
            "sources": self.sources,
        }, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "QuerySet":
        """Deserializes a QuerySet from a JSON string."""
        data = json.loads(json_str)
        query_ast = Expression.from_dict(data["query_ast"])
        return cls(Query(query_ast), data["sources"])

    def resolve(self) -> Iterator[Any]:
        """
        Lazily resolves the query against the data sources.

        This generator function iterates through the specified sources,
        loads the data (supporting JSON and JSONL), and yields the documents
        that match the query.
        """
        for source_path in self._expand_sources():
            try:
                with source_path.open("r") as f:
                    # Handle JSONL (one JSON object per line)
                    if source_path.suffix == ".jsonl":
                        for line in f:
                            if line.strip():
                                doc = json.loads(line)
                                if self.query(doc): # Use Query.__call__
                                    yield doc
                    # Handle standard JSON (a single object or list)
                    else:
                        data = json.load(f)
                        if isinstance(data, list):
                            yield from self.query.filter(data) # Use Query.filter
                        elif self.query(data):
                            yield data
            except (IOError, json.JSONDecodeError) as e:
                print(f"Warning: Could not read or parse {source_path}: {e}", file=sys.stderr)
                continue

    def _expand_sources(self) -> Iterator[Path]:
        """Expands source strings into a list of concrete file paths."""
        base_path = Path.cwd()
        for pattern in self.sources:
            # Handle stdin
            if pattern == "-":
                # In this context, we can't directly read from sys.stdin
                # as it would block. We'll rely on the CLI runner to pipe it.
                # For programmatic use, users should pass explicit file paths.
                continue

            path = Path(pattern)
            if path.is_dir():
                yield from path.rglob("*.json")
                yield from path.rglob("*.jsonl")
            elif '*' in pattern or '?' in pattern:
                # Use glob for wildcard matching from the current or a base directory
                # Note: glob doesn't support absolute paths in the pattern well.
                # We handle this by checking if the pattern is absolute.
                if path.is_absolute():
                     # This part is tricky with glob. Let's simplify.
                     # Users should use relative paths for wildcards for now.
                     p = Path(pattern)
                     yield from Path(p.anchor).glob(str(p.relative_to(p.anchor)))
                else:
                    yield from base_path.glob(pattern)
            elif path.exists() and path.is_file():
                yield path
            else:
                print(f"Warning: Source not found or supported: {pattern}", file=sys.stderr)

    def __repr__(self) -> str:
        return f"QuerySet(query={self.query}, sources={self.sources})"
