#!/usr/bin/env python3
"""Search the Matlas mathematical literature database (8M+ statements from 435K papers)."""
import argparse
import hashlib
import json
import logging
import os
import sys
import urllib.request
from pathlib import Path

from _common.paths import configure_cli_logging

configure_cli_logging()
logger = logging.getLogger(__name__)

MATLAS_API = "https://matlas.ai/api/search"


def search(query: str, num_results: int = 10, cache_dir: str | None = None) -> None:
    logger.info("matlas_search.search called: num_results=%d query=%r", num_results, query)
    payload = json.dumps({"query": query, "num_results": max(num_results, 10)}).encode()
    req = urllib.request.Request(
        MATLAS_API,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read().decode("utf-8")
    except Exception as e:
        logger.exception("matlas_search.search failed: %s", e)
        print(json.dumps({"ok": False, "error": str(e)}))
        sys.exit(1)

    try:
        results = json.loads(data)
    except json.JSONDecodeError as e:
        logger.error("matlas_search.search JSON parse error: %s", e)
        print(json.dumps({"ok": False, "error": f"JSON parse error: {e}", "raw": data[:500]}))
        sys.exit(1)

    if cache_dir:
        cache_path = Path(cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)
        qhash = hashlib.sha256(query.encode()).hexdigest()[:12]
        cache_file = cache_path / f"{qhash}.md"
        lines = [f"# Matlas Search: {query}\n"]
        for r in results:
            lines.append(f"## {r.get('title', r.get('entity_name', 'Unknown'))}")
            lines.append(f"- **Type**: {r.get('type', '')}")
            authors = r.get("authors", "")
            if isinstance(authors, list):
                authors = ", ".join(authors)
            lines.append(f"- **Authors**: {authors}")
            lines.append(f"- **Year**: {r.get('year', '')}")
            lines.append(f"- **DOI**: {r.get('doi', '')}")
            lines.append(f"\n{r.get('statement', '')}\n")
        cache_file.write_text("\n".join(lines), encoding="utf-8")

    logger.info("matlas_search.search succeeded: %d results", len(results))
    print(json.dumps({"ok": True, "count": len(results), "results": results}, ensure_ascii=False, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Search Matlas math literature database")
    parser.add_argument("query", help="Natural language search query")
    parser.add_argument("--num-results", type=int, default=10, help="Number of results (min 10, default: 10)")
    parser.add_argument("--cache-dir", default=None, help="Directory to cache results as Markdown")
    args = parser.parse_args(argv)
    search(args.query, args.num_results, args.cache_dir)


if __name__ == "__main__":
    main()
