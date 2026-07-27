# Subagent Dispatch Cookbook

Dispatch the smallest specialist that owns the current blocker. There is no fixed
order — a run may formalize, prove, bounce back to review, blueprint a
decomposition, and prove again, in any sequence the target demands.

| Situation | Dispatch | Output | Next |
|-----------|----------|--------|------|
| Source statement is not yet in Lean | `formalizer` | `scratch/formalizer/<task>/*.lean` with `sorry` bodies | `f-reviewer` |
| A Lean statement may not mean what the source says | `f-reviewer` | `reviews/statement_<task>.md` | snapshot with `lean.py guard snapshot`, then `f-generator` |
| An approved statement needs a proof | `f-generator` (one target each, isolated scratchpad) | candidate proof in `scratch/f-generator/<task>/` | gates, then `integrator` |
| Target is too large, or the same target failed repeatedly | `blueprinter` | `blueprint/plan_<N>.md` | `formalizer` for the helper statements, then `f-generator` per item |
| A step needs a library lemma nobody can name | `f-generator` with the `lean-search` skill (`lean.py search ...`) | premise candidates in the scratchpad | continue the proof, or `blueprinter` if the gap is structural |
| A proof is nearly there but one subgoal blocks it | `f-generator` with the `sorrifier` skill | helper lemma extracted as its own task | ledger entry for the helper, then `f-generator` |
| A candidate proof passes the gates | `integrator` | merge into `target/` | `regulator` at wave close |
| A merged proof is verbose or ugly | `golfer` | shorter proof candidate | gates again — a golfed proof is a candidate, not a proof |
| A wave finished | `regulator` | `reviews/wave_<N>.md`, blocker classes, ledger patch recommendations | Orchestrator applies the patch and opens the next wave |
| A protected statement changed, or an axiom appeared | `regulator`, then the owner it names | audit entry | never "fix" it by weakening the statement |
| An approved statement turns out to be unfaithful to the source | `f-reviewer` rejection → `formalizer` revision → `f-reviewer` approval → `lean.py guard approve-change` | `reviews/statement_<task>.md` + new snapshot | `f-generator` restarts on the new statement |
| A recurring formalization trap cost a wave | `memory-routing` skill → `Experience_*` card | long-term memory card | re-render `memory.md` |
| A reusable helper lemma or Mathlib gap is worth keeping | `knowledge` skill → `Lean_*` card | KB inbox entry | continue |

## The Master Development

`target/` is the default name only. The master development is often an existing
lake project elsewhere (a book formalization, a Mathlib fork). The Orchestrator
records its real path in `STATUS.md` and the ledger task's `target_file`, and
names the concrete file in every dispatch. The rules are location-independent:
Integrator-only writes, four gates, commit at wave close.

## Isolation

Each dispatch names exactly one scratchpad, `scratch/<role>/<task_id>/`, and the
agent writes only there. Concurrency is capped at 6 specialists; subagents never
spawn subagents. Full ownership table:
`prompts/references/workspace-and-ownership.md`.

## Parallel F-Generators

Independent ledger tasks (no dependency edge, disjoint declarations) can run
concurrently. Give each its own task id, its own scratchpad, and its own target
declaration. Do not run two F-Generators on the same declaration hoping one
succeeds — that produces two candidates and no way to choose between them beyond
the gates, which is what the ledger's dependency order exists to avoid.

When a target has genuinely distinct proof strategies worth trying in parallel,
make that explicit: separate ledger tasks, distinct stated strategies (e.g.
`by induction on n` vs. `via the Mathlib API for X`), and a note in each task of
which one it is.

## Prompt-Only Specialization

The specialists share a base model. Their separation comes from different input
files, different allowed write targets, different forbidden actions, different
output shapes, and different completion criteria. The point is not more votes —
it is preventing the Orchestrator from privately doing formalization, proof
search, statement review, and merging in one context.
