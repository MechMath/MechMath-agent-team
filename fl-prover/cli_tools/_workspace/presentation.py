#!/usr/bin/env python3
"""Build AI-readable presentation indexes for proof workspaces."""

from __future__ import annotations

import argparse
import shutil
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
from _memory.local import append_entry, ensure_channels, iter_jsonl, channel_path

configure_cli_logging()

SECTIONS = {"proof", "writer", "recovery", "source", "verification", "presentation", "status"}


def presentation_dir(workspace: Path) -> Path:
    return workspace / "presentation"


def file_info(workspace: Path, path: Path, *, view: str) -> dict[str, Any] | None:
    if not path.exists() or not path.is_file():
        return None
    info: dict[str, Any] = {
        "path": relative_to_workspace(path, workspace),
        "size": path.stat().st_size,
        "mtime_ns": path.stat().st_mtime_ns,
    }
    if path.suffix.casefold() in {".md", ".tex", ".txt"}:
        text = read_text(path, limit=12000)
        info["summary"] = summarize_text(text, view=view)
        info["head"] = first_nonempty_lines(text, limit=3)
    return info


def collect_files(workspace: Path, pattern: str, *, view: str) -> list[dict[str, Any]]:
    return [
        info
        for path in sorted(workspace.glob(pattern))
        if (info := file_info(workspace, path, view=view)) is not None
    ]


def phase_from_status(workspace: Path) -> str | None:
    status = workspace / "STATUS.md"
    if not status.exists():
        return None
    lines = status.read_text(encoding="utf-8", errors="replace").splitlines()
    for index, line in enumerate(lines):
        if line.strip().casefold() == "## phase":
            for candidate in lines[index + 1 :]:
                stripped = candidate.strip()
                if stripped:
                    return stripped
    return None


def build_payload(workspace: Path, *, view: str) -> dict[str, Any]:
    proof = file_info(workspace, workspace / "proof.tex", view=view)
    status = file_info(workspace, workspace / "STATUS.md", view=view)
    writer = collect_files(workspace, "writer/*", view=view)
    recovery = collect_files(workspace, "recovery/*.md", view=view)
    source = collect_files(workspace, "routes/source_theorem*.md", view=view) + collect_files(workspace, "queries/*/*.md", view=view)
    verification = collect_files(workspace, "**/review_packet*.md", view=view) + collect_files(workspace, "**/verdict*.md", view=view)
    pdfs = collect_files(workspace, "proof.pdf", view=view) + collect_files(workspace, "progress_notes.pdf", view=view)
    presentation_failures = [
        item for item in writer if "revision_notes" in item.get("path", "") or "failure" in item.get("summary", "").casefold()
    ]
    return {
        "workspace": str(workspace),
        "generated_at_utc": utc_now(),
        "phase": phase_from_status(workspace),
        "proof": proof,
        "status": status,
        "writer": writer,
        "export_pdfs": pdfs,
        "recovery": recovery,
        "source": source,
        "verification": verification,
        "presentation_failures": presentation_failures,
    }


