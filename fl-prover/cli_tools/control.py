#!/usr/bin/env python3
"""control — the control plane entry: task ledger and wave summaries (paper §2.1).

    control task {list|show|next|validate} --workspace W
    control task {init|add|set-status|set-owner|add-dependency|add-report|
                  record-check|record-summary|apply-patch} --workspace W --actor orchestrator
    control wave --workspace W --wave N [--output FILE]

Read commands are open to every agent; write commands require
`--actor orchestrator` (the Orchestrator is the sole ledger writer). Specialists
request ledger changes through their reports.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _control import tasks, wave

DISPATCH = {"task": tasks.main, "wave": wave.main}
USAGE = "usage: control {task|wave} [args...]"


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(USAGE)
        sys.exit(0 if len(sys.argv) >= 2 else 2)
    cmd = sys.argv[1]
    if cmd not in DISPATCH:
        print(f"unknown subcommand {cmd!r}\n{USAGE}", file=sys.stderr)
        sys.exit(2)
    DISPATCH[cmd](sys.argv[2:])


if __name__ == "__main__":
    main()
