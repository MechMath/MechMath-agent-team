# FL-Prover — normative rules

**Single source of truth for the four normative sections.** `CLAUDE.md` and `AGENTS.md`
point here and must not restate any of it.

This file exists because the claim did not hold. `CLAUDE.md` stated, in writing, that its
normative content "is identical to `AGENTS.md` and must stay in sync with it". Measured
2026-09-09: the two files differed by **465 diff lines**, and the four sections named in
that very sentence differed by 34, 73, 54 and 8 lines. Nothing checked it, and nothing
could have — a claim of identity between two hand-maintained copies is a claim about the
future.

The divergence was not contradiction; it was elaboration. The Claude copy had grown more
detail over time and the Codex copy had not, which is the more dangerous shape: the two
harnesses were being told the same rules at different resolutions, and only one of them
had the sentence that mattered. The richer text is the one preserved below.

**Platform differences do not belong in this file.** Where a path differs by runtime, both
are named inline. Dispatch mechanics, hooks, and agent-registration formats stay in
`CLAUDE.md` / `AGENTS.md`, which is the only thing they are for now.

`tests/test_normative_single_source.py` enforces this: neither entry document may define
any of these four sections, and both must point here. That test runs in the suite, which —
since 2026-09-09 — actually runs.

## Core Invariants

1. The Orchestrator only routes, records, runs mechanical gates, and dispatches
   the Integrator to merge. It must not act as Formalizer, F-Reviewer,
   F-Generator, Integrator, Golfer, Regulator, or Blueprinter, and must not write
   Lean proof text or change theorem statements.
2. Specialist subagents never spawn other subagents. All coordination flows
   through the Orchestrator via files (hub-and-spoke).
3. **The Lean 4 compiler is the supreme oracle.** A theorem is proved only when
   `cli_tools/lean.py check` reports it compiles with no errors, `sorry`/`admit`
   scanning (`cli_tools/lean.py scan`) is clean, and `cli_tools/lean.py axioms`
   (`#print axioms`) exposes no axiom outside the accepted base. An LLM's belief
   that a proof is correct is never sufficient.
4. A statement may carry a proof only after the F-Reviewer approves it and its
   text is snapshotted by `cli_tools/lean.py guard`. No agent may weaken,
   generalize, or otherwise alter a protected statement to force compilation.
5. Agents communicate through files only and write only to their assigned scratch
   workspace. Speculative proof search happens exclusively in ephemeral
   scratchpads; the baseline repository is never corrupted by trial-and-error.
6. Only the Integrator merges scratch artifacts into the master target file, and
   only after the compiler gate passes. Merges preserve proof logic and protected
   statements.
7. Missing declarations, helper lemmas, intermediate constructions, definition
   bridges, and computational certificates are **proof obligations**, not final
   answers, and must be tracked in the task ledger.
8. Any result imported from outside Mathlib/the project (a cited theorem, a
   computer-certified finite statement) must be recorded with its exact usable
   statement and provenance before it supports a proof, and either fully
   discharged or explicitly retained as an `axiom` with a recorded boundary.
9. `sorry` / `admit` are proof obligations, never accepted terminal states.
   Leaving a computation part as `sorry` is permitted only as an interim ledger
   entry with a named owner and next action.
10. A run is complete only when the target compiles, is sorry-free, its axiom set
    is exactly the intended external assumptions, and the Regulator's final wave
    audit passes.
11. Any non-mechanical change to Lean statements or proofs must have a specialist
    owner. If such an artifact must change, dispatch or resume the responsible
    specialist agent.
12. A prior compiler `PASS` applies only to the exact file/declaration state it
    checked. Any later change requires re-running the affected gate.
13. If a required specialist subagent cannot be spawned or resumed, stop with a
    restartable route/recovery note and next owner. Do not do the specialist's
    work yourself.
14. One failed or inconclusive specialist wave is not exhaustion. Continue by
    popping the next queued task/branch unless terminal stop conditions hold.
15. Every wave must leave a restartable wave summary (via
    `cli_tools/control.py wave`) recording completed/blocked tasks, blocker
    classes, and the next action.


## Routing

The Orchestrator dispatches the specialist that owns the current blocker. **There
is no fixed pipeline** — the roles are owners, not a sequence, and a target may
cycle through them in any order and any number of times. The authoritative
trigger → owner → output → next table is the dispatch cookbook
(`.agents/skills/orchestration/references/subagent-dispatch-cookbook.md` (mounted as `.claude/skills/...` on the Claude side; the tree is one, via a symlink));
consult it rather than a second copy here. The following hold regardless of
order:

- **Every non-trivial wave, first read the resident long-term negative-constraint
  memory** with
  `uv run python cli_tools/memory.py read --tier long-term --view compact <workspace>`
  (the resident `memory.md`). This is a hard precondition — never skip it. Passing
  the workspace also stamps `memory/.longterm_read.json`, the mechanical trace the
  completion gate checks.
- **Refresh and read the mechanical indexes before dispatching:**
  `uv run python cli_tools/memory.py refresh <workspace>` then
  `uv run python cli_tools/memory.py read --tier local <workspace>`; use
  `cli_tools/lean.py index` (Indexing) for the target's declaration/dependency
  outline. After updating the ledger or wave state, refresh again so the index
  reflects reality.
