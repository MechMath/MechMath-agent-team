# Task Ledger Format

The task ledger is `WORKSPACE/.claude/state/proof_tasks.json`.

Only `orchestrator` may use write commands (paper §2.1). Every other agent — the Integrator included — uses the read commands and requests ledger changes in its report.

Use:

```bash
uv run python cli_tools/control.py task list --workspace WORKSPACE
uv run python cli_tools/control.py task show --workspace WORKSPACE TASK_ID
uv run python cli_tools/control.py task next --workspace WORKSPACE --readonly
uv run python cli_tools/control.py task validate --workspace WORKSPACE
```

Write commands require `--actor orchestrator`.