def write_indexes(workspace: Path, payload: dict[str, Any]) -> None:
    root = presentation_dir(workspace)
    root.mkdir(parents=True, exist_ok=True)
    write_json(root / "index.json", payload)
    lines = ["# Presentation Index", ""]
    lines.append(f"- **Phase**: {payload.get('phase') or 'unknown'}")
    proof = payload.get("proof") or {}
    if proof:
        lines.append(f"- **Proof**: {proof.get('path')}")
    pdfs = payload.get("export_pdfs", [])
    lines.append(f"- **Exported PDFs**: {len(pdfs)}")
    for pdf in pdfs:
        lines.append(f"  - {pdf.get('path')}")
    lines.append(f"- **Writer files**: {len(payload.get('writer', []))}")
    lines.append(f"- **Recovery files**: {len(payload.get('recovery', []))}")
    lines.append(f"- **Source files**: {len(payload.get('source', []))}")
    lines.append(f"- **Verification files**: {len(payload.get('verification', []))}")
    if payload.get("presentation_failures"):
        lines.append("- **Presentation failures**: yes")
    (root / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build(workspace: Path, *, view: str) -> dict[str, Any]:
    ensure_channels(workspace)
    payload = build_payload(workspace, view=view)
    write_indexes(workspace, payload)
    append_entry(
        workspace,
        "presentation",
        {
            "kind": "presentation_index",
            "source_path": "presentation/index.json",
            "summary": f"Presentation index built with phase={payload.get('phase') or 'unknown'}",
        },
    )
    return payload


def show(workspace: Path, *, section: str, view: str) -> dict[str, Any]:
    payload = build(workspace, view=view)
    if section not in SECTIONS:
        raise SystemExit(f"unknown section {section!r}; allowed: {', '.join(sorted(SECTIONS))}")
    if section == "presentation":
        return {
            "phase": payload.get("phase"),
            "export_pdfs": payload.get("export_pdfs", []),
            "presentation_failures": payload.get("presentation_failures", []),
        }
    return {section: payload.get(section)}


def latest(workspace: Path, *, section: str, limit: int, view: str) -> dict[str, Any]:
    if section == "presentation":
        channel = "presentation"
    elif section == "recovery":
        channel = "failed_paths"
    elif section == "verification":
        channel = "verification_reports"
    else:
        payload = build(workspace, view=view)
        items = payload.get(section, [])
        if isinstance(items, list):
            return {"section": section, "count": min(len(items), limit), "entries": items[-limit:]}
        return {"section": section, "count": 1 if items else 0, "entries": [items] if items else []}
    ensure_channels(workspace)
    entries = list(iter_jsonl(channel_path(workspace, channel)))[-limit:]
    return {"section": section, "channel": channel, "count": len(entries), "entries": entries}


def sync_static(workspace: Path, *, includes: list[str]) -> dict[str, Any]:
    root = presentation_dir(workspace) / "static"
    root.mkdir(parents=True, exist_ok=True)
    include_set = set(includes or ["writer"])
    copied: list[str] = []
    patterns: list[str] = []
    if "writer" in include_set:
        patterns.extend(["writer/*.tex", "writer/*.md"])
    if "recovery" in include_set:
        patterns.append("recovery/*.md")
    if "source" in include_set:
        patterns.extend(["routes/source_theorem*.md", "queries/*/*.md"])
    if "verification" in include_set:
        patterns.extend(["**/review_packet*.md", "**/verdict*.md"])
    for pattern in patterns:
        for path in sorted(workspace.glob(pattern)):
            if not path.is_file() or presentation_dir(workspace) in path.parents:
                continue
            rel = relative_to_workspace(path, workspace).replace("/", "__")
            target = root / rel
            shutil.copyfile(path, target)
            copied.append(relative_to_workspace(target, workspace))
    return {"ok": True, "count": len(copied), "copied": copied}


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Build presentation indexes")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "show", "latest", "sync-static"):
        p = sub.add_parser(name)
        p.add_argument("workspace")
        p.add_argument("--format", choices=FORMAT_CHOICES, default="json")
        p.add_argument("--view", choices=VIEW_CHOICES, default="compact")
    sub.choices["show"].add_argument("--section", required=True, choices=sorted(SECTIONS))
    sub.choices["latest"].add_argument("--section", required=True, choices=sorted(SECTIONS))
    sub.choices["latest"].add_argument("--limit", type=int, default=5)
    sub.choices["sync-static"].add_argument("--include", action="append", default=[])
    args = parser.parse_args(argv)

    workspace = workspace_path(args.workspace)
    if args.command == "build":
        payload = build(workspace, view=args.view)
    elif args.command == "show":
        payload = show(workspace, section=args.section, view=args.view)
    elif args.command == "latest":
        payload = latest(workspace, section=args.section, limit=args.limit, view=args.view)
    elif args.command == "sync-static":
        payload = sync_static(workspace, includes=args.include)
    else:
        raise AssertionError(args.command)
    emit(payload, fmt=args.format)


if __name__ == "__main__":
    main()
