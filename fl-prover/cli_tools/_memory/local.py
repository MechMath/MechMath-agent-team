#!/usr/bin/env python3
"""Workspace-local JSONL memory ledger tools."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _common.indexing import (
    FORMAT_CHOICES,
    VIEW_CHOICES,
    append_jsonl,
    emit,
    first_nonempty_lines,
    iter_jsonl,
    read_text,
    relative_to_workspace,
    score_query,
    summarize_text,
    utc_now,
    workspace_path,
    write_json,
)
from _common.paths import configure_cli_logging

configure_cli_logging()

CHANNELS = {
    "branch_states",
    "failed_paths",
    "verification_reports",
    "source_findings",
    "presentation",
}

# Artifacts whose mtime defines "the index is stale" (ADR 0020 B.2, Q3).
# Kept narrow (STATUS.md only) so the gate does not over-fire; widen this tuple
# to include e.g. "routes"/"recovery" if a broader baseline is wanted.
STALE_BASELINE = ("STATUS.md",)


def memory_dir(workspace: Path) -> Path:
    return workspace / "memory"


def _epoch_to_utc(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def baseline_paths(workspace: Path) -> list[Path]:
    return [workspace / name for name in STALE_BASELINE]


def staleness(workspace: Path) -> dict[str, Any]:
    """Is the local index stale relative to STATUS.md (and any other baseline
    artifact)? Stale = a baseline artifact is newer than memory/index.json, or the
    index does not exist yet. Read-only; does not rebuild (ADR 0020 B.2)."""
    index_json = memory_dir(workspace) / "index.json"
    present = [p for p in baseline_paths(workspace) if p.exists()]
    baseline_rel = [relative_to_workspace(p, workspace) for p in present]
    if not index_json.exists():
        return {
            "ok": True,
            "stale": True,
            "reason": "no local index yet; run `memory.py refresh`",
            "baseline": baseline_rel,
            "newer_than_index": baseline_rel,
        }
    index_mtime = index_json.stat().st_mtime
    newer: list[str] = []
    baseline_mtime = 0.0
    for p in present:
        m = p.stat().st_mtime
        baseline_mtime = max(baseline_mtime, m)
        if m > index_mtime:
            newer.append(relative_to_workspace(p, workspace))
    return {
        "ok": True,
        "stale": bool(newer),
        "index_generated_at_utc": _epoch_to_utc(index_mtime),
        "baseline_mtime_utc": _epoch_to_utc(baseline_mtime) if present else None,
        "baseline": baseline_rel,
        "newer_than_index": newer,
    }


def channel_path(workspace: Path, channel: str) -> Path:
    if channel not in CHANNELS:
        raise SystemExit(f"unknown channel {channel!r}; allowed: {', '.join(sorted(CHANNELS))}")
    return memory_dir(workspace) / f"{channel}.jsonl"


def ensure_channels(workspace: Path) -> None:
    root = memory_dir(workspace)
    root.mkdir(parents=True, exist_ok=True)
    for channel in CHANNELS:
        channel_path(workspace, channel).touch(exist_ok=True)


def entry_key(entry: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(entry.get("channel", "")),
        str(entry.get("kind", "")),
        str(entry.get("source_path", "")),
    )


def existing_keys(workspace: Path) -> set[tuple[str, str, str]]:
    keys: set[tuple[str, str, str]] = set()
    for channel in CHANNELS:
        for entry in iter_jsonl(channel_path(workspace, channel)):
            keys.add(entry_key(entry))
    return keys


def append_entry(workspace: Path, channel: str, record: dict[str, Any]) -> dict[str, Any]:
    ensure_channels(workspace)
    entry = {
        "timestamp_utc": utc_now(),
        "channel": channel,
        **record,
    }
    append_jsonl(channel_path(workspace, channel), entry)
    return entry


def source_record(workspace: Path, source: Path, *, channel: str, kind: str, view: str) -> dict[str, Any]:
    text = read_text(source, limit=8000)
    return {
        "kind": kind,
        "source_path": relative_to_workspace(source, workspace),
        "summary": summarize_text(text, view=view),
        "head": first_nonempty_lines(text, limit=3),
    }


def append_from_source(workspace: Path, *, channel: str, source: str, kind: str, view: str) -> dict[str, Any]:
    source_path = (workspace / source).resolve() if not Path(source).is_absolute() else Path(source).resolve()
    if not source_path.exists():
        raise SystemExit(f"source does not exist: {source}")
    return append_entry(workspace, channel, source_record(workspace, source_path, channel=channel, kind=kind, view=view))


def refresh(workspace: Path, *, view: str, check: bool = False) -> dict[str, Any]:
    # --check is a read-only staleness probe: report whether the existing index
    # is stale vs the baseline without rebuilding (ADR 0020 B.2).
    if check:
        return staleness(workspace)
    ensure_channels(workspace)
    keys = existing_keys(workspace)
    added: list[dict[str, Any]] = []
    patterns = [
        ("branch_states", "status", ["STATUS.md"]),
        ("failed_paths", "recovery", ["recovery/*.md", "routes/proof_review*.md"]),
        ("verification_reports", "verifier_packet", ["**/review_packet*.md", "**/verdict*.md"]),
        ("source_findings", "query", ["queries/*/*.md"]),
        ("presentation", "writer", ["writer/*.tex", "writer/*.md", "proof.pdf", "progress_notes.pdf"]),
    ]
    for channel, kind, globs in patterns:
        for pattern in globs:
            for path in sorted(workspace.glob(pattern)):
                if not path.is_file():
                    continue
                record = source_record(workspace, path, channel=channel, kind=kind, view=view)
                if entry_key({"channel": channel, **record}) in keys:
                    continue
                added.append(append_entry(workspace, channel, record))
    index = build_index(workspace)
    return {"ok": True, "added": len(added), "entries": added, "index": index}


def build_index(workspace: Path) -> dict[str, Any]:
    ensure_channels(workspace)
    channels: dict[str, Any] = {}
    for channel in sorted(CHANNELS):
        entries = list(iter_jsonl(channel_path(workspace, channel)))
        channels[channel] = {
            "count": len(entries),
            "latest": entries[-5:],
            "path": relative_to_workspace(channel_path(workspace, channel), workspace),
        }
    payload = {
        "workspace": str(workspace),
        "generated_at_utc": utc_now(),
        "channels": channels,
    }
    write_json(memory_dir(workspace) / "index.json", payload)
    (memory_dir(workspace) / "index.md").write_text(render_index_md(payload), encoding="utf-8")
    return payload


def render_index_md(payload: dict[str, Any]) -> str:
    """Render the index.md so a model reading only index.md sees the latest content
    of every channel, not just counts (ADR 0016 §3.2: no dead json)."""
    lines = ["# Workspace Memory Index", ""]
    lines.append(f"_Generated {payload.get('generated_at_utc', '')} (UTC)._")
    lines.append(
        "_Freshness: run `memory.py refresh --check <workspace>` to test whether "
        "this index is stale vs `STATUS.md` before relying on it (ADR 0020)._"
    )
    lines.append("")
    for channel, info in payload["channels"].items():
        lines.append(f"## {channel} — {info['count']} records ({info['path']})")
        latest = info.get("latest") or []
        if not latest:
            lines.append("_(no entries)_")
            lines.append("")
            continue
        for entry in latest:
            kind = entry.get("kind", "")
            src = entry.get("source_path", "")
            summary = summarize_text(str(entry.get("summary", "")), view="compact")
            summary = " ".join(summary.split())
            prefix = f"- `{src}`" if src else "-"
            if kind:
                prefix += f" [{kind}]"
            lines.append(f"{prefix}: {summary}" if summary else prefix)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def show(workspace: Path, *, channel: str, view: str, latest: int | None, limit: int) -> dict[str, Any]:
    ensure_channels(workspace)
    entries = list(iter_jsonl(channel_path(workspace, channel)))
    if latest is not None:
        entries = entries[-latest:]
    else:
        entries = entries[:limit]
    if view == "compact":
        entries = [
            {
                "timestamp_utc": item.get("timestamp_utc"),
                "kind": item.get("kind"),
                "source_path": item.get("source_path"),
                "summary": summarize_text(str(item.get("summary", "")), view="compact"),
            }
            for item in entries
        ]
    return {"channel": channel, "count": len(entries), "entries": entries}


def search(workspace: Path, *, query: str, channels: list[str], limit: int, view: str) -> dict[str, Any]:
    ensure_channels(workspace)
    selected = channels or sorted(CHANNELS)
    results: list[dict[str, Any]] = []
    for channel in selected:
        for entry in iter_jsonl(channel_path(workspace, channel)):
            haystack = json.dumps(entry, ensure_ascii=False)
            score = score_query(query, haystack)
            if score <= 0:
                continue
            result = dict(entry)
            result["score"] = score
            if view == "compact":
                result = {
                    "channel": channel,
                    "score": score,
                    "kind": entry.get("kind"),
                    "source_path": entry.get("source_path"),
                    "summary": summarize_text(str(entry.get("summary", haystack)), view="compact"),
                }
            results.append(result)
    results.sort(key=lambda item: (-float(item.get("score", 0)), str(item.get("source_path", ""))))
    return {"query": query, "count": min(len(results), limit), "results": results[:limit]}


# This is an internal library module of the memory package: it has no CLI of its
# own. The model-facing entry is `cli_tools/memory.py` (memory.py read/refresh/…),
# which drives these functions directly.
