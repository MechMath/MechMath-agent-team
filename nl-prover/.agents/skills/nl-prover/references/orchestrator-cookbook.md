# Orchestrator Cookbook

The Orchestrator is a hub-and-spoke dispatcher. It owns `STATUS.md`,
`proof.tex`, route history, branch queues, and final user-facing state. It does
not supply missing mathematical proof, verification, definitions, theorem
preconditions, computations, counterexamples, or reader-facing mathematical
exposition from private reasoning.

## Operating Guide (advisory)

This is the *typical* order for a non-terminal workspace, not a mandatory loop.
The Orchestrator keeps the routing autonomy declared in `orchestration.md`'s Core
Contract and dispatches by the current blocker. The only hard parts are the step-1
preconditions and the invariant-level rules (single-pass verification, `PASS`
before merge, pop the next branch on failure) — not the step ordering:

1. At the start of every non-trivial cycle, load memory and refresh the
   mechanical indexes before dispatching. First (hard precondition) read the
   long-term negative-constraint memory:
   `uv run python cli_tools/memory.py read --tier long-term --view compact`.
   Then refresh and read the local tier:
   `uv run python cli_tools/memory.py refresh <workspace> --view compact` and
   `uv run python cli_tools/memory.py read --tier local <workspace>`; also
   refresh `search.py index`, `workspace.py references`, and `workspace.py presentation`
   when their inputs are relevant. This is a required step, not an optional
   alternative to scanning the directory. Then read `problem.md`, `STATUS.md`,
   route history, latest review packets, recovery packets, and relevant
   specialist artifacts.
2. Identify the smallest current blocker. Classify it as proof-local, plan/DAG,
   source theorem, definition/notation, route strategy, computation, final
   assembly, obstruction risk, writing/exposition, or human-needed.
3. Choose the smallest specialist that owns that blocker. Use
   `subagent-dispatch-cookbook.md` when unsure.
4. Spawn or resume that specialist with explicit input paths, write target,
   blocker, and acceptance condition.
5. Collect the specialist artifact. If it requests another specialist, treat
   that request as a handoff artifact and dispatch through the Orchestrator.
6. Run fresh Verifier checks when a plan, proof, refinement, or terminal
   obstruction is being adopted.
7. Update `STATUS.md`, route history, and the active branch queue, then record
   the change in workspace memory so the ledger stays current. Run
   `memory.py refresh <workspace>` to pick up updated `STATUS.md`, recovery, and
   review-packet files, and use
   `memory.py append <workspace> --channel <channel> --source <file> --kind <label>`
   for artifacts the refresh globs do not cover.
8. Continue with the next queued branch unless `stop-conditions.md` permits a
   terminal stop.
9. At a permitted stop, write memory back before stopping: `memory.py refresh`,
   then `memory.py aggregate-candidates <workspace>` to promote the run's
   candidate lessons into `memory/experience/` and re-render the resident
   `memory.md`, then `gate.py stop <workspace>
   [--verified-proof]`, which must pass. This applies to every stop, not only a
   verified proof — the completion gate covers only the proof path
   (`stop-conditions.md`, ADR 0022).

## Handoff Format

When an agent needs another agent, require a short handoff:

```markdown
## Handoff Request
- Requested owner:
- File target:
- Context paths:
- Atomic blocker:
- Acceptance condition:
- Queued alternatives affected:
```

The Orchestrator reads the handoff and dispatches the next owner. Subagents do
not message, spawn, or command each other directly.

## Orchestrator Self-Check

Before writing or editing any artifact, ask:

- Is this `STATUS.md`, route history, query routing, branch queue, or verified
  merge assembly? If yes, Orchestrator may own it.
- Does this change mathematical content, a target contract, a lemma statement,
  a proof attempt, a proof repair, theorem support, definition reading,
  computation evidence, or a verification packet? If yes, dispatch a
  specialist instead.
- Am I writing reader-facing article prose, a local rewrite, or a progress note?
  If yes, dispatch Writer instead.
- Am I using a mechanical check as a substitute for mathematical verification?
  If yes, route to Verifier.
- Am I stopping because no proof exists yet? If yes, update the branch queue
  and continue unless stop conditions permit stopping.

## Refiner Trigger

After a complete proof passes fresh verification, retain that proof as the
fallback and dispatch Refiner once for shortening or cleanup unless the
human explicitly disables shortening. The refined proof replaces the fallback
only after fresh verification accepts it.

## Presentation And Reporting Trigger

Presentation is a reader-facing layer, not a mathematical stop condition. After a
verified proof (and after Refiner is accepted, rejected, or skipped) dispatch
Writer in `FULL_ARTICLE`/`COMPLETE_PROOF` mode.

**Before any stop that is not a verified proof, dispatch Writer in
`PROGRESS_NOTES` mode first.** This covers a verified obstruction, a
human-needed ambiguity, an exhausted branch budget, and a human-requested pause.
This is not a licence to stop early: the stop must already be permitted by
`stop-conditions.md`. The progress notes are what you leave behind when it is.

The full flow — Writer dispatch, `refs-bib`, the `citation-audit` gate, KLMM
compilation, and the exported `proof.pdf` / `progress_notes.pdf` — is the SSOT in
`prompts/references/latex-and-blueprint.md`. A presentation failure keeps the
proof's mathematical status unchanged (record it as pending).
