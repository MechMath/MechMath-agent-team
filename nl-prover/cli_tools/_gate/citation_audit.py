#!/usr/bin/env python3
"""Final-article citation audit — ADR 0019 §5 / P5 (mechanical half).

Non-mathematical checks run before a PDF is accepted. The mathematical/attribution
half is a fresh Verifier; this tool is the lint that gates it.

Checks (ADR 0019 §5):
  1. every \\citep/\\citet key resolves in refs.bib;
  2. every `cite-as-existing` ledger row is cited at least once (first-use rule);
  3. no ledger result is used as settled support while still `pending-audit`
     or unresolved `borrowed` (its cite_key appears in the article);
  4. attribution detector (#5): a theorem stated as the article's own, whose text
     matches a ledger `source_quality: original theorem` row, with no citation —
     i.e. someone else's result passed off as original.

    gate.py citation-audit <workspace> --tex writer/article_candidate.tex

Presentation failure blocks PDF acceptance but does not change the mathematical
stop status (ADR 0019 / orchestration.md).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from _gate import waiver

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _workspace import ledger as _ledger  # noqa: E402

CITE_RE = re.compile(r"\\cite[a-z]*\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}", re.IGNORECASE)
BIB_KEY_RE = re.compile(r"@\w+\s*\{\s*([^,]+),")
THEOREM_ENV_RE = re.compile(
    r"\\begin\{(theorem|lemma|proposition|corollary)\}(\[[^\]]*\])?(.*?)\\end\{\1\}",
    re.DOTALL | re.IGNORECASE,
)
STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "are", "for", "with",
    "that", "this", "we", "let", "then", "there", "exists", "every", "all", "any",
    "such", "if", "be", "by", "on", "as", "it", "its", "has", "have", "which",
}


REQUIREMENT = waiver.requirement_text(
    checks='citation integrity in the final article: resolvable references, and disclosure\nof mathematical content supplied from outside the run.',
    legal='externally supplied mathematics is a provenance fact, not run history, and\nmust survive into reader-facing output',
    fix='Add the citation, or disclose the external source.',
)

# Wording that says content came from outside this run.
EXTERNAL_SUPPLY = re.compile(
    r"\b(?:imported|externally supplied|supplied externally|external manuscript|"
    r"external package|provided by the human|human-supplied)\b",
    re.IGNORECASE,
)


def cited_keys(tex: str) -> set[str]:
    keys: set[str] = set()
    for match in CITE_RE.finditer(tex):
        for key in match.group(1).split(","):
            key = key.strip()
            if key:
                keys.add(key)
    return keys


def bib_keys(bib: str) -> set[str]:
    return {m.group(1).strip() for m in BIB_KEY_RE.finditer(bib)}


def tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-zA-Z]+", (text or "").lower()) if len(t) > 2 and t not in STOPWORDS}


def overlap(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a)


def theorem_blocks(tex: str) -> list[dict]:
    blocks = []
    for match in THEOREM_ENV_RE.finditer(tex):
        opt = match.group(2) or ""
        body = match.group(3) or ""
        blocks.append({
            "env": match.group(1),
            "attributed": bool(CITE_RE.search(opt)) or bool(CITE_RE.search(body)),
            "body": body,
        })
    return blocks


def audit(workspace: str | Path, tex_path: str | Path) -> dict:
    tex_path = Path(tex_path)
    if not tex_path.is_absolute():
        tex_path = Path(workspace) / tex_path
    errors: list[str] = []
    warnings: list[str] = []

    try:
        tex = tex_path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "errors": [f"cannot read tex {tex_path}: {exc}"], "warnings": []}

    bib_path = Path(workspace) / "references" / "refs.bib"
    bib = bib_path.read_text(encoding="utf-8") if bib_path.exists() else ""
    defined = bib_keys(bib)
    cited = cited_keys(tex)
    rows = _ledger.load_rows(workspace)

    # 1. every cited key resolves in refs.bib
    for key in sorted(cited - defined):
        errors.append(f"\\cite key {key!r} does not resolve in references/refs.bib")

    # 2. every cite-as-existing ledger row cited at least once
    for row in rows:
        if row.get("trust") == "cite-as-existing":
            key = row.get("cite_key") or row.get("paper_id") or row.get("claim_id")
            if key and key not in cited:
                errors.append(
                    f"cite-as-existing result {row.get('claim_id')!r} (key {key!r}) "
                    "is never cited at its point of use"
                )

    # 3. no pending-audit / unresolved-borrowed result used as settled support
    for row in rows:
        key = row.get("cite_key") or row.get("paper_id") or row.get("claim_id")
        if key and key in cited and row.get("trust") in ("pending-audit", "borrowed"):
            errors.append(
                f"result {row.get('claim_id')!r} (key {key!r}) is cited as settled "
                f"support but its trust is {row.get('trust')!r} (must be cite-as-existing)"
            )

    # 4. attribution detector: unattributed theorem matching an original-theorem row
    originals = [r for r in rows if r.get("source_quality") == "original theorem" and r.get("statement")]
    blocks = theorem_blocks(tex)
    for row in originals:
        row_tok = tokens(row["statement"])
        for block in blocks:
            if block["attributed"]:
                continue
            if overlap(row_tok, tokens(block["body"])) >= 0.6:
                errors.append(
                    f"a \\begin{{{block['env']}}} matches ledger original-theorem "
                    f"{row.get('claim_id')!r} but carries no citation — an existing "
                    "result must be attributed, not presented as original"
                )
                break

    # 5. externally supplied mathematics must survive into reader-facing output.
    #    Stripping agent run history is correct; stripping "the core came from
    #    outside this run" is not. That is a provenance fact, not run history,
    #    and one run lost it exactly this way: ~20 occurrences of "imported" in
    #    proof.tex, 0 in the article, with the source never stated (ADR 0023 Q.3).
    proof_path = Path(workspace) / "proof.tex"
    if proof_path.exists() and proof_path != tex_path:
        try:
            proof_tex = proof_path.read_text(encoding="utf-8")
        except OSError:
            proof_tex = ""
        if EXTERNAL_SUPPLY.search(proof_tex) and not EXTERNAL_SUPPLY.search(tex):
            errors.append(
                "proof.tex discloses externally supplied mathematics but "
                f"{tex_path.name} does not. External supply is a provenance fact, "
                "not run history: disclose where the content came from."
            )

    return {"ok": not errors, "errors": errors, "warnings": warnings,
            "cited": sorted(cited), "defined": sorted(defined)}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Final-article citation audit (ADR 0019 §5)",
        epilog=REQUIREMENT,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("workspace")
    parser.add_argument("--tex", required=True, help="article/proof .tex (absolute or workspace-relative)")
    parser.add_argument("--json", action="store_true")
    waiver.add_waiver_arg(parser)
    args = parser.parse_args(argv)

    result = audit(args.workspace, args.tex)
    # Waive first, then report. Reporting first published a verdict computed
    # before the waiver was applied, so `--json` and the human output could
    # disagree about `ok` on the same run.
    errs, waived = waiver.apply_waiver(
        list(result.get("errors", [])), args.waive, gate="citation-audit",
        workspace=args.workspace,
    )
    result["errors"], result["waived"] = errs, waived
    result["ok"] = not errs
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"citation_audit: {'PASS' if result['ok'] else 'FAIL'} ({args.tex})")
        for e in result["errors"]:
            print(f"ERROR: {e}")
        for w in result["warnings"]:
            print(f"WARNING: {w}")
        waiver.print_waived(waived, args.waive or "")
    if errs and not args.json:
        # Prose after a JSON document makes the document unparseable exactly
        # when it carries something to report. Six of the ten gates did this;
        # only the ones that happened to pass on the workspace they were tried
        # against looked healthy.
        print()
        print(REQUIREMENT)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
