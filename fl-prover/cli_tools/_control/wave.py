#!/usr/bin/env python3
"""Generate a draft wave summary from workspace state."""

from __future__ import annotations

import argparse
from pathlib import Path

from _control import tasks as task_ledger


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--wave", type=int, required=True)
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    data = task_ledger.load_ledger(args.workspace)
    state = task_ledger.state_dir(args.workspace)
    output = Path(args.output) if args.output else state / "summaries" / f"wave{args.wave}.md"
    output.parent.mkdir(parents=True, exist_ok=True)

    active = [t for t in data.get("tasks", []) if t.get("status") in {"active", "needs-proof", "needs-integration", "needs-review", "needs-blueprint"}]
    done = [t for t in data.get("tasks", []) if t.get("status") == "done"]
    blocked = [t for t in data.get("tasks", []) if t.get("status") == "blocked"]

    lines = [
        "# Wave Summary",
        "",
        f"- workspace: {Path(args.workspace).resolve()}",
        f"- wave: {args.wave}",
        f"- current ledger wave: {data.get('current_wave')}",
        "",
        "## Active Tasks",
    ]
    lines.extend(f"- {t.get('id')} [{t.get('status')}] owner={t.get('owner')} next={t.get('routing', {}).get('next_owner')}" for t in active)
    lines.extend(["", "## Completed Tasks"])
    lines.extend(f"- {t.get('id')}" for t in done)
    lines.extend(["", "## Blocked Tasks"])
    lines.extend(f"- {t.get('id')}: {t.get('routing', {}).get('blocker_class')}" for t in blocked)
    lines.extend(["", "## Regulator Notes", "", "- regulator verdict:", "- next recommended wave:"])

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
