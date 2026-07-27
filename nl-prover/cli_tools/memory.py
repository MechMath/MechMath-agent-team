#!/usr/bin/env python3
"""Unified three-tier memory entry point (ADR 0016 §3.7).

The ONLY memory tool exposed to the model. The tier logic lives in the internal
package `cli_tools/_memory/` (`local` = former workspace_memory, `kb` = former
kb_manager_summary, `experience` = the Experience_* card model); this file is the
single outer interface over them, adds the long-term resident tier (`memory.md`),
and provides `render-longterm` (Phase 2) and `aggregate-candidates` (Phase 3.5).

    memory read    --tier local|long-term|kb --view compact|summary|full [--query ...] [workspace]
    memory refresh [--tier local] <workspace>
    memory render-longterm            # KB Experience_* cards -> memory.md
    memory aggregate-candidates <workspace>   # dedup candidate cards -> inbox

Nothing in `_memory/` is model-facing or in the Codex allowlist; only `memory.py`
is. The `search.py index` and `workspace.py presentation` internal packages import
the local tier from `_memory.local`.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _memory import local as _local
from _memory import kb as _kb
from _memory import experience as _exp
from _memory import inbox as _write
from _memory import cardlint as _cardlint
from _common.indexing import FORMAT_CHOICES, VIEW_CHOICES, emit, iter_jsonl, score_query, summarize_text, workspace_path
from _common.paths import configure_cli_logging, data_dir as resolve_data_dir

configure_cli_logging()

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MEMORY_MD = REPO_ROOT / "memory.md"

TIERS = ("local", "long-term", "kb")


def _envelope(tier: str, view: str, payload: dict[str, Any]) -> dict[str, Any]:
    out = {"tier": tier, "view": view}
    out.update(payload)
    return out


# ADR 0020 B.0: leave a mechanical trace that long-term memory was read this run,
# so the completion gate can verify the hard precondition mechanically.
LONGTERM_READ_MARKER = ".longterm_read.json"


def _stamp_longterm_read(workspace: Path) -> str | None:
    try:
        mem = workspace / "memory"
        mem.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        (mem / LONGTERM_READ_MARKER).write_text(
            json.dumps({"read_at_utc": ts}) + "\n", encoding="utf-8"
        )
        return ts
    except OSError:
        return None


# --- read ------------------------------------------------------------------

def read_local(workspace: Path, *, view: str, query: str | None) -> dict[str, Any]:
    if query:
        return _local.search(workspace, query=query, channels=[], limit=10, view=view)
    index_path = _local.memory_dir(workspace) / "index.json"
    if not index_path.exists():
        return {
            "ok": False,
            "hint": f"no local index yet; run `memory refresh --tier local {workspace}`",
        }
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    if view == "compact":
        # Drop the heavy `latest` bodies; keep counts + a one-line head per channel.
        channels = {}
        for name, info in payload.get("channels", {}).items():
            latest = info.get("latest") or []
            heads = [summarize_text(str(e.get("summary", "")), view="compact") for e in latest[-3:]]
            channels[name] = {"count": info.get("count", 0), "path": info.get("path"), "recent": heads}
        payload = {"ok": True, "workspace": payload.get("workspace"), "channels": channels}
    else:
        payload = {"ok": True, **payload}
    return payload


def _longterm_cards(query: str | None, card_root: Path | None) -> list[dict[str, Any]]:
    cards = _exp.load_cards(card_root)
    if query:
        scored = []
        for c in cards:
            hay = " ".join(str(c.get(k, "")) for k in ("statement", "trigger", "why", "body"))
            if score_query(query, hay) > 0:
                scored.append(c)
        cards = scored
    return cards


def read_longterm(*, view: str, query: str | None, memory_file: Path, card_root: Path | None = None) -> dict[str, Any]:
    if view == "full":
        cards = _longterm_cards(query, card_root)
        return {"ok": True, "count": len(cards), "cards": [
            {k: c.get(k) for k in ("id", "kind", "statement", "trigger", "why", "failure_modes", "provenance", "scope", "refs", "path")}
            for c in cards
        ]}
    # compact / summary: the resident memory.md list (recall path, no KB pull).
    if not memory_file.exists():
        return {"ok": False, "hint": f"no {memory_file.name}; run `memory render-longterm`"}
    text = memory_file.read_text(encoding="utf-8")
    if query:
        kept = [ln for ln in text.splitlines() if score_query(query, ln) > 0 or ln.startswith("#")]
        text = "\n".join(kept)
    return {"ok": True, "source": str(memory_file), "content": text}


def read_kb(*, view: str, query: str | None, data_dir: Path) -> dict[str, Any]:
    # The KB tier always returns the compact index plus a pointer to fetch full
    # cards, regardless of --view: the KB never holds recall, and full card bodies
    # come from the kb-manager query workflow, not from this read. So `--view full`
    # and `--view compact` behave the same here (the view arg is accepted for a
    # uniform interface but is a no-op for the KB tier).
    payload = _kb.build_summary(str(data_dir))
    if not payload.get("ok"):
        return payload
    if query:
        def keep(items: list[str]) -> list[str]:
            return [it for it in items if score_query(query, it) > 0]
        payload = dict(payload)
        for key in ("concepts", "analyses", "experience"):
            payload[key] = keep(payload.get(key, []))
    payload["note"] = (
        "compact KB index; to read a full card body, run the kb-manager query "
        "workflow (queries/<id>/) — the KB tier never returns full bodies here"
    )
    return payload


# --- render-longterm -------------------------------------------------------

def render_longterm(*, memory_file: Path, force: bool = False, card_root: Path | None = None) -> dict[str, Any]:
    cards = _exp.load_cards(card_root)
    # ADR §3.5 guard: a non-empty existing memory.md must not be silently blanked
    # because no card bodies were found (e.g. a render run before migration).
    if not cards and memory_file.exists():
        existing = memory_file.read_text(encoding="utf-8")
        has_content = any(ln.strip() and not ln.lstrip().startswith(("#", "<!--")) for ln in existing.splitlines())
        if has_content and not force:
            return {
                "ok": False,
                "error": "refusing to overwrite a non-empty memory.md with an empty render "
                         f"(no Experience_* cards in {_exp.experience_dir(card_root)}). Pass --force to blank it.",
                "cards": 0,
                "memory_file": str(memory_file),
            }
    problems = {c["id"]: p for c in cards if (p := _exp.validate_card(c))}
    text = _exp.render_memory_md(cards)
    memory_file.write_text(text, encoding="utf-8")
    line_count = len(text.splitlines())
    return {
        "ok": True,
        "cards": len(cards),
        "memory_file": str(memory_file),
        "lines": line_count,
        "over_100_line_cap": line_count > 100,
        "invalid_cards": problems,
    }


# --- aggregate-candidates --------------------------------------------------

def _normalize(text: str) -> str:
    return " ".join(str(text).lower().split())


PROMOTION_RECEIPT = "candidates_promoted.json"


def aggregate_candidates(
    workspace: Path,
    *,
    promote: bool = True,
    memory_file: Path | None = None,
    card_root: Path | None = None,
) -> dict[str, Any]:
    """Dedup a run's candidate cards and promote them into the local long-term
    tier, then re-render `memory.md`.

    Promotion used to mean "write a note into the KB inbox and wait for a human
    to file it into `DATA_DIR/wiki/experience/`". That hop never ran, so nothing
    ever reached `memory.md`. Cards now land directly in `memory/experience/`
    and the recall index is rebuilt in the same call — written automatically,
    loaded every cycle.
    """
    cand_dir = _local.memory_dir(workspace) / "candidates"
    records: list[dict[str, Any]] = []
    if cand_dir.exists():
        for path in sorted(cand_dir.glob("*.jsonl")):
            records.extend(iter_jsonl(path))
    # Drop explicit no-constraint markers; they satisfy the production-side lint
    # but carry nothing to promote.
    cards = [r for r in records if not r.get("no_constraint")]
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for r in cards:
        key = (str(r.get("kind", "")), _normalize(r.get("statement", "")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    out_path = _local.memory_dir(workspace) / "candidates_aggregated.jsonl"
    _local.memory_dir(workspace).mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for r in deduped:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    result: dict[str, Any] = {
        "ok": True,
        "candidates_found": len(records),
        "after_dedup": len(deduped),
        "aggregated_file": str(out_path),
        "promoted": [],
        "already_present": [],
        "rejected": {},
    }
    if not promote:
        return result

    # Dedup against the cards already in the long-term tier, so re-running a
    # workspace does not stack duplicate constraints into memory.md.
    existing = {
        (str(c.get("kind", "")), _exp.normalize_statement(c.get("statement", "")))
        for c in _exp.load_cards(card_root)
    }
    for r in deduped:
        statement = str(r.get("statement", ""))
        key = (str(r.get("kind", "")), _exp.normalize_statement(statement))
        if key in existing:
            result["already_present"].append(statement)
            continue
        problems = _exp.validate_card(r)
        if problems:
            # A card without a trigger cannot be recalled, so it is not usable
            # as long-term memory; report it rather than storing a dead card.
            result["rejected"][statement or "<no statement>"] = problems
            continue
        fields = {k: v for k, v in r.items() if k in _exp.FRONTMATTER_KEYS}
        fields.setdefault("kind", "negative-constraint")
        fields["source"] = workspace.name
        path = _exp.write_card(fields, root=card_root)
        existing.add(key)
        result["promoted"].append(path.name)

    receipt = _local.memory_dir(workspace) / PROMOTION_RECEIPT
    receipt.write_text(
        json.dumps(
            {
                "promoted": result["promoted"],
                "already_present": len(result["already_present"]),
                "rejected": len(result["rejected"]),
                "candidates": len(deduped),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    result["receipt"] = str(receipt)
    result["render"] = render_longterm(
        memory_file=memory_file or DEFAULT_MEMORY_MD, force=True, card_root=card_root
    )
    return result


# --- CLI -------------------------------------------------------------------

def main() -> None:
    # inbox-write and card-lint have their own full argparse in the memory
    # package; forward to them so `memory.py` stays the single memory entry.
    if len(sys.argv) >= 2 and sys.argv[1] == "inbox-write":
        return _write.main(sys.argv[2:])
    if len(sys.argv) >= 2 and sys.argv[1] == "card-lint":
        return _cardlint.main(sys.argv[2:])

    parser = argparse.ArgumentParser(
        description="Unified three-tier memory (ADR 0016)",
        epilog="also: `memory.py inbox-write ...` (write a KB inbox note), "
               "`memory.py card-lint <file> [--fact]` (long-term/KB boundary lint)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_read = sub.add_parser("read", help="read a memory tier")
    p_read.add_argument("workspace", nargs="?", help="workspace path (required for --tier local)")
    p_read.add_argument("--tier", choices=TIERS, required=True)
    p_read.add_argument("--view", choices=VIEW_CHOICES, default="compact")
    p_read.add_argument("--query", default=None)
    p_read.add_argument("--data-dir", default=None)
    p_read.add_argument("--memory-file", default=None)
    p_read.add_argument("--format", choices=FORMAT_CHOICES, default="json")

    p_ref = sub.add_parser("refresh", help="refresh a memory tier")
    p_ref.add_argument("workspace")
    p_ref.add_argument("--tier", choices=("local",), default="local")
    p_ref.add_argument("--view", choices=VIEW_CHOICES, default="compact")
    p_ref.add_argument("--check", action="store_true",
                       help="read-only: exit non-zero if the local index is stale "
                            "vs STATUS.md, without rebuilding (ADR 0020)")
    p_ref.add_argument("--format", choices=FORMAT_CHOICES, default="json")

    # append a single artifact the refresh glob misses (ADR 0016 §3.2 step 5).
    p_app = sub.add_parser("append", help="append one local-tier artifact the refresh glob misses")
    p_app.add_argument("workspace")
    p_app.add_argument("--channel", required=True, choices=sorted(_local.CHANNELS))
    p_app.add_argument("--source", required=True)
    p_app.add_argument("--kind", required=True)
    p_app.add_argument("--view", choices=VIEW_CHOICES, default="compact")
    p_app.add_argument("--format", choices=FORMAT_CHOICES, default="json")

    p_rl = sub.add_parser("render-longterm", help="render memory.md from KB Experience_* cards")
    p_rl.add_argument("--data-dir", default=None)
    p_rl.add_argument("--memory-file", default=None)
    p_rl.add_argument("--force", action="store_true", help="overwrite even when render would empty a non-empty memory.md")
    p_rl.add_argument("--format", choices=FORMAT_CHOICES, default="json")

    p_ag = sub.add_parser(
        "aggregate-candidates", help="dedup candidate cards into the long-term tier and re-render memory.md"
    )
    p_ag.add_argument("workspace")
    p_ag.add_argument("--data-dir", default=None)
    p_ag.add_argument("--memory-file", default=None)
    p_ag.add_argument(
        "--no-promote",
        action="store_true",
        help="only dedup into candidates_aggregated.jsonl; do not write cards or re-render memory.md",
    )
    p_ag.add_argument("--format", choices=FORMAT_CHOICES, default="json")

    args = parser.parse_args()
    data_dir = resolve_data_dir(getattr(args, "data_dir", None))
    memory_file = Path(args.memory_file) if getattr(args, "memory_file", None) else DEFAULT_MEMORY_MD

    if args.command == "read":
        if args.tier == "local":
            if not args.workspace:
                raise SystemExit("--tier local requires a workspace argument")
            payload = read_local(workspace_path(args.workspace), view=args.view, query=args.query)
        elif args.tier == "long-term":
            payload = read_longterm(view=args.view, query=args.query, memory_file=memory_file)
            if args.workspace:
                ts = _stamp_longterm_read(workspace_path(args.workspace))
                if ts:
                    payload = {**payload, "read_trace_utc": ts}
        else:
            payload = read_kb(view=args.view, query=args.query, data_dir=data_dir)
        emit(_envelope(args.tier, args.view, payload), fmt=args.format)
    elif args.command == "refresh":
        payload = _local.refresh(workspace_path(args.workspace), view=args.view, check=args.check)
        emit(_envelope("local", args.view, payload), fmt=args.format)
        if args.check and payload.get("stale"):
            raise SystemExit(1)
    elif args.command == "append":
        payload = _local.append_from_source(
            workspace_path(args.workspace), channel=args.channel, source=args.source, kind=args.kind, view=args.view
        )
        emit(_envelope("local", args.view, payload), fmt=args.format)
    elif args.command == "render-longterm":
        emit(render_longterm(memory_file=memory_file, force=args.force), fmt=args.format)
    elif args.command == "aggregate-candidates":
        emit(
            aggregate_candidates(
                workspace_path(args.workspace),
                promote=not args.no_promote,
                memory_file=memory_file,
            ),
            fmt=args.format,
        )
    else:
        raise AssertionError(args.command)


if __name__ == "__main__":
    main()
