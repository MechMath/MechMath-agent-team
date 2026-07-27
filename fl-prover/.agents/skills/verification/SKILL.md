---
name: verification
description: "Use after Lean edits, before claiming completion, or when auditing a proof task. Provides the deterministic Lean gates behind cli_tools/lean.py: compile check, sorry/admit scan, axiom-set audit, and protected-statement guard."
---

# Verification Tools

Tools for deterministic Lean verification. Use this skill after any meaningful Lean edit, before marking a task done, and when the Orchestrator or Integrator audits a wave.

## Available Tools

| Tool | Purpose | When to use |
|------|---------|-------------|
| **lean-check** | Compile a Lean file and report errors (local, no API key) | First step to validate any proof attempt |
| **no-sorry scan** | Check for `sorry` or `admit` placeholders | Before claiming a theorem or file is complete |
| **file info** | Inspect declarations, statements, imports, and file outline | When a role needs local file structure without reading the whole file |
| **statement-guard** | Check protected statements against snapshots | Before proof work and before completion in task-ledger workflows |
| **axioms** | `#print axioms` audit of the declarations' final axiom set | Before declaring a target done, and before any Integrator merge |

## Core Gate

For a normal Lean proof task, run the smallest useful deterministic gate:

```bash
uv run python cli_tools/lean.py check FILE --compact
uv run python cli_tools/lean.py scan FILE --plain
uv run python cli_tools/lean.py axioms FILE
uv run python cli_tools/lean.py guard check --workspace WORKSPACE --task TASK_ID
```

`check` alone is not the gate. A file can compile while still depending on
`sorryAx` through an import, or on a project-local `axiom` someone added to get
past a hard step — `scan` and `axioms` are what catch those. `axioms` accepts the
classical base (`propext`, `Classical.choice`, `Quot.sound`) and reports anything
else; widen it only with an explicit, recorded `--allow`.

Use `lean.py guard` when the task has a ledger entry or protected statement snapshot. An F-Generator agent must not change protected statements to remove `sorry`. For task-ledger workflows, the detailed statement guard procedure lives in `../orchestration/references/statement-guard.md`.

Use more detailed output only when needed:

```bash
uv run python cli_tools/lean.py check FILE --summary --severity error
uv run python cli_tools/lean.py check FILE --summary --severity warning
uv run python cli_tools/lean.py scan FILE --context-lines 2
uv run python cli_tools/lean.py index statement FILE DECL_NAME
uv run python cli_tools/lean.py index declarations FILE --kind theorem --name-contains local
```

Lean compilation is the authority. Do not replace these gates with external proof validators or LLM judgment.

For full parameters and examples, read `reference-lean-check.md`.
