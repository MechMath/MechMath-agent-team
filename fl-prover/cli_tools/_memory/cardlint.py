#!/usr/bin/env python3
"""Boundary lint for the long-term / KB memory split (ADR 0016 Phase 5, §3.4).

Two boundaries are enforced:

1. Long-term Experience_* cards must be compact negative-constraint cards that
   REFERENCE declarative facts via pointers (`refs:`), never inline a theorem
   statement. Inlining causes statement drift (ADR 0016 §3.4 "risk A").
       uv run python cli_tools/experience_card_lint.py <card.md>

2. KB fact content (Concept_/Source_ cards, inbox notes destined for the wiki)
   must not smuggle transferable behavioral constraints ("do not ...", "never
   ...") — those belong in the long-term tier, not the fact KB.
       uv run python cli_tools/experience_card_lint.py --fact <note.md>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from _memory import experience as _exp

# Words that mark a stated declarative result inlined into a card body.
_THEOREM_WORDS = re.compile(r"\b(theorem|lemma|proposition|corollary)\b", re.IGNORECASE)
# Imperative negative-constraint language (belongs in long-term memory, not a fact).
_CONSTRAINT_LANG = re.compile(
    r"\b(do not|don't|must not|never|avoid|refrain from|should not)\b", re.IGNORECASE
)
_MATH = re.compile(r"\$[^$]+\$|\\\([^)]+\\\)|\\\[[^\]]+\\\]")


def lint_experience_card(path: Path) -> list[str]:
    card = _exp.load_card(path)
    errors: list[str] = _exp.validate_card(card)

    statement = str(card.get("statement", ""))
    if "\n" in statement.strip():
        errors.append("statement must be a compact one-line boundary, not multi-line")
    if len(statement) > 240:
        errors.append(f"statement is {len(statement)} chars; keep it a compact one-line boundary (<=240)")

    body = str(card.get("body", ""))
    has_refs = bool(str(card.get("refs", "")).strip() or str(card.get("evidence_refs", "")).strip())
    if _THEOREM_WORDS.search(body) and not has_refs:
        errors.append(
            "long-term card appears to inline a theorem/lemma statement without a "
            "`refs:` pointer; reference the KB fact instead (ADR 0016 §3.4)"
        )
    if _MATH.search(statement) and not has_refs:
        # A boundary may mention a symbol, but heavy math usually means an inlined fact.
        errors.append(
            "statement carries inline math but no `refs:` pointer; if it depends on a "
            "stated fact, point to the KB card rather than copying it"
        )
    return errors


def lint_fact_content(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    hits = sorted({m.group(0).lower() for m in _CONSTRAINT_LANG.finditer(text)})
    if hits:
        errors.append(
            "fact/KB content contains behavioral-constraint language "
            f"({', '.join(hits)}); transferable 'don't do X' boundaries belong in the "
            "long-term tier (Experience_* card), not the fact KB"
        )
    return errors


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Long-term/KB boundary lint (ADR 0016 Phase 5)")
    parser.add_argument("path", type=Path)
    parser.add_argument("--fact", action="store_true", help="lint as KB fact content (reject constraint language)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    errors = lint_fact_content(args.path) if args.fact else lint_experience_card(args.path)
    ok = not errors
    if args.json:
        print(json.dumps({"ok": ok, "path": str(args.path), "errors": errors}, ensure_ascii=False))
    else:
        if ok:
            print(f"OK: {args.path}")
        else:
            for e in errors:
                print(f"ERROR: {e}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
