#!/usr/bin/env python3
"""Workspace task ledger helper for Lean agent orchestration."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Paper §2.1: the Orchestrator is the sole ledger writer. Specialists —
# Integrator included — request ledger changes through their reports.
WRITE_ACTORS = {"orchestrator"}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def state_dir(workspace: str | Path) -> Path:
    return Path(workspace).resolve() / ".claude" / "state"


def ledger_path(workspace: str | Path) -> Path:
    return state_dir(workspace) / "proof_tasks.json"


def default_ledger(workspace: Path) -> dict[str, Any]:
    return {
        "version": 1,
        "workspace_root": str(workspace.resolve()),
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "updated_by": "orchestrator",
        "current_wave": 0,
        "tasks": [],
    }


def require_actor(actor: str | None) -> str:
    if actor not in WRITE_ACTORS:
        allowed = ", ".join(sorted(WRITE_ACTORS))
        raise SystemExit(f"write command requires --actor in {{{allowed}}}")
    return actor


def load_ledger(workspace: str | Path) -> dict[str, Any]:
    path = ledger_path(workspace)
    if not path.exists():
        raise SystemExit(f"ledger not found: {path}\nRun: task_ledger.py init --workspace {Path(workspace).resolve()} --actor orchestrator")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_ledger(workspace: str | Path, data: dict[str, Any], actor: str) -> None:
    path = ledger_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = now_iso()
    data["updated_by"] = actor
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    tmp.replace(path)


def find_task(data: dict[str, Any], task_id: str) -> dict[str, Any]:
    for task in data.get("tasks", []):
        if task.get("id") == task_id:
            return task
    raise SystemExit(f"task not found: {task_id}")


def validate_data(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("version") != 1:
        errors.append("version must be 1")
    if not data.get("workspace_root"):
        errors.append("workspace_root is required")
    seen: set[str] = set()
    for i, task in enumerate(data.get("tasks", [])):
        tid = task.get("id")
        if not tid:
            errors.append(f"tasks[{i}].id is required")
        elif tid in seen:
            errors.append(f"duplicate task id: {tid}")
        else:
            seen.add(tid)
        if not task.get("status"):
            errors.append(f"task {tid or i}: status is required")
        if not task.get("target_file"):
            errors.append(f"task {tid or i}: target_file is required")
    return errors


def print_json(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def cmd_init(args: argparse.Namespace) -> None:
    actor = require_actor(args.actor)
    workspace = Path(args.workspace).resolve()
    path = ledger_path(workspace)
    if path.exists() and not args.force:
        raise SystemExit(f"ledger already exists: {path}")
    for sub in ["summaries", "statements", "reports", "route_notes"]:
        (state_dir(workspace) / sub).mkdir(parents=True, exist_ok=True)
    save_ledger(workspace, default_ledger(workspace), actor)
    print(f"initialized ledger: {path}")


def cmd_list(args: argparse.Namespace) -> None:
    data = load_ledger(args.workspace)
    tasks = data.get("tasks", [])
    if args.status:
        tasks = [t for t in tasks if t.get("status") == args.status]
    for task in tasks:
        print(f"{task.get('id')} [{task.get('status')}] owner={task.get('owner', '-')} next={task.get('routing', {}).get('next_owner', '-')}")


def cmd_show(args: argparse.Namespace) -> None:
    print_json(find_task(load_ledger(args.workspace), args.task_id))


def cmd_next(args: argparse.Namespace) -> None:
    data = load_ledger(args.workspace)
    tasks = data.get("tasks", [])
    actionable = [
        t for t in tasks
        if t.get("status") in {"active", "needs-formalization", "needs-review", "needs-blueprint", "needs-proof", "needs-integration", "needs-golf"}
    ]
    actionable.sort(key=lambda t: (-int(t.get("priority", 0)), t.get("id", "")))
    print_json(actionable[0] if actionable else {"next": None})


def cmd_add(args: argparse.Namespace) -> None:
    actor = require_actor(args.actor)
    data = load_ledger(args.workspace)
    if any(t.get("id") == args.id for t in data.get("tasks", [])):
        raise SystemExit(f"task already exists: {args.id}")
    task = {
        "id": args.id,
        "kind": args.kind,
        "status": args.status,
        "priority": args.priority,
        "target_file": args.file,
        "declaration": args.decl,
        "source_paths": [],
        "dependencies": [],
        "blocked_by": [],
        "owner": args.owner,
        "write_scope": {"mode": "scratch-first", "allowed_files": [args.file], "protected_regions": [f"statement:{args.decl}"] if args.decl else []},
        "protected_statement": {"state": "uninitialized", "snapshot_path": None, "hash": None, "version": 0, "change_policy": "review-required", "approved_change": None},
        "proof_state": {"has_sorry": None, "last_lean_check": None},
        "routing": {"last_owner": None, "next_owner": args.owner, "blocker_class": None, "next_action": None},
        "artifacts": {"reports": [], "route_notes": [], "summaries": []},
    }
    data.setdefault("tasks", []).append(task)
    save_ledger(args.workspace, data, actor)
    print(f"added task: {args.id}")


def cmd_set_status(args: argparse.Namespace) -> None:
    actor = require_actor(args.actor)
    data = load_ledger(args.workspace)
    task = find_task(data, args.task_id)
    task["status"] = args.status
    save_ledger(args.workspace, data, actor)
    print(f"{args.task_id}: status={args.status}")


def cmd_set_owner(args: argparse.Namespace) -> None:
    actor = require_actor(args.actor)
    data = load_ledger(args.workspace)
    task = find_task(data, args.task_id)
    task["owner"] = args.owner
    task.setdefault("routing", {})["next_owner"] = args.owner
    save_ledger(args.workspace, data, actor)
    print(f"{args.task_id}: owner={args.owner}")


def cmd_add_dependency(args: argparse.Namespace) -> None:
    actor = require_actor(args.actor)
    data = load_ledger(args.workspace)
    task = find_task(data, args.task_id)
    deps = task.setdefault("dependencies", [])
    if args.dependency_id not in deps:
        deps.append(args.dependency_id)
    save_ledger(args.workspace, data, actor)
    print(f"{args.task_id}: dependency added {args.dependency_id}")


def cmd_add_report(args: argparse.Namespace) -> None:
    actor = require_actor(args.actor)
    data = load_ledger(args.workspace)
    task = find_task(data, args.task_id)
    reports = task.setdefault("artifacts", {}).setdefault("reports", [])
    if args.path not in reports:
        reports.append(args.path)
    save_ledger(args.workspace, data, actor)
    print(f"{args.task_id}: report added {args.path}")


def cmd_record_check(args: argparse.Namespace) -> None:
    actor = require_actor(args.actor)
    data = load_ledger(args.workspace)
    task = find_task(data, args.task_id)
    task.setdefault("proof_state", {})["last_lean_check"] = {
        "status": args.status,
        "checked_at": now_iso(),
        "command": args.command,
        "artifact": args.artifact,
    }
    save_ledger(args.workspace, data, actor)
    print(f"{args.task_id}: lean_check={args.status}")


def cmd_record_summary(args: argparse.Namespace) -> None:
    actor = require_actor(args.actor)
    data = load_ledger(args.workspace)
    data["current_wave"] = max(int(data.get("current_wave", 0)), args.wave)
    for task in data.get("tasks", []):
        if args.task_id is None or task.get("id") == args.task_id:
            summaries = task.setdefault("artifacts", {}).setdefault("summaries", [])
            if args.path not in summaries:
                summaries.append(args.path)
    save_ledger(args.workspace, data, actor)
    print(f"wave {args.wave}: summary recorded {args.path}")


def merge_task(task: dict[str, Any], patch: dict[str, Any]) -> None:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(task.get(key), dict):
            task[key].update(value)
        else:
            task[key] = value


def cmd_apply_patch(args: argparse.Namespace) -> None:
    actor = require_actor(args.actor)
    data = load_ledger(args.workspace)
    patch_path = Path(args.patch_json)
    patch = json.loads(patch_path.read_text(encoding="utf-8"))
    for item in patch.get("tasks", []):
        task = find_task(data, item["id"])
        merge_task(task, {k: v for k, v in item.items() if k != "id"})
    if "current_wave" in patch:
        data["current_wave"] = patch["current_wave"]
    save_ledger(args.workspace, data, actor)
    print(f"applied patch: {patch_path}")


def cmd_validate(args: argparse.Namespace) -> None:
    data = load_ledger(args.workspace)
    errors = validate_data(data)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
    print("ledger ok")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=(
            "Read-only commands: list, show, next, validate. "
            "Write commands: init, add, set-status, set-owner, add-dependency, "
            "add-report, record-check, record-summary, apply-patch. "
            "Write commands require --actor orchestrator."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_workspace(p: argparse.ArgumentParser) -> None:
        p.add_argument("--workspace", required=True)

    def add_actor(p: argparse.ArgumentParser) -> None:
        p.add_argument("--actor", required=True, choices=sorted(WRITE_ACTORS))

    p = sub.add_parser("init")
    add_workspace(p); add_actor(p); p.add_argument("--force", action="store_true"); p.set_defaults(func=cmd_init)
    p = sub.add_parser("list")
    add_workspace(p); p.add_argument("--status"); p.set_defaults(func=cmd_list)
    p = sub.add_parser("show")
    add_workspace(p); p.add_argument("task_id"); p.set_defaults(func=cmd_show)
    p = sub.add_parser("next")
    add_workspace(p); p.add_argument("--readonly", action="store_true"); p.set_defaults(func=cmd_next)
    p = sub.add_parser("add")
    add_workspace(p); add_actor(p); p.add_argument("--id", required=True); p.add_argument("--file", required=True); p.add_argument("--decl"); p.add_argument("--kind", default="theorem"); p.add_argument("--status", default="todo"); p.add_argument("--priority", type=int, default=0); p.add_argument("--owner", default="f-generator"); p.set_defaults(func=cmd_add)
    p = sub.add_parser("set-status")
    add_workspace(p); add_actor(p); p.add_argument("task_id"); p.add_argument("status"); p.set_defaults(func=cmd_set_status)
    p = sub.add_parser("set-owner")
    add_workspace(p); add_actor(p); p.add_argument("task_id"); p.add_argument("owner"); p.set_defaults(func=cmd_set_owner)
    p = sub.add_parser("add-dependency")
    add_workspace(p); add_actor(p); p.add_argument("task_id"); p.add_argument("dependency_id"); p.set_defaults(func=cmd_add_dependency)
    p = sub.add_parser("add-report")
    add_workspace(p); add_actor(p); p.add_argument("task_id"); p.add_argument("path"); p.set_defaults(func=cmd_add_report)
    p = sub.add_parser("record-check")
    add_workspace(p); add_actor(p); p.add_argument("task_id"); p.add_argument("--status", required=True); p.add_argument("--artifact"); p.add_argument("--command"); p.set_defaults(func=cmd_record_check)
    p = sub.add_parser("record-summary")
    add_workspace(p); add_actor(p); p.add_argument("--wave", type=int, required=True); p.add_argument("--path", required=True); p.add_argument("--task-id"); p.set_defaults(func=cmd_record_summary)
    p = sub.add_parser("apply-patch")
    add_workspace(p); add_actor(p); p.add_argument("patch_json"); p.set_defaults(func=cmd_apply_patch)
    p = sub.add_parser("validate")
    add_workspace(p); p.set_defaults(func=cmd_validate)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
