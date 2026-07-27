#!/usr/bin/env python3
"""One-time migration: legacy memory.md Rule/Why/Trigger entries -> KB Experience_* cards.

ADR 0017 P2. Converts each `- Rule:/Why:/Trigger:` block in the flat memory.md
into an Experience_* card (kind: negative-constraint) written under
`DATA_DIR/wiki/experience/`, then (with --apply) re-renders memory.md as the
resident compact index via the same logic as `memory.py render-longterm`.

Dry-run by default. This is a human-run migration, not a model tool: it mutates
the external KB and reformats the curated memory.md, so it is intentionally not
in the Codex allowlist and requires an explicit --apply.

    uv run python cli_tools/migrate_memory_md.py                 # dry-run: show plan
    uv run python cli_tools/migrate_memory_md.py --apply         # write cards + re-render
    uv run python cli_tools/migrate_memory_md.py --apply --data-dir ../data
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from _memory import experience as _exp
from _common.paths import data_dir as resolve_data_dir

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MEMORY_MD = REPO_ROOT / "memory.md"

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str, *, limit: int = 6) -> str:
    words = _SLUG_RE.sub("-", text.lower()).strip("-").split("-")
    words = [w for w in words if w and w not in {"the", "a", "an", "do", "not", "of", "to", "in", "for"}]
    return "-".join(words[:limit]) or "rule"


def parse_entries(text: str) -> list[dict[str, str]]:
    """Parse `- Rule: ... / Why: ... / Trigger: ...` blocks."""
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    field: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        m = re.match(r"\s*-\s*Rule:\s*(.*)", line)
        if m:
            if current:
                entries.append(current)
            current = {"statement": m.group(1).strip()}
            field = "statement"
            continue
        if current is None:
            continue
        m = re.match(r"\s*Why:\s*(.*)", line)
        if m:
            current["why"] = m.group(1).strip()
            field = "why"
            continue
        m = re.match(r"\s*Trigger:\s*(.*)", line)
        if m:
            current["trigger"] = m.group(1).strip()
            field = "trigger"
            continue
        if line.strip() and field:
            current[field] = (current.get(field, "") + " " + line.strip()).strip()
    if current:
        entries.append(current)
    return entries


def entry_to_card_fields(entry: dict[str, str], seen: set[str]) -> dict[str, str]:
    cid = f"neg-{slugify(entry['statement'])}"
    base = cid
    n = 2
    while cid in seen:
        cid = f"{base}-{n}"
        n += 1
    seen.add(cid)
    # Problem-specific triggers (referencing a concrete problem id) are flagged in
    # scope so the human promotion gate can decide whether they are truly general.
    trigger = entry.get("trigger", "")
    problem_specific = bool(re.search(r"\b\d{4}_problem|\bproblem_\d", trigger))
    return {
        "type": "experience",
        "kind": "negative-constraint",
        "id": cid,
        "statement": entry["statement"],
        "trigger": trigger,
        "why": entry.get("why", ""),
        "provenance": "[migrated-from-memory-md]",
        "scope": "problem-specific-review" if problem_specific else "general",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate memory.md -> KB Experience_* cards (ADR 0017 P2)")
    parser.add_argument("--memory-file", default=None)
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--apply", action="store_true", help="write cards and re-render memory.md")
    args = parser.parse_args()

    memory_file = Path(args.memory_file) if args.memory_file else DEFAULT_MEMORY_MD
    data_dir = resolve_data_dir(args.data_dir)
    exp_dir = _exp.experience_dir(data_dir)

    text = memory_file.read_text(encoding="utf-8")
    entries = parse_entries(text)
    seen: set[str] = set()
    cards = [entry_to_card_fields(e, seen) for e in entries]

    plan = {
        "memory_file": str(memory_file),
        "experience_dir": str(exp_dir),
        "entries_parsed": len(entries),
        "cards": [{"id": c["id"], "scope": c["scope"], "statement": c["statement"][:70]} for c in cards],
        "applied": False,
    }

    if args.apply:
        exp_dir.mkdir(parents=True, exist_ok=True)
        for c in cards:
            (exp_dir / f"{c['id']}.md").write_text(_exp.card_from_fields(c), encoding="utf-8")
        rendered = _exp.render_memory_md(_exp.load_cards(data_dir))
        memory_file.write_text(rendered, encoding="utf-8")
        plan["applied"] = True
        plan["rendered_lines"] = len(rendered.splitlines())

    print(json.dumps(plan, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
