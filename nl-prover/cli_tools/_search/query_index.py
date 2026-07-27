#!/usr/bin/env python3
"""Summarize existing problem-local query outputs into workspace memory."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from _common.indexing import (
    FORMAT_CHOICES,
    VIEW_CHOICES,
    emit,
    first_nonempty_lines,
    read_text,
    relative_to_workspace,
    summarize_text,
    utc_now,
    workspace_path,
    write_json,
)
from _common.paths import configure_cli_logging
from _memory.local import append_entry, ensure_channels

configure_cli_logging()

SOURCE_FILES = {
    "arxiv": ("arxiv.md",),
    "matlas": ("matlas.md",),
    # `collector.md` is the pre-rename name; workspaces written before the
    # Collector -> KB-Manager rename still carry it, so keep reading it.
    "kb-manager": ("kb-manager.md", "collector.md"),
}


def queries_dir(workspace: Path) -> Path:
    return workspace / "queries"


def query_dirs(workspace: Path) -> list[Path]:
    root = queries_dir(workspace)
    if not root.exists():
        return []
    return sorted(path for path in root.iterdir() if path.is_dir())


def summarize_query(workspace: Path, query_id: str, *, view: str) -> dict[str, Any]:
    qdir = queries_dir(workspace) / query_id
    if not qdir.exists():
        raise SystemExit(f"query does not exist: {query_id}")
    request = read_text(qdir / "request.md", limit=4000) if (qdir / "request.md").exists() else ""
    status = read_text(qdir / "status.md", limit=4000) if (qdir / "status.md").exists() else ""
    sources: dict[str, Any] = {}
    for source, filenames in SOURCE_FILES.items():
        path = next((qdir / name for name in filenames if (qdir / name).exists()), None)
        if path is None:
            continue
        text = read_text(path, limit=12000)
        sources[source] = {
            "path": relative_to_workspace(path, workspace),
            "summary": summarize_text(text, view=view),
            "head": first_nonempty_lines(text, limit=3),
        }
    payload = {
        "query_id": query_id,
        "path": relative_to_workspace(qdir, workspace),
        "request_summary": summarize_text(request, view=view),
        "status_summary": summarize_text(status, view=view),
        "sources": sources,
        "updated_at_utc": utc_now(),
    }
    write_query_indexes(workspace, qdir, payload)
    return payload


def write_query_indexes(workspace: Path, qdir: Path, payload: dict[str, Any]) -> None:
    write_json(qdir / "index.json", payload)
    lines = [f"# Query Index: {payload['query_id']}", ""]
    if payload.get("request_summary"):
        lines.extend(["## Request", payload["request_summary"], ""])
    if payload.get("status_summary"):
        lines.extend(["## Status", payload["status_summary"], ""])
    lines.append("## Sources")
    sources = payload.get("sources", {})
    if not sources:
        lines.append("NONE")
    for source, info in sources.items():
        lines.append(f"### {source}")
        lines.append(f"- Path: {info['path']}")
        lines.append(f"- Summary: {info['summary']}")
    (qdir / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def refresh(workspace: Path, *, sources: list[str], view: str) -> dict[str, Any]:
    ensure_channels(workspace)
    selected = set(sources or SOURCE_FILES)
    summaries: list[dict[str, Any]] = []
    for qdir in query_dirs(workspace):
        payload = summarize_query(workspace, qdir.name, view=view)
        filtered_sources = {
            name: info for name, info in payload.get("sources", {}).items() if name in selected
        }
        for source, info in filtered_sources.items():
            append_entry(
                workspace,
                "source_findings",
                {
                    "kind": "query_result",
                    "source": source,
                    "query_id": qdir.name,
                    "source_path": info["path"],
                    "summary": info["summary"],
                },
            )
        summaries.append(payload)
    index = {
        "workspace": str(workspace),
        "generated_at_utc": utc_now(),
        "count": len(summaries),
        "queries": [
            {
                "query_id": item["query_id"],
                "path": item["path"],
                "sources": sorted(item.get("sources", {}).keys()),
            }
            for item in summaries
        ],
    }
    root = queries_dir(workspace)
    root.mkdir(parents=True, exist_ok=True)
    write_json(root / "index.json", index)
    lines = ["# Query Index", ""]
    for item in index["queries"]:
        lines.append(f"- **{item['query_id']}**: {', '.join(item['sources']) or 'no outputs'} ({item['path']})")
    (root / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"ok": True, "count": len(summaries), "queries": summaries, "index": index}


def latest(workspace: Path, *, source: str | None, limit: int, view: str) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for qdir in query_dirs(workspace):
        payload = summarize_query(workspace, qdir.name, view=view)
        if source and source not in payload.get("sources", {}):
            continue
        items.append(payload)
    items.sort(key=lambda item: item.get("updated_at_utc", ""))
    return {"count": min(len(items), limit), "queries": items[-limit:]}


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Index existing query outputs")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("summarize", "refresh", "latest"):
        p = sub.add_parser(name)
        p.add_argument("workspace")
        p.add_argument("--format", choices=FORMAT_CHOICES, default="json")
        p.add_argument("--view", choices=VIEW_CHOICES, default="compact")
    sub.choices["summarize"].add_argument("--query-id", required=True)
    sub.choices["refresh"].add_argument("--source", action="append", choices=sorted(SOURCE_FILES), default=[])
    sub.choices["latest"].add_argument("--source", choices=sorted(SOURCE_FILES))
    sub.choices["latest"].add_argument("--limit", type=int, default=5)
    args = parser.parse_args(argv)

    workspace = workspace_path(args.workspace)
    if args.command == "summarize":
        payload = summarize_query(workspace, args.query_id, view=args.view)
    elif args.command == "refresh":
        payload = refresh(workspace, sources=args.source, view=args.view)
    elif args.command == "latest":
        payload = latest(workspace, source=args.source, limit=args.limit, view=args.view)
    else:
        raise AssertionError(args.command)
    emit(payload, fmt=args.format)


if __name__ == "__main__":
    main()
