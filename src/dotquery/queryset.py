import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Union

from .core import Expression, Query


class QuerySet:
    """
    Represents a lazily evaluated query against a set of data sources.

    This class encapsulates a query expression (AST) and the sources
    of data it should be run against. The sources can be file paths,
    directories, or even wildcards.

    The QuerySet object is designed to be serialized to JSON, allowing it
    to be passed between command-line processes.
    """

    def __init__(self, query: Query, sources: List[str]):
        if not isinstance(query, Query):
            raise TypeError("query must be a Query object")
        self.query = query
        self.sources = sources

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

    def resolve(self) -> Iterable[Any]:
        """
        Lazily resolves the query against the data sources.

        This generator function iterates through the specified sources,
        loads the data (assuming JSON for now), and yields the documents
        that match the query.
        """
        for source_path in self._expand_sources():
            try:
                with open(source_path, "r") as f:
                    # Handle JSONL (one JSON object per line)
                    if source_path.suffix == ".jsonl":
                        for line in f:
                            if line.strip():
                                doc = json.loads(line)
                                if self.query.evaluate(doc):
                                    yield doc
                    # Handle standard JSON (a single object or list)
                    else:
                        data = json.load(f)
                        if isinstance(data, list):
                            for doc in data:
                                if self.query.evaluate(doc):
                                    yield doc
                        elif self.query.evaluate(data):
                            yield data
            except (IOError, json.JSONDecodeError) as e:
                print(f"Warning: Could not read or parse {source_path}: {e}", file=sys.stderr)
                continue

    def _expand_sources(self) -> Iterable[Path]:
        """Expands source strings into a list of concrete file paths."""
        base_path = Path.cwd()
        for pattern in self.sources:
            path = Path(pattern)
            if path.is_dir():
                yield from path.rglob("*.json")
                yield from path.rglob("*.jsonl")
            elif '*' in pattern or '?' in pattern:
                # Use glob for wildcard matching
                yield from base_path.glob(pattern)
            elif path.exists() and path.is_file():
                yield path
            else:
                # Potentially handle other source types here in the future
                print(f"Warning: Source not found or supported: {pattern}", file=sys.stderr)
