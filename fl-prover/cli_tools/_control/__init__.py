"""Control-plane internals behind the `control.py` facade (paper §2.1).

Not model-facing.

- tasks.py  the task ledger (`WORKSPACE/.claude/state/proof_tasks.json`)
- wave.py   the end-of-wave summary generated from that ledger
"""
