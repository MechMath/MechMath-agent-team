#!/usr/bin/env python3
"""Citation-graph multi-hop search (ADR 0018, option O1).

Walks references and citations outward from a seed paper, deduplicates, and
ranks candidates by cheap keyword overlap with the obligation being sought.

Like `frontier.py`, this tool is mechanical: the score orders a work queue, it
never decides whether a result is true or usable. Correctness auditing belongs
to the Auditor (ADR 0019), not here and not to the Searcher.

    search.py citation-graph <seed> --obligation "<statement>" [--hops 1]

`<seed>` may be an arXiv id (`2103.01234`), a DOI (`10.1234/foo`), or an
OpenAlex work id (`W2741809807`).

Data source is OpenAlex (ADR 0018, Q-API settled): open, no API key, generous
polite-pool limits, headless-friendly. Edge fetching goes through the
`EdgeProvider` seam below so a second source (e.g. Semantic Scholar) can be
added or swapped without touching the traversal.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from _common.paths import configure_cli_logging

configure_cli_logging()
logger = logging.getLogger(__name__)

OPENALEX_API = "https://api.openalex.org"
ARXIV_DOI_PREFIX = "10.48550/arXiv."

# Words too common in mathematical titles to carry signal.
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "in",
    "is", "it", "its", "of", "on", "or", "that", "the", "to", "we", "with",
    "this", "these", "those", "which", "some", "any", "all", "new", "note",
    "paper", "results", "result", "study", "case", "using", "via", "over",
}


# --------------------------------------------------------------------------
# scoring (cheap, deterministic, keyword-level only)
# --------------------------------------------------------------------------

def tokenize(text: str) -> set[str]:
    return {
        tok for tok in re.findall(r"[a-z0-9]+", (text or "").lower())
        if len(tok) > 2 and tok not in STOPWORDS
    }


def relevance(obligation_tokens: set[str], title: str, abstract: str) -> tuple[float, str]:
    """Fraction of obligation keywords present in the candidate's text."""
    if not obligation_tokens:
        return 0.0, "no obligation keywords"
    candidate = tokenize(f"{title} {abstract}")
    hits = obligation_tokens & candidate
    score = round(len(hits) / len(obligation_tokens), 4)
    why = "matched: " + ", ".join(sorted(hits)) if hits else "no keyword overlap"
    return score, why


def reconstruct_abstract(inverted_index: dict | None) -> str:
    """OpenAlex ships abstracts as {word: [positions]}; invert it back."""
    if not inverted_index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, idxs in inverted_index.items():
        for idx in idxs or []:
            positions.append((idx, word))
    positions.sort()
    return " ".join(word for _, word in positions)


# --------------------------------------------------------------------------
# edge provider seam
# --------------------------------------------------------------------------

class EdgeProvider:
    """Interface for a citation edge source."""

    def resolve(self, seed: str) -> dict | None:  # pragma: no cover - interface
        raise NotImplementedError

    def fetch(self, work_ids: list[str]) -> list[dict]:  # pragma: no cover - interface
        raise NotImplementedError

    def cited_by(self, work_id: str, limit: int) -> list[dict]:  # pragma: no cover - interface
        raise NotImplementedError


class OpenAlexProvider(EdgeProvider):
    def __init__(self, mailto: str | None = None, max_retries: int = 3, timeout: int = 30):
        self.mailto = mailto or os.environ.get("OPENALEX_MAILTO") or ""
        self.max_retries = max_retries
        self.timeout = timeout

    # -- http ------------------------------------------------------------
    def _get(self, path: str, params: dict | None = None) -> dict:
        params = dict(params or {})
        if self.mailto:
            params["mailto"] = self.mailto
        url = f"{OPENALEX_API}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "NL-Prover/citation-graph"})
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return {}
                retryable = e.code == 429 or 500 <= e.code < 600
                if not retryable or attempt == attempts - 1:
                    raise
                delay = min(3.0 * (2 ** attempt), 30.0)
                logger.warning("citation_graph HTTP %s; retrying in %.1fs", e.code, delay)
                time.sleep(delay)
            except urllib.error.URLError:
                if attempt == attempts - 1:
                    raise
                delay = min(3.0 * (2 ** attempt), 30.0)
                logger.warning("citation_graph transient URL error; retrying in %.1fs", delay)
                time.sleep(delay)
        raise RuntimeError("unreachable retry loop exit")

    # -- interface -------------------------------------------------------
    def resolve(self, seed: str) -> dict | None:
        for path in _seed_paths(seed):
            work = self._get(path)
            if work and work.get("id"):
                return normalize_work(work)
        return None

    def fetch(self, work_ids: list[str]) -> list[dict]:
        out: list[dict] = []
        # OpenAlex allows up to 50 ids per OR-filter.
        for chunk_start in range(0, len(work_ids), 50):
            chunk = work_ids[chunk_start:chunk_start + 50]
            data = self._get("/works", {"filter": "openalex:" + "|".join(chunk), "per-page": 50})
            out.extend(normalize_work(w) for w in data.get("results", []))
        return out

    def cited_by(self, work_id: str, limit: int) -> list[dict]:
        data = self._get("/works", {"filter": f"cites:{work_id}", "per-page": min(limit, 50)})
        return [normalize_work(w) for w in data.get("results", [])]


