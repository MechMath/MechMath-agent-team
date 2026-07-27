"""Experience_* card model — the long-term negative-constraint tier.

Long-term negative-constraint / heuristic-threshold cards. Both the card bodies
(`memory/experience/*.md`) and their rendered recall index (repo-root
`memory.md`, two load-bearing lines `trigger` + `statement` per card) live **in
this repository**, and `memory render-longterm` produces the latter from the
former.

Card bodies used to live in the KB (`DATA_DIR/wiki/experience/`), on the ADR 0016
§3.3 reasoning that keeping them there avoided statement drift. That reasoning
does not survive its own §3.4 rule: an experience card may hold only *pointers*
to declarative cards (`refs: [[Concept_X]]`), never a copied theorem statement —
so there is nothing in one that can drift. Routing this tier through the KB only
bought a human promotion gate that never ran, leaving `memory.md` permanently
empty. The tier is now local, written automatically, and read every cycle; the KB
keeps the declarative families (`Concept_`, `Source_`, ...) that genuinely need
one content authority.

No YAML dependency: the frontmatter is simple `key: value` lines, and only a few
fields are load-bearing, so a minimal parser suffices.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# The two load-bearing fields for recall (rendered into memory.md), plus the
# fields that make a card honest/usable. Kept in sync with ADR 0017 §2.
CARD_KINDS = ("negative-constraint", "heuristic-threshold")
CARD_TYPES = ("experience", "error", "obstruction")

FRONTMATTER_KEYS = (
    "type",
    "kind",
    "id",
    "statement",
    "trigger",
    "why",
    "failure_modes",
    "provenance",
    "scope",
    "refs",
    "source",
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def experience_dir(root: Path | None = None) -> Path:
    """Where Experience_* card bodies live: `<repo>/memory/experience/`."""
    return (root or REPO_ROOT) / "memory" / "experience"


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Return (frontmatter dict, body). Minimal `---`-delimited `key: value`
    parser; values are kept as raw strings (lists left verbatim)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    fm: dict[str, str] = {}
    body_start = len(lines)
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            body_start = i + 1
            break
        raw = lines[i]
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        fm[key.strip()] = value.strip()
    body = "\n".join(lines[body_start:]).strip()
    return fm, body


def load_card(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    card = dict(fm)
    card["path"] = str(path)
    card["body"] = body
    card["raw"] = text
    if not card.get("statement"):
        # Fall back to the one-line body as the statement.
        card["statement"] = body.splitlines()[0].strip() if body else ""
    if not card.get("id"):
        card["id"] = path.stem
    return card


def load_cards(root: Path | None = None) -> list[dict[str, Any]]:
    cards_dir = experience_dir(root)
    if not cards_dir.exists():
        return []
    return [load_card(p) for p in sorted(cards_dir.glob("*.md"))]


def slugify(text: str, *, limit: int = 60) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    if len(slug) <= limit:
        return slug or "card"
    # Cut on a word boundary so the id stays readable.
    return slug[:limit].rsplit("-", 1)[0] or slug[:limit]


def normalize_statement(text: str) -> str:
    return " ".join(str(text).lower().split())


def write_card(fields: dict[str, Any], *, root: Path | None = None) -> Path:
    """Write one Experience_* card body, returning its path."""
    cards_dir = experience_dir(root)
    cards_dir.mkdir(parents=True, exist_ok=True)
    card_id = fields.get("id") or f"neg-{slugify(fields.get('statement', ''))}"
    fields = {"type": "experience", **fields, "id": card_id}
    path = cards_dir / f"Experience_{card_id}.md"
    path.write_text(card_from_fields(fields), encoding="utf-8")
    return path


def validate_card(card: dict[str, Any]) -> list[str]:
    """Return a list of problems; empty means valid enough to store."""
    problems: list[str] = []
    if not card.get("statement"):
        problems.append("missing statement")
    if not card.get("trigger"):
        problems.append("missing trigger (recall is load-bearing)")
    kind = card.get("kind", "")
    if kind and kind not in CARD_KINDS:
        problems.append(f"unknown kind {kind!r}; allowed: {', '.join(CARD_KINDS)}")
    return problems


def render_memory_md(cards: list[dict[str, Any]]) -> str:
    """Render the resident compact list (trigger + statement two lines per card)
    that becomes repo-root memory.md. ADR 0016 §3.3."""
    header = [
        "# Long-Term Negative-Constraint Memory",
        "",
        "<!-- GENERATED by `memory render-longterm` from memory/experience/*.md. -->",
        "<!-- Do not edit by hand: edit the cards under memory/experience/ and -->",
        "<!-- re-render. Keep this file at 100 lines or fewer. -->",
        "",
    ]
    lines: list[str] = []
    for card in cards:
        statement = " ".join(str(card.get("statement", "")).split())
        trigger = " ".join(str(card.get("trigger", "")).split())
        cid = card.get("id", "")
        prefix = f"- [{cid}] " if cid else "- "
        lines.append(f"{prefix}{statement}")
        if trigger:
            lines.append(f"  Trigger: {trigger}")
    if not lines:
        lines = ["_(no long-term negative-constraint cards yet)_"]
    return "\n".join(header + lines).rstrip() + "\n"


def card_from_fields(fields: dict[str, Any]) -> str:
    """Serialize a card dict into the on-disk frontmatter+body format."""
    out = ["---"]
    for key in FRONTMATTER_KEYS:
        if key in fields and fields[key] not in (None, ""):
            out.append(f"{key}: {fields[key]}")
    out.append("---")
    out.append(str(fields.get("statement", "")).strip())
    return "\n".join(out) + "\n"
