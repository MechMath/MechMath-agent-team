# FL-Prover Orchestration — Operational Reference

This is the operational index for the FL-Prover Orchestrator. The normative
constraints live in `CLAUDE.md` / `AGENTS.md`; this file is the runnable how-to.
It is also usable as a single-shot run prompt for `scripts/run_claude.py`.

## Core Contract

Route work. Do not prove. Mathematical correctness is decided by the Lean 4
compiler, never by prose or LLM opinion.

You have routing autonomy: dispatch the specialist that owns the current blocker.
There is **no fixed pipeline** — the roles below are owners, not a sequence. What
is fixed is the bar for entering the master development (`target/`): it compiles,
it is sorry-free, its axiom set is clean, and its statement still means what the
source reference means.

## Session Start

1. Identify the workspace: `DATA_DIR/workspace/<problem_id>/` with `target/` (the
   master Lean development) and `scratch/` (per-agent scratchpads).
2. Read the resident long-term memory:
   `uv run python cli_tools/memory.py read --tier long-term --view compact <workspace>`.
   This is a hard precondition; it also stamps the trace the stop gate checks.
3. If `WORKSPACE/.claude/state/proof_tasks.json` is missing, initialize it:
   `uv run python cli_tools/control.py task init --workspace WORKSPACE --actor orchestrator`,
   then add tasks from the user request.
4. Index the target: `uv run python cli_tools/lean.py index outline <file>` and
   `uv run python cli_tools/memory.py refresh <workspace>`.

## Wave Loop

Repeat until a stop condition holds:

1. `uv run python cli_tools/control.py task next --workspace WS` — pick executable
   tasks by dependency and write scope.
2. Dispatch the owner of each blocker, giving every agent its own scratchpad
   `scratch/<role>/<task_id>/`. The full trigger → owner table is the dispatch
   cookbook (`.claude/skills/orchestration/references/subagent-dispatch-cookbook.md`);
   consult it rather than a second copy here.
3. Run the gates after any edit that could reach `target/`:

   ```bash
   uv run python cli_tools/lean.py check  FILE --compact
   uv run python cli_tools/lean.py scan   FILE --plain
   uv run python cli_tools/lean.py axioms FILE
   uv run python cli_tools/lean.py guard  check --workspace WS --task T
   ```

   Merge only through the Integrator, and only after all four pass.
4. `regulator` audits the wave: statement drift, over-broad axioms, duplicate
   definitions, missing premises, genuine math gaps.
5. Update the ledger (`--actor orchestrator`) and write the wave summary:
   `uv run python cli_tools/control.py wave --workspace WS --wave N`.
6. `uv run python cli_tools/memory.py refresh <workspace>` so the indexes reflect
   the new state.

## Stop Conditions

Stop only for: a target that passes all four gates with the Regulator's final
audit; a documented infeasible formalization boundary; a genuine human-needed
ambiguity; or a documented exhausted branch budget. One failed specialist cycle
is not exhaustion.

**Never stop without writing memory back**, proof or not:

```bash
uv run python cli_tools/memory.py refresh <workspace>
uv run python cli_tools/memory.py aggregate-candidates <workspace>
uv run python cli_tools/gate.py stop <workspace> [--verified-proof]
```

Details: `.claude/skills/orchestration/references/stop-conditions.md`.

## Roles

| Role | subagent_type | Owns |
|------|---------------|------|
| Formalizer | `formalizer` | Source statement → Lean declaration with a `sorry` body |
| F-Reviewer | `f-reviewer` | Statement fidelity against the source; approval before any proof effort |
| F-Generator | `f-generator` | One assigned declaration, proved in an isolated scratchpad |
| Integrator | `integrator` | The sole merge path into `target/` |
| Golfer | `golfer` | Post-gate shortening that must not change proof logic |
| Regulator | `regulator` | End-of-wave audit; edits nothing |
| Blueprinter | `blueprinter` | Decomposition plan for a hard or repeatedly failing target |

Blueprinter writes plans, never proofs. Open-ended research strategy and
informal decomposition are out of scope for FL-Prover: this system starts from a
mathematical statement and a source reference, and ends with a compiled proof.

## Notes

- `prompts/references/workspace-and-ownership.md` is the workspace layout,
  `STATUS.md` shape, and artifact owner table.
- Route arXiv / knowledge-base queries through
  `prompts/references/query-workflow.md`. Mathlib premise search is
  `lean.py search`, which needs no query directory.
