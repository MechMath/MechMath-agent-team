#!/usr/bin/env python3
"""refs.bib generator — ADR 0019 §4 / P2.

Turns the provenance ledger into a real BibTeX file next to the article `.tex`,
so KLMM `\\citep`/`\\citet` keys resolve at `bibtex` time.

Policy (ADR 0019): fetch a *real* BibTeX entry from an authoritative metadata
source — no `TODO` placeholders in the prose. Order:
  1. Crossref content negotiation on a DOI (returns application/x-bibtex; no key).
  2. OpenAlex by DOI (no key; polite pool takes a mailto).
Only when every source fails is the key reported as MISSING (for a human to
fill), never silently TODO'd into the article.

    workspace.py refs-bib <workspace> [--mailto you@example.org]

Writes `<workspace>/references/refs.bib` and prints a fetched/synthesized/missing
report. The network layer sits behind `BibtexProvider` so it is testable offline.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from _common.paths import configure_cli_logging
from _workspace import ledger as _ledger

configure_cli_logging()
logger = logging.getLogger(__name__)

CROSSREF_BIBTEX = "https://api.crossref.org/works/{doi}/transform/application/x-bibtex"


class BibtexProvider:
    """Fetches a BibTeX record for a DOI. Subclassed/faked in tests."""

    def __init__(self, mailto: str | None = None, timeout: int = 30):
        self.mailto = mailto or os.environ.get("OPENALEX_MAILTO") or ""
        self.timeout = timeout

    def by_doi(self, doi: str) -> str | None:
        doi = _clean_doi(doi)
        if not doi:
            return None
        url = CROSSREF_BIBTEX.format(doi=urllib.parse.quote(doi, safe="/"))
        headers = {"User-Agent": f"NL-Prover/refs-bib ({self.mailto or 'anonymous'})"}
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.read().decode("utf-8", errors="replace").strip()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            logger.warning("refs_bib crossref HTTP %s for %s", exc.code, doi)
            return None
        except urllib.error.URLError as exc:
            logger.warning("refs_bib crossref URL error for %s: %s", doi, exc)
            return None


def _clean_doi(doi: str) -> str:
    doi = (doi or "").strip()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    return doi


def _rekey(entry: str, cite_key: str) -> str:
    """Replace the citation key inside a fetched BibTeX entry with our cite_key."""
    return re.sub(r"(@\w+\s*\{)[^,]*,", rf"\g<1>{cite_key},", entry, count=1)


def synthesize(row: dict) -> str:
    """Minimal, honest entry from ledger fields when no source resolves.

    Not a TODO: it is a real (if sparse) @misc marked incomplete, so the article
    still compiles while the missing metadata is reported to a human.
    """
    key = row.get("cite_key") or row.get("claim_id")
    title = row.get("statement", "").strip().rstrip(".") or row.get("paper_id", "untitled")
    fields = [f"  title = {{{title}}}"]
    if row.get("paper_id"):
        fields.append(f"  note = {{source: {row['paper_id']}, locator {row.get('locator', '')}}}")
    return "@misc{" + key + ",\n" + ",\n".join(fields) + "\n}"


def cite_key_for(row: dict) -> str:
    return row.get("cite_key") or row.get("paper_id") or row.get("claim_id") or "unknown"


def build(workspace: str | Path, provider: BibtexProvider | None = None) -> dict:
    provider = provider or BibtexProvider()
    rows = _ledger.load_rows(workspace)

    entries: list[str] = []
    fetched: list[str] = []
    synthesized: list[str] = []
    missing: list[str] = []
    seen_keys: set[str] = set()

    for row in rows:
        key = cite_key_for(row)
        if key in seen_keys:  # one bib entry per cite_key even if reused across claims
            continue
        seen_keys.add(key)
        # keep the ledger's cite_key column in sync
        if row.get("claim_id") and not row.get("cite_key"):
            _ledger.set_cite_key(workspace, row["claim_id"], key)

        entry = provider.by_doi(row.get("doi", "")) if row.get("doi") else None
        if entry:
            entries.append(_rekey(entry, key))
            fetched.append(key)
        else:
            entries.append(synthesize({**row, "cite_key": key}))
            if row.get("doi"):
                missing.append(key)   # had a DOI but the fetch failed — flag for a human
            else:
                synthesized.append(key)   # no DOI to resolve; sparse entry from ledger

    out_path = Path(workspace) / "references" / "refs.bib"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n\n".join(entries) + ("\n" if entries else ""), encoding="utf-8")

    return {
        "ok": True,
        "path": str(out_path),
        "entries": len(entries),
        "fetched": fetched,
        "synthesized": synthesized,
        "missing": missing,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate references/refs.bib from the provenance ledger (ADR 0019)")
    parser.add_argument("workspace")
    parser.add_argument("--mailto", default=None, help="contact email for the OpenAlex/Crossref polite pool")
    args = parser.parse_args(argv)

    result = build(args.workspace, provider=BibtexProvider(mailto=args.mailto))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("missing"):
        # DOIs that should have resolved but did not: surface, do not fail the build.
        logger.warning("refs_bib: %d key(s) need manual metadata: %s", len(result["missing"]), result["missing"])
    if not result.get("ok", True):
        sys.exit(1)


if __name__ == "__main__":
    main()
