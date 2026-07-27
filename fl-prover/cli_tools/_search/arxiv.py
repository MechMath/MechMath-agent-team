#!/usr/bin/env python3
"""Search arXiv for papers related to a mathematical topic."""
import argparse
import hashlib
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from _common.paths import configure_cli_logging

configure_cli_logging()
logger = logging.getLogger(__name__)

ARXIV_API = "https://export.arxiv.org/api/query"
NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def _retry_after_seconds(error: urllib.error.HTTPError) -> float | None:
    retry_after = error.headers.get("Retry-After")
    if not retry_after:
        return None
    try:
        return max(float(retry_after), 0.0)
    except ValueError:
        return None


def _read_url_with_retry(url: str, max_retries: int = 3, timeout: int = 30) -> str:
    attempts = max_retries + 1
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            is_retryable = e.code == 429 or 500 <= e.code < 600
            if not is_retryable or attempt == attempts - 1:
                raise
            delay = _retry_after_seconds(e)
            if delay is None:
                delay = min(3.0 * (2**attempt), 30.0)
            logger.warning(
                "arxiv_search.search HTTP %s; retrying in %.1fs (%d/%d)",
                e.code,
                delay,
                attempt + 1,
                max_retries,
            )
            time.sleep(delay)
        except urllib.error.URLError as e:
            if attempt == attempts - 1:
                raise
            delay = min(3.0 * (2**attempt), 30.0)
            logger.warning(
                "arxiv_search.search transient URL error %s; retrying in %.1fs (%d/%d)",
                e,
                delay,
                attempt + 1,
                max_retries,
            )
            time.sleep(delay)
    raise RuntimeError("unreachable retry loop exit")


def search(query: str, max_results: int = 5, cache_dir: str | None = None, max_retries: int = 3) -> None:
    logger.info("arxiv_search.search called: max_results=%d query=%r", max_results, query)
    params = urllib.parse.urlencode({
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    })
    url = f"{ARXIV_API}?{params}"

    try:
        data = _read_url_with_retry(url, max_retries=max_retries)
    except Exception as e:
        logger.exception("arxiv_search.search failed: %s", e)
        print(json.dumps({"ok": False, "error": str(e)}))
        sys.exit(1)

    root = ET.fromstring(data)
    results = []
    for entry in root.findall("atom:entry", NS):
        title = entry.findtext("atom:title", "", NS).strip().replace("\n", " ")
        summary = entry.findtext("atom:summary", "", NS).strip().replace("\n", " ")
        arxiv_id = entry.findtext("atom:id", "", NS).strip()
        published = entry.findtext("atom:published", "", NS).strip()[:10]
        authors = [a.findtext("atom:name", "", NS) for a in entry.findall("atom:author", NS)]
        pdf_link = ""
        for link in entry.findall("atom:link", NS):
            if link.get("title") == "pdf":
                pdf_link = link.get("href", "")
        results.append({
            "title": title,
            "authors": authors,
            "abstract": summary[:500],
            "arxiv_id": arxiv_id,
            "published": published,
            "pdf": pdf_link,
        })

    # Cache if dir provided
    if cache_dir:
        cache_path = Path(cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)
        qhash = hashlib.sha256(query.encode()).hexdigest()[:12]
        cache_file = cache_path / f"{qhash}.md"
        lines = [f"# arXiv Search: {query}\n"]
        for r in results:
            lines.append(f"## {r['title']}")
            lines.append(f"- **Authors**: {', '.join(r['authors'])}")
            lines.append(f"- **Published**: {r['published']}")
            lines.append(f"- **arXiv**: {r['arxiv_id']}")
            lines.append(f"- **PDF**: {r['pdf']}")
            lines.append(f"\n{r['abstract']}\n")
        cache_file.write_text("\n".join(lines), encoding="utf-8")

    logger.info("arxiv_search.search succeeded: %d results", len(results))
    print(json.dumps({"ok": True, "count": len(results), "results": results}, ensure_ascii=False, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Search arXiv for math papers")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--max-results", type=int, default=5, help="Max results (default: 5)")
    parser.add_argument("--cache-dir", default=None, help="Directory to cache results as Markdown")
    parser.add_argument("--max-retries", type=int, default=3, help="Retries for HTTP 429/5xx/transient URL errors (default: 3)")
    args = parser.parse_args(argv)
    search(args.query, args.max_results, args.cache_dir, max(0, args.max_retries))


if __name__ == "__main__":
    main()