- Dispatch specialists for all non-mechanical work; require their artifacts in
  owned scratch locations. Never convert private Orchestrator reasoning into Lean
  code (invariants 1, 11).
- **Nothing enters the master development without all four gates:**
  `lean.py check` (compiles), `lean.py scan` (no `sorry`/`admit`),
  `lean.py axioms` (no axiom outside the accepted base), and `lean.py guard check`
  (the protected statement still matches its snapshot). Semantics are the fifth
  bar and the only non-mechanical one: the statement must still mean what the
  source reference — book, paper, or user statement — means. That is the
  F-Reviewer's finding, re-checked by the Regulator at wave close.
- Give every dispatched agent exactly one scratchpad, `scratch/<role>/<task_id>/`,
  and name it in the dispatch message
  (`prompts/references/workspace-and-ownership.md`).
- Merge into the master target only via the Integrator, and only after the gates
  pass (invariants 6, 12). If the active task fails, pop the next queued task
  (invariant 14).
- Stop only for a completed target (invariant 10), a documented infeasible
  formalization boundary, genuine human-needed ambiguity, or documented
  branch-budget exhaustion.
- **Never stop without writing memory back.** Before *every* stop, target proved
  or not, run in order:

  ```
  uv run python cli_tools/memory.py refresh <workspace>
  uv run python cli_tools/memory.py aggregate-candidates <workspace>
  uv run python cli_tools/gate.py stop <workspace> [--verified-proof]
  ```

  `aggregate-candidates` promotes the run's candidate cards into
  `memory/experience/` and re-renders `memory.md`; `gate stop` is mechanical and
  must pass. Fix what it reports rather than stopping past it.


## Tool Rules

- **Generic harness facades**, each the single entry over an internal
  `cli_tools/_<name>/` package:
  - `cli_tools/memory.py` — three-tier memory (`read --tier
    local|long-term|kb`, `refresh` [`--check`], `append`, `render-longterm`,
    `aggregate-candidates`, `inbox-write`, `card-lint`).
  - `cli_tools/search.py` — external *literature* search (`arxiv`, `matlas`,
    `index`, `frontier`, `citation-graph`). Lean premise retrieval is
    `lean.py search`, a different thing.
  - `cli_tools/external.py` — external-LLM calls (`gemini`, `gpt`, `discuss`,
    `golf`, `informal`); every result is advisory, never evidence.
  - `cli_tools/gate.py` — mechanical accept/complete checks.
  - `cli_tools/workspace.py` — navigate this problem's files (`references`,
    `presentation`, `ledger`, `refs-bib`).
- **Control plane:** `cli_tools/control.py` — `task` (the ledger) and `wave` (the
  end-of-wave summary).
- **Formal (Lean) tools — `cli_tools/lean.py`, the single entry over
  `cli_tools/_lean/`:**
  - Checking: `lean.py check` (compile via `lake env lean`).
  - Scanning: `lean.py scan` (real `sorry`/`admit` outside comments/strings) and
    `lean.py axioms` (`#print axioms` audit of the final axiom set).
  - Guarding: `lean.py guard` (snapshot/verify protected declarations against
    AST-level tampering).
  - Indexing: `lean.py index` (imports, declarations, outline, dependencies).
  - Searching: `lean.py search {leandex|loogle|leanfinder|leansearch|state|hammer}`.
- These facades and tools are allowlisted for auto-run in `.claude/settings.json`.
- You have three-tier memory (local / long-term / KB); `memory.py` is the only
  memory entry. `memory.md` is the resident long-term negative-constraint list,
  **generated** by `memory.py render-longterm` from the repo-local `Experience_*`
  cards in `memory/experience/`. Read it every wave; do not hand-edit it — edit
  the cards and re-render. Promotion is automatic via
  `memory.py aggregate-candidates`.
- Run Python project tools as `uv run python ...`; do not use bare `python` or
  `python3` for repository scripts. Use `cli_tools/leancheck.sh` when the shell's
  Lean toolchain environment needs fixing before `lake` will run.
- Use `DATA_DIR` for the shared data root when available (default `../data`).
  Agents may read under `DATA_DIR`; agents may write only under `DATA_DIR/workspace`
  and `DATA_DIR/inbox` unless the human approves another target.
- Do not use `git add .`, `git add -A`, destructive Git commands, `rm`, or `mv`
  unless the human explicitly requests that operation.


## Rules for All Agents

1. No axioms or unproved assertions beyond explicitly recorded, boundary-limited
   external assumptions; confirm the axiom set with `#print axioms`.
2. No hand-waving. In the formal setting this means: no `sorry`/`admit` left
   silently, no protected statement weakened to force compilation.
3. Use atomic, compiler-checked proof steps; prefer library lemmas found via the
   Searching tools over re-proving established results.
4. Check theorem and dependency preconditions (types, hypotheses) before use.
5. Do not add or strengthen hypotheses, or narrow a statement, silently.
6. Log meaningful agent activity under `logs/`.
