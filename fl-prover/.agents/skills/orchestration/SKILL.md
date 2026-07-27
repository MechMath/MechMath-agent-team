---
name: orchestration
description: "FL-Prover orchestration cookbook for multi-agent Lean 4 runs. Use when the Orchestrator manages a Lean workspace, chooses specialist subagents, maintains the task ledger and wave queue, runs the compile/sorry/axiom gates, or diagnoses a stalled target. Trigger on statement not yet formalized, statement-fidelity doubt, failing or stalled proof attempt, missing Mathlib premise, merge into the master file, verbose proof, end-of-wave audit, protected-statement drift, unexpected axiom, or unclear artifact ownership."
---

# FL-Prover Orchestration Cookbook

Use this skill to run a Lean workspace without doing specialist work inside the
Orchestrator. **It is not a fixed pipeline.** There is no mandated
Formalizer → F-Reviewer → F-Generator → Integrator → Golfer → Regulator order:
dispatch whichever specialist owns the current blocker, in whatever order the
target demands, as often as it takes.

What is *not* negotiable is what may enter the master Lean development:

1. it compiles (`lean.py check`);
2. it is free of `sorry` / `admit` (`lean.py scan`);
3. its axiom set is the accepted base and nothing more (`lean.py axioms`);
4. its statement still says what the source reference says — the book, paper, or
   user statement the target came from — and matches the guarded snapshot
   (`lean.py guard check`).

Everything else in this cookbook is advice about how to get there efficiently.

## Quick Dispatch

| Need | First reference |
|------|-----------------|
| Choose the next specialist | [subagent-dispatch-cookbook.md](references/subagent-dispatch-cookbook.md) |
| Run the merge gates | [gates.md](references/gates.md) |
| Ledger commands and fields | [task-ledger-format.md](references/task-ledger-format.md) |
| Protect / verify a statement | [statement-guard.md](references/statement-guard.md) |
| Close a wave | [wave-summary.md](references/wave-summary.md) |
| Decide whether stopping is allowed | [stop-conditions.md](references/stop-conditions.md) |
| Who may write what | [../../../prompts/references/workspace-and-ownership.md](../../../prompts/references/workspace-and-ownership.md) |

## Specialist Summary

Blueprinter decomposes a hard target into a dependency-ordered helper-lemma plan;
Formalizer turns source statements into Lean declarations with `sorry` bodies;
F-Reviewer judges statement fidelity against the source before any proof effort;
F-Generator proves one assigned declaration inside an isolated scratchpad;
Integrator is the only agent that merges into the master development; Golfer
shortens an already-passing proof without changing its logic; Regulator audits a
finished wave for statement drift, duplicate definitions, and unexpected axioms.

## State

Control-plane state lives under `WORKSPACE/.claude/state/`. If
`proof_tasks.json` is missing, only the Orchestrator initializes it:

```bash
uv run python cli_tools/control.py task init --workspace WORKSPACE --actor orchestrator
```

Create explicit task entries before dispatching, and record each dispatch's
outcome — a specialist cycle that leaves no ledger trace did not happen.

## Skills

| Skill | Description |
|-------|-------------|
| [verification](../verification/SKILL.md) | The deterministic Lean gates: check, scan, axioms, guard |
| [lean-search](../lean-search/SKILL.md) | Premise retrieval: leandex, loogle, leanfinder, leansearch, state, hammer |
| [formalize](../formalize/SKILL.md) | Informal mathematics → faithful Lean declarations |
| [sorrifier](../sorrifier/SKILL.md) | Isolate a failing proof step into a helper lemma |
| [knowledge](../knowledge/SKILL.md) | KB-Manager tier: read the index, write `Lean_*` / `Experience_*` cards |
| [memory-routing](../memory-routing/SKILL.md) | Which memory tier a new fact or lesson belongs to |
| [llm](../llm/SKILL.md) | External-LLM support: informal draft, discussion, cross-check, golf |

## Environment variables

- `OPENROUTER_API_KEY` — preferred for the `external.py` tools
- `GEMINI_API_KEY` / `OPENAI_API_KEY` — direct-API fallbacks
- `LEANDEX_API_KEY` — Leandex semantic search
- `LEAN_ELAN_HOME` — only when elan does not live in `~/.elan`
