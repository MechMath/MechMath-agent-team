#!/usr/bin/env python3
"""Provenance ledger — the connective tissue of ADR 0019.

`<workspace>/references/ledger.jsonl` holds one record per external result the
proof depends on. It is a mechanical index, not mathematics. Two roles author
disjoint field sets (ADR 0019 §1):

- **Searcher** writes provenance facts: claim_id, statement, paper_id, locator,
  source_quality (and an optional doi for bibtex resolution).
- A fresh **Verifier** writes the trust verdict: audit_status,
  independent_warrant, trust. Its auto-FAIL #10 is exactly this source audit.
- `workspace.py refs-bib` fills cite_key.

This module is the safe writer/reader so agents never hand-edit raw JSONL.

    workspace.py ledger add       <workspace> --claim-id ... --paper-id ... ...
    workspace.py ledger set-trust <workspace> --claim-id ... --trust ... ...
    workspace.py ledger list      <workspace>
    workspace.py ledger status    <workspace>
    workspace.py ledger validate  <workspace>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TRUST_LEVELS = ("pending-audit", "borrowed", "cite-as-existing")
SOURCE_QUALITY = ("original theorem", "secondary mention", "derived in paper")
AUDIT_STATUS = ("usable", "needs-source", "needs-local-derivation", "obstruction-candidate", "")
WARRANT = ("PASS", "FAIL", "UNCLEAR", "")

# Fields each role owns (ADR 0019 §1 field-ownership table).
SEARCHER_FIELDS = ("claim_id", "statement", "paper_id", "locator", "source_quality", "doi")
VERIFIER_FIELDS = ("audit_status", "independent_warrant", "trust")
DEFAULT_TRUST = "pending-audit"


def ledger_path(workspace: str | Path) -> Path:
    return Path(workspace) / "references" / "ledger.jsonl"


def load_rows(workspace: str | Path) -> list[dict]:
    path = ledger_path(workspace)
    if not path.exists():
        return []
    rows: list[dict] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed ledger line {lineno} in {path}: {exc}") from exc
    return rows


def save_rows(workspace: str | Path, rows: list[dict]) -> None:
    path = ledger_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)
    path.write_text(body, encoding="utf-8")


def get(workspace: str | Path, claim_id: str) -> dict | None:
    for row in load_rows(workspace):
        if row.get("claim_id") == claim_id:
            return row
    return None


def add_row(
    workspace: str | Path,
    claim_id: str,
    *,
    statement: str = "",
    paper_id: str = "",
    locator: str = "",
    source_quality: str = "",
    doi: str = "",
) -> dict:
    """Searcher-side insert/update of provenance facts. Idempotent on claim_id.

    Never touches trust fields: a re-add updates provenance but leaves an
    existing Verifier verdict intact (and defaults new rows to pending-audit).
    """
    if not claim_id:
        return {"ok": False, "error": "claim_id is required"}
    if source_quality and source_quality not in SOURCE_QUALITY:
        return {"ok": False, "error": f"source_quality must be one of {list(SOURCE_QUALITY)}"}
    rows = load_rows(workspace)
    by_id = {r.get("claim_id"): r for r in rows}
    provenance = {
        "claim_id": claim_id,
        "statement": statement,
        "paper_id": paper_id,
        "locator": locator,
        "source_quality": source_quality,
        "doi": doi,
    }
    if claim_id in by_id:
        row = by_id[claim_id]
        for key, value in provenance.items():
            if value:
                row[key] = value
        created = False
    else:
        row = {**provenance, "audit_status": "", "independent_warrant": "", "trust": DEFAULT_TRUST, "cite_key": ""}
        rows.append(row)
        created = True
    save_rows(workspace, rows)
    return {"ok": True, "created": created, "claim_id": claim_id, "row": row}


def set_trust(
    workspace: str | Path,
    claim_id: str,
    *,
    trust: str,
    audit_status: str = "",
    independent_warrant: str = "",
) -> dict:
    """Verifier-side write of the trust verdict. Only a fresh Verifier calls this."""
    if trust not in TRUST_LEVELS:
        return {"ok": False, "error": f"trust must be one of {list(TRUST_LEVELS)}"}
    if audit_status and audit_status not in AUDIT_STATUS:
        return {"ok": False, "error": f"audit_status must be one of {list(a for a in AUDIT_STATUS if a)}"}
    if independent_warrant and independent_warrant not in WARRANT:
        return {"ok": False, "error": f"independent_warrant must be one of {list(w for w in WARRANT if w)}"}
    rows = load_rows(workspace)
    for row in rows:
        if row.get("claim_id") == claim_id:
            row["trust"] = trust
            if audit_status:
                row["audit_status"] = audit_status
            if independent_warrant:
                row["independent_warrant"] = independent_warrant
            save_rows(workspace, rows)
            return {"ok": True, "claim_id": claim_id, "row": row}
    return {"ok": False, "error": f"unknown claim_id {claim_id!r}"}


def set_cite_key(workspace: str | Path, claim_id: str, cite_key: str) -> dict:
    """refs-bib fills this. Kept here so all ledger writes go through one module."""
    rows = load_rows(workspace)
    for row in rows:
        if row.get("claim_id") == claim_id:
            row["cite_key"] = cite_key
            save_rows(workspace, rows)
            return {"ok": True, "claim_id": claim_id, "cite_key": cite_key}
    return {"ok": False, "error": f"unknown claim_id {claim_id!r}"}


def validate(workspace: str | Path) -> dict:
    errors: list[str] = []
    try:
        rows = load_rows(workspace)
    except ValueError as exc:
        return {"ok": False, "errors": [str(exc)]}
    seen: set[str] = set()
    for index, row in enumerate(rows, 1):
        cid = row.get("claim_id")
        if not cid:
            errors.append(f"row {index}: missing claim_id")
            continue
        if cid in seen:
            errors.append(f"row {index}: duplicate claim_id {cid!r}")
        seen.add(cid)
        if row.get("trust") not in TRUST_LEVELS:
            errors.append(f"{cid}: trust {row.get('trust')!r} not one of {list(TRUST_LEVELS)}")
        sq = row.get("source_quality", "")
        if sq and sq not in SOURCE_QUALITY:
            errors.append(f"{cid}: source_quality {sq!r} invalid")
    return {"ok": not errors, "errors": errors, "rows": len(rows)}


def status(workspace: str | Path) -> dict:
    rows = load_rows(workspace)
    by_trust = {t: 0 for t in TRUST_LEVELS}
    for row in rows:
        by_trust[row.get("trust", DEFAULT_TRUST)] = by_trust.get(row.get("trust", DEFAULT_TRUST), 0) + 1
    return {
        "ok": True,
        "total": len(rows),
        "by_trust": by_trust,
        "pending": [r["claim_id"] for r in rows if r.get("trust") == "pending-audit"],
        "borrowed": [r["claim_id"] for r in rows if r.get("trust") == "borrowed"],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Provenance ledger (ADR 0019 §1)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Searcher: insert/update provenance fields")
    p_add.add_argument("workspace")
    p_add.add_argument("--claim-id", required=True)
    p_add.add_argument("--statement", default="")
    p_add.add_argument("--paper-id", default="")
    p_add.add_argument("--locator", default="")
    p_add.add_argument("--source-quality", default="", choices=[s for s in SOURCE_QUALITY] + [""])
    p_add.add_argument("--doi", default="")

    p_trust = sub.add_parser("set-trust", help="Verifier: write the trust verdict")
    p_trust.add_argument("workspace")
    p_trust.add_argument("--claim-id", required=True)
    p_trust.add_argument("--trust", required=True, choices=list(TRUST_LEVELS))
    p_trust.add_argument("--audit-status", default="")
    p_trust.add_argument("--independent-warrant", default="")

    p_list = sub.add_parser("list", help="print all rows")
    p_list.add_argument("workspace")

    p_status = sub.add_parser("status", help="trust-level counts")
    p_status.add_argument("workspace")

    p_val = sub.add_parser("validate", help="schema check")
    p_val.add_argument("workspace")

    args = parser.parse_args(argv)

    if args.command == "add":
        result = add_row(
            args.workspace, args.claim_id, statement=args.statement, paper_id=args.paper_id,
            locator=args.locator, source_quality=args.source_quality, doi=args.doi,
        )
    elif args.command == "set-trust":
        result = set_trust(
            args.workspace, args.claim_id, trust=args.trust,
            audit_status=args.audit_status, independent_warrant=args.independent_warrant,
        )
    elif args.command == "list":
        result = {"ok": True, "rows": load_rows(args.workspace)}
    elif args.command == "status":
        result = status(args.workspace)
    else:
        result = validate(args.workspace)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("ok", True):
        sys.exit(1)


if __name__ == "__main__":
    main()
