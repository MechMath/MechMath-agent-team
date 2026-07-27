#!/usr/bin/env python3
"""Statement snapshot and drift checker for Lean tasks."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from pathlib import Path
from typing import Any

from _lean import fileinfo as lean_file_info
from _control import tasks as task_ledger


def normalize(text: str) -> str:
    return " ".join(text.split())


def sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_statement(file_path: Path, declaration: str) -> str:
    result = lean_file_info.extract_statement(file_path, declaration)
    if not result.get("found"):
        raise SystemExit(f"declaration not found: {declaration} in {file_path}")
    return str(result["statement"]).strip()


def workspace_path(workspace: str | Path, path: str | None) -> Path:
    if not path:
        raise SystemExit("task has no path")
    p = Path(path)
    return p if p.is_absolute() else Path(workspace).resolve() / p


def load_task(workspace: str, task_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    data = task_ledger.load_ledger(workspace)
    return data, task_ledger.find_task(data, task_id)


def snapshot_path(workspace: str, task: dict[str, Any], version: int) -> Path:
    return task_ledger.state_dir(workspace) / "statements" / f"{task['id']}.v{version}.statement.lean"


def cmd_snapshot(args: argparse.Namespace) -> None:
    actor = task_ledger.require_actor(args.actor)
    data, task = load_task(args.workspace, args.task)
    declaration = task.get("declaration")
    statement = extract_statement(workspace_path(args.workspace, task.get("target_file")), declaration)
    protected = task.setdefault("protected_statement", {})
    version = int(protected.get("version") or 0) + 1
    out = snapshot_path(args.workspace, task, version)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(statement + "\n", encoding="utf-8")
    protected.update({
        "state": "snapshotted",
        "snapshot_path": str(out.relative_to(Path(args.workspace).resolve())),
        "hash": sha256(normalize(statement)),
        "version": version,
    })
    task_ledger.save_ledger(args.workspace, data, actor)
    print(f"snapshot saved: {out}")


def current_and_snapshot(args: argparse.Namespace) -> tuple[str, str, dict[str, Any]]:
    _, task = load_task(args.workspace, args.task)
    current = extract_statement(workspace_path(args.workspace, task.get("target_file")), task.get("declaration"))
    protected = task.get("protected_statement", {})
    snap_path = workspace_path(args.workspace, protected.get("snapshot_path"))
    if not snap_path.exists():
        raise SystemExit(f"snapshot not found: {snap_path}")
    snapshot = snap_path.read_text(encoding="utf-8")
    return current, snapshot, task


def cmd_check(args: argparse.Namespace) -> None:
    current, snapshot, _ = current_and_snapshot(args)
    current_hash = sha256(normalize(current))
    snapshot_hash = sha256(normalize(snapshot))
    if current_hash != snapshot_hash:
        print("statement_guard: FAIL")
        print(f"current={current_hash}")
        print(f"snapshot={snapshot_hash}")
        raise SystemExit(1)
    print("statement_guard: PASS")


def cmd_diff(args: argparse.Namespace) -> None:
    current, snapshot, _ = current_and_snapshot(args)
    diff = difflib.unified_diff(
        snapshot.splitlines(),
        current.splitlines(),
        fromfile="snapshot",
        tofile="current",
        lineterm="",
    )
    print("\n".join(diff))


def cmd_approve_change(args: argparse.Namespace) -> None:
    cmd_snapshot(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--workspace", required=True)
        p.add_argument("--task", required=True)

    p = sub.add_parser("snapshot")
    common(p); p.add_argument("--actor", default="orchestrator"); p.set_defaults(func=cmd_snapshot)
    p = sub.add_parser("check")
    common(p); p.set_defaults(func=cmd_check)
    p = sub.add_parser("diff")
    common(p); p.set_defaults(func=cmd_diff)
    p = sub.add_parser("approve-change")
    common(p); p.add_argument("--review"); p.add_argument("--actor", default="orchestrator"); p.set_defaults(func=cmd_approve_change)
    p = sub.add_parser("reset-snapshot")
    common(p); p.add_argument("--review"); p.add_argument("--actor", default="orchestrator"); p.set_defaults(func=cmd_approve_change)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
