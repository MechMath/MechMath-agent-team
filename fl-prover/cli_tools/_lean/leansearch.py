#!/usr/bin/env python3
"""Search Lean theorems using LeanSearch (natural language + Lean terms)."""
import argparse
import json
import os
import logging
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from _common.paths import configure_cli_logging

configure_cli_logging()
logger = logging.getLogger(__name__)


def search(query: str, num_results: int = 5) -> None:
    logger.info("leansearch.search called: num_results=%d query=%r", num_results, query)
    try:
        # leansearch.net expects POST /search with JSON body
        # {"query": [<list of query strings>], "num_results": N}.
        # Response is a list-of-lists (one inner list per query).
        body = json.dumps({"query": [query], "num_results": num_results}).encode("utf-8")
        req = urllib.request.Request(
            "https://leansearch.net/search",
            data=body,
            headers={
                "User-Agent": "numina-lean-agent/0.1",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=20) as response:
            payload = json.loads(response.read())

        # Unwrap the outer list (one entry per query — we only send one).
        results = payload[0] if payload and isinstance(payload, list) else []

        if not results:
            logger.info("leansearch.search: no results found")
            print("No results found.")
            return

        logger.info("leansearch.search succeeded: %d results", len(results))
        print(json.dumps(results, indent=2, ensure_ascii=False))
    except Exception as e:
        logger.exception("leansearch.search failed: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Search Lean theorems using LeanSearch")
    parser.add_argument("query", help="Natural language or Lean term query")
    parser.add_argument("-n", "--num-results", type=int, default=5, help="Max results (default: 5)")
    args = parser.parse_args(argv)
    search(args.query, args.num_results)


if __name__ == "__main__":
    main()
