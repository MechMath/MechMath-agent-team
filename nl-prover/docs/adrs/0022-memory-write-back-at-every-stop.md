# ADR 0022 — Memory Write-Back at Every Stop

- **Status**: Accepted — implemented, 2026-07-26
- **Extends**: ADR 0016 §3.6 (candidate cards), ADR 0021 (mandatory progress
  notes). Neither is superseded; this ADR closes the enforcement gap in both.

## Context

Observed on the real Ramanujan Challenge runs (`2_2`, `2_5`, `2_7`). The
three-tier memory system of ADR 0016 works *as tooling* — `memory.py
aggregate-candidates` correctly dedups candidate cards — but across every one of
those runs the workspace-external tiers stayed empty:

- `2_5` produced two well-formed negative-constraint cards on 2026-07-23 (a
  normalization-repair boundary and a differential-factor exclusion boundary).
  Three days later they were still sitting in `memory/candidates/`. No
  `candidates_aggregated.jsonl`, nothing in `DATA_DIR/inbox`.
- `2_2` reached `COMPLETE` with a verified proof and passed the completion gate,
  having recorded a non-empty `failed_paths` channel and *zero* candidate cards.
- No workspace had a `memory/.longterm_read.json` trace, so the resident
  `memory.md` was likely never read either.

Three causes, all structural rather than model misbehaviour:

**1. The only enforcement is on the verified-proof path.** `validate_candidate_
aggregation` is a real hard check, but it lives in `gate complete`, which runs
only when a run completes with a proof. `2_5` stopped for an exhausted branch
queue — the most common outcome of a hard problem, and precisely the case with
the most dead-end knowledge worth keeping — so no gate ever ran. This is the
same shape of defect ADR 0021 fixed for the reader-facing document: mandatory at
completion, absent at every other stop.

**2. Nothing in the routing loop names the step.** `aggregate-candidates`
appeared only in a tool-index table and in ADR 0016 itself. No prompt, skill, or
cookbook step told the Orchestrator to run it, so it ran only when the
completion gate happened to complain.

**3. The production-side check was advisory.** `validate_candidate_production`
emitted a warning when a run recorded failures but captured no lesson — which is
exactly what `2_2` did, and a warning does not stop anything.

## Decision

### A. A stop gate, applying to all four stop conditions

New `gate stop <workspace> [--verified-proof]` (`cli_tools/_gate/stop.py`), run
before **every** stop, not only a verified proof. Checks, all errors:

| Check | Rationale |
|-------|-----------|
| local index exists and is fresh | a run that sedimented nothing hands on nothing |
| `memory/.longterm_read.json` present | the resident negative-constraint list was actually consulted |
| recorded failures ⇒ a captured lesson | the `2_2` defect |
| candidates aggregated and promoted into the long-term tier | the `2_5` defect |
| stop export present | ADR 0021 made this mandatory; this makes it mechanical |

The mandated order before stopping is `memory.py refresh` → `memory.py
aggregate-candidates` → `gate.py stop`.

### B. Escalation is scoped to the stop gate

`validate_candidate_production` and `validate_longterm_read` gain an `escalate`
flag. The stop gate sets it; `gate complete` keeps its existing warning
classification so runs predating this ADR are not retro-blocked. One rule, one
enforcement point.

The escape hatch stays cheap and honest: a failure with no transferable lesson is
recorded as `{"no_constraint": "<why>"}`, which satisfies the check. The bar is
*capture a lesson or say why there is none*, not *invent a lesson*.

### C. Aggregation is not owed when there is nothing to promote

`validate_candidate_aggregation` previously demanded aggregation whenever any
record existed, including a workspace whose records were all `no_constraint`
markers — a required step that would produce an empty file and promote nothing.
It now filters to real cards first.

### D. The routing loop names the step

Added to `stop-conditions.md` (SSOT, alongside the ADR 0021 export rule), and
pointed at from `orchestrator-cookbook.md`, `prompts/orchestration.md`,
`memory-routing/SKILL.md`, `AGENTS.md`, and `CLAUDE.md`.

### E. The long-term tier is local and self-promoting

Originally this ADR stopped at the KB inbox and recorded the rest as a known gap:
`render-longterm` built `memory.md` from `DATA_DIR/wiki/experience/*.md`, that
directory did not exist, and ADR 0019 left `inbox → check → wiki` human-gated —
so `memory.md` could never fill no matter how well the harness behaved.

Resolved by moving the tier into the repository. Card bodies now live in
`memory/experience/*.md` and `aggregate-candidates` writes them and re-renders
`memory.md` in the same call: **written automatically, loaded every cycle**, with
no inbox hop and no human promotion step.

ADR 0016 §3.3's argument for keeping the bodies in the KB was statement drift —
the fear that a card copying a theorem would diverge from the KB's copy. That
argument does not survive §3.4 of the same ADR, which forbids an experience card
from holding anything but *pointers* (`refs: [[Concept_X]]`). There is nothing in
one that can drift. Routing this tier through the KB bought only a gate that
never ran.

Promotion dedups against the cards already present, so re-running a workspace
does not stack duplicates, and rejects a card with no `trigger` — unrecallable,
it would grow `memory.md` without ever firing. The KB keeps the declarative
families (`Concept_`, `Source_`, ...) that genuinely need one content authority;
`memory.py inbox-write` and Searcher's `Source_` deposits are unchanged.

## Consequences

- A stop now pays into the next run. Re-running the recovered chain on `2_5`
  promoted both stranded cards into `memory/experience/` and rendered them into
  `memory.md`, where the next cycle's hard-precondition read picks them up.
- Runs that stop for branch-budget exhaustion — the knowledge-richest failures —
  are covered for the first time.
- A run can no longer complete having recorded only dead ends and learned
  nothing; it must either capture the lesson or state that there is none.
- Cost: one extra mechanical command at each stop, and a stop can now fail for a
  memory reason. Both are intended — the gate reports what to fix.
- `memory.md` now grows on its own, so its 100-line cap becomes a live concern.
  `render-longterm` reports `over_100_line_cap`; compaction (merging
  near-duplicate constraints in `memory/experience/`) stays the Orchestrator's
  judgement call, not a script's.
