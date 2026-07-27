# Workspace and Ownership

Each problem lives in `DATA_DIR/workspace/<problem_id>/`.

```text
problem.md                      the target as given (source statement + reference)
STATUS.md                       current state, active wave, next owner
.claude/state/                  control plane (ledger, summaries, statements, reports)
target/                         the master Lean development — the only place proofs land
scratch/<role>/<task_id>/       one isolated scratchpad per dispatched agent
blueprint/plan_<N>.md           dependency-ordered helper-lemma plans
reviews/statement_<task>.md     statement-fidelity verdicts
reviews/wave_<N>.md             end-of-wave audits
queries/<query_id>/             search / KB query workflow
references/                     source PDFs and their extracted indexes
memory/                         local memory tier + experience cards
logs/                           agent activity logs
```

## The Master Development (`target/`)

`target/` is the *default* name, not a fixed requirement. The master development
is often an existing lake project that lives somewhere else entirely — a book
formalization repo, a Mathlib fork, a shared project directory. Whatever it is:

- the Orchestrator records its actual path once, in `STATUS.md` and in the ledger
  task's `target_file`, and every dispatch names the concrete file path;
- "`target/`" in this repo's documents means "wherever that path points";
- the rules do not change with the location: only the Integrator writes there,
  the four gates run against it, and it is what gets committed at wave close.

If the project is outside `DATA_DIR/workspace/<problem_id>/`, say so explicitly in
the dispatch message — an agent must never infer write permission outside its
scratchpad from a path it merely saw.

## STATUS.md

Keep it short and restartable — someone who was not in the run should be able to
pick it up from this file plus the ledger:

```markdown
# Status: <problem_id>

## Target
<one-line statement of what is being proved, and the source reference it came from>

## Master development
<path to the lake project / file the Integrator writes>

## Wave
<N> — <what this wave is trying>

## Declarations
| Declaration | Statement approved | Snapshot | Proof | Gates | Owner |
|-------------|--------------------|----------|-------|-------|-------|

## Open obligations
| Obligation | Owner | Why it is open | Next action |
|------------|-------|----------------|-------------|

## Blocked / queued
| Item | Blocker class | Next owner |
|------|---------------|------------|

## History
- [timestamp] <event>
```

A stuck route must still record: the atomic blocker, the latest artifact paths,
what is reusable, what is not, why it is not terminal, and who is next.

## Scratchpads

Every dispatched specialist gets exactly one directory,
`scratch/<role>/<task_id>/`, and writes **only** there. The Orchestrator names it
in the dispatch message; an agent that was not given one asks rather than
guesses.

- Speculative proof search — half-finished tactics, throwaway `example`s,
  alternative attempts — stays inside the scratchpad. It never touches `target/`.
- Scratchpads are readable by anyone. An agent may read another's scratchpad for
  context, but reading is not adoption: nothing in a scratchpad is established
  until it compiles and is merged.
- A Lean file under a scratchpad is a *candidate*. It becomes real only when the
  Integrator merges it into `target/` after `lean.py check`, `scan`, and `axioms`
  pass on it.
- Scratchpads are not cleaned up mid-run: a failed attempt is evidence for the
  next wave and for the Regulator's audit.

Isolation here is a routing discipline plus the gates below, not an OS sandbox.
What protects the baseline is that only the Integrator writes
`target/`, protected statements are snapshotted, and each wave is committed.

## Snapshots

`scripts/runner.py` commits `target/` at the end of every round
(`commit_round`), so each wave is a restorable point and a bad merge can be
diffed rather than reconstructed. Interactive runs keep the same discipline:
commit `target/` when a wave closes.

## Ownership

| File or directory | Owner |
|-------------------|-------|
| `problem.md` | Human, except explicit mechanical copy/format requests |
| `STATUS.md` | Orchestrator |
| `.claude/state/proof_tasks.json` | Orchestrator only (`control.py task --actor orchestrator`) |
| `.claude/state/summaries/wave<N>.md` | `control.py wave` mechanical output, then the Regulator's notes |
| `.claude/state/statements/*` | `lean.py guard` mechanical output |
| `.claude/state/reports/*` | the specialist that filed the report |
| `target/**` | Integrator only |
| `scratch/formalizer/<task>/*` | Formalizer |
| `scratch/f-generator/<task>/*` | F-Generator (one task each) |
| `scratch/golfer/<task>/*` | Golfer |
| `scratch/integrator/<task>/*` | Integrator |
| `blueprint/plan_<N>.md` | Blueprinter |
| `reviews/statement_<task>.md` | F-Reviewer |
| `reviews/wave_<N>.md` | Regulator |
| `queries/index.md`, `queries/<query_id>/request.md`, `queries/<query_id>/status.md` | Orchestrator |
| `queries/<query_id>/index.json`, `index.md` | `search.py index` mechanical output |
| `references/index.json`, `index.md`, `.extracted/*` | `workspace.py references` mechanical output |
| `memory/*.jsonl`, `memory/index.json`, `memory/index.md` | `memory.py` local-tier mechanical output |
| `memory/experience/*.md`, `memory/candidates/*.jsonl` | `memory.py aggregate-candidates` mechanical output |
| `logs/*` | the agent that produced the activity |

Agents may read context broadly but write only owned files. The Orchestrator
maintains `STATUS.md`, the ledger, wave summaries, and query routing, and runs
the mechanical gates. It does not write Lean statements or proof text: any
non-mechanical change to Lean content has a specialist owner.

## Forbidden

- No agent other than the Integrator writes under `target/`.
- No agent edits a protected statement to make something compile. If the
  statement is wrong, that is an F-Reviewer finding, not a proof step. The only
  legal route to change a snapshotted statement is:

  1. F-Reviewer files a rejection in `reviews/statement_<task>.md` saying what is
     unfaithful to the source;
  2. Formalizer revises the declaration in its own scratchpad;
  3. F-Reviewer approves the revision (`VERDICT: APPROVE`);
  4. the Orchestrator re-snapshots with
     `lean.py guard approve-change --workspace WS --task T --review <path>`.

  No step may be skipped, and no other role may start it.
- No agent writes another agent's scratchpad, or the ledger.
- No agent adds an `axiom` to close a goal. An unprovable step is a proof
  obligation with an owner, recorded in the ledger.