def _seed_paths(seed: str) -> list[str]:
    """Candidate OpenAlex lookup paths for a user-supplied seed identifier."""
    seed = seed.strip()
    if re.fullmatch(r"W\d+", seed):
        return [f"/works/{seed}"]
    if seed.lower().startswith("10."):
        return [f"/works/doi:{seed}"]
    if seed.lower().startswith("arxiv:"):
        seed = seed.split(":", 1)[1]
    if re.fullmatch(r"\d{4}\.\d{4,5}(v\d+)?", seed):
        bare = seed.split("v")[0]
        return [f"/works/doi:{ARXIV_DOI_PREFIX}{bare}"]
    return [f"/works/doi:{seed}", f"/works/{seed}"]


def short_id(work_id: str) -> str:
    return (work_id or "").rstrip("/").rsplit("/", 1)[-1]


def normalize_work(work: dict) -> dict:
    return {
        "id": short_id(work.get("id", "")),
        "title": work.get("title") or work.get("display_name") or "",
        "year": work.get("publication_year"),
        "doi": work.get("doi") or "",
        "abstract": reconstruct_abstract(work.get("abstract_inverted_index")),
        "referenced_works": [short_id(w) for w in work.get("referenced_works") or []],
    }


# --------------------------------------------------------------------------
# traversal
# --------------------------------------------------------------------------

def walk(
    seed: str,
    obligation: str,
    hops: int = 1,
    per_node: int = 25,
    provider: EdgeProvider | None = None,
) -> dict:
    """BFS outward from `seed` over references and citations, up to `hops`."""
    provider = provider or OpenAlexProvider()
    obligation_tokens = tokenize(obligation)

    root = provider.resolve(seed)
    if not root:
        return {"ok": False, "error": f"could not resolve seed {seed!r} in the citation graph"}

    seen: set[str] = {root["id"]}
    results: list[dict] = []
    current = [root]

    for hop in range(1, hops + 1):
        neighbour_ids: list[str] = []
        neighbours: list[dict] = []
        for node in current:
            # backward edges: what this paper cites (where an older theorem hides)
            for ref in node.get("referenced_works", [])[:per_node]:
                if ref not in seen:
                    seen.add(ref)
                    neighbour_ids.append(ref)
            # forward edges: what cites this paper (later refinements/uses)
            for citing in provider.cited_by(node["id"], per_node):
                if citing["id"] not in seen:
                    seen.add(citing["id"])
                    neighbours.append(citing)

        if neighbour_ids:
            neighbours.extend(provider.fetch(neighbour_ids))

        for node in neighbours:
            score, why = relevance(obligation_tokens, node["title"], node["abstract"])
            results.append({
                "id": node["id"],
                "title": node["title"],
                "year": node["year"],
                "doi": node["doi"],
                "hop": hop,
                "score": score,
                "why": why,
            })

        current = neighbours
        if not current:
            break

    results.sort(key=lambda r: (-r["score"], r["hop"], r["id"]))
    return {
        "ok": True,
        "seed": {"id": root["id"], "title": root["title"]},
        "obligation": obligation,
        "hops": hops,
        "count": len(results),
        "results": results,
    }


def push_to_frontier(workspace: str, payload: dict, limit: int) -> int:
    """Merge results into the shared O3 frontier (ADR 0018: one queue, not two)."""
    from _search import frontier

    pushed = 0
    for item in payload.get("results", [])[:limit]:
        frontier.push(
            workspace,
            node_id=item["id"],
            title=item["title"],
            source="citation-graph",
            depth=item["hop"],
            parent=payload["seed"]["id"],
            score=item["score"],
            why=item["why"],
        )
        pushed += 1
    return pushed


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description="Citation-graph multi-hop search (ADR 0018 O1)")
    parser.add_argument("seed", help="arXiv id, DOI, or OpenAlex work id")
    parser.add_argument("--obligation", required=True, help="the statement being sought")
    parser.add_argument("--hops", type=int, default=1, help="hop budget (default: 1)")
    parser.add_argument("--per-node", type=int, default=25, help="max edges followed per node (default: 25)")
    parser.add_argument("--mailto", default=None, help="contact email for the OpenAlex polite pool")
    parser.add_argument("--push-frontier", default=None, metavar="WORKSPACE",
                        help="also push results into that workspace's frontier")
    parser.add_argument("--push-limit", type=int, default=20, help="max nodes pushed to the frontier (default: 20)")
    args = parser.parse_args(argv)

    try:
        payload = walk(
            args.seed, args.obligation, max(1, args.hops), max(1, args.per_node),
            provider=OpenAlexProvider(mailto=args.mailto),
        )
    except Exception as e:  # network/parse failures are tool failures, not evidence
        logger.exception("citation_graph.walk failed: %s", e)
        print(json.dumps({"ok": False, "error": str(e)}))
        sys.exit(1)

    if payload.get("ok") and args.push_frontier:
        payload["pushed_to_frontier"] = push_to_frontier(args.push_frontier, payload, args.push_limit)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if not payload.get("ok", True):
        sys.exit(1)


if __name__ == "__main__":
    main()
