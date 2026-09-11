# Branch Queue Cookbook

The active branch queue prevents early stop after one failed route. It is
orchestration state, not proof evidence.

## Minimal Queue

```markdown
## Active Branch Queue
| Rank | Branch | Owner | File target | Needed evidence | Status |
|------|--------|-------|-------------|-----------------|--------|
| 1 | <branch> | <agent> | <path> | <evidence> | active |
| 2 | <branch> | <agent> | <path> | <evidence> | queued |
```

Allowed statuses. **These six are the whole vocabulary** — a word that is not on
this list does not change a branch's state, whatever an artifact calls it:

| Status | Meaning | Who may set it |
|---|---|---|
| `active` | currently dispatched or ready to dispatch | Orchestrator |
| `queued` | on the main line, waiting its turn | Orchestrator |
| `open` | still viable, but not on the main line | anyone |
| `blocked` | waiting on a **named** external condition | anyone, and the condition must be written down |
| `rejected` | **exact counterexample, or certification-mode Verifier FAIL** | certification mode only |
| `done` | produced an accepted artifact | certification mode only |

`rejected` is a hard wall with no way back, so it is deliberately hard to reach.
An attempt that simply did not work is **not** rejected: not budget exhaustion,
not an unmet precondition, not a missing ingredient, not an inconclusive search,
not a failed literature lookup. All of those are `open`.

**Say how far a rejection reaches, in the status cell.** A counterexample
certifies that a statement is false; it does not delimit *how* it is false, and
a bare `rejected` closes the route at whatever width the next reader assumes.
Write `rejected: exact <thing> only`, and put what survives in the
`recovery/route_history.md` entry as `Non-goals: <the neighbouring routes> remain
open`. Runs already do this; the qualifier was simply going nowhere, because the
gate read the first word of the cell and discarded the rest. It now records the
qualifier as data and warns when there is none.

**The default landing spot for a failed attempt is `open`.** `blocked` requires
naming what is being waited for; without a named condition it is `open`, not
`blocked`. This is what stops `blocked` becoming a second name for `rejected`.

`open` and `queued` are kept apart on purpose. "Waiting its turn on the main
line" and "still worth doing, but nothing is scheduling it" are different inputs
to whoever ranks next, and merging them loses that.

## Queue Update Rules

- Every recovery packet, Regulator decision, and Synthesizer output should update
  the queue or explain why no alternative exists.
- **`active` is not a singleton.** Any number of rows may be `active` at once as
  long as their file targets do not overlap; nothing in this vocabulary or in
  `gate.py discovery` limits it to one. The singular phrasing below is about the
  branch that just failed, not a claim that only one branch runs at a time.
- When an active branch fails, set it to `open` and pop the next queued branch.
  Use `blocked` only with a named condition, and `rejected` only with an exact
  counterexample or a certification-mode Verifier FAIL.
- An `open` branch may be re-proposed at any time and competes on equal footing
  with new candidates. Being in the history is not a mark against it.
- Do not write `future Sketcher/Human after a new idea` while queued branches
  remain.
- Do not ask Human merely because the current proof route failed.
- A branch is materially different only if it changes proof strategy, source
  theorem package, definition reading, construction, invariant, DAG bridge,
  computation evidence, or obstruction hypothesis.

## Restart Packet Requirements

A stalled branch must record:

- exact blocked target;
- current route and latest artifact paths;
- one atomic blocker;
- reusable work;
- unusable support;
- non-terminal reason;
- active branch queue;
- selected next owner and file target.

## Exhaustion Standard

Branch-budget exhaustion requires all of the following:

- the active branch was attempted or explicitly blocked with evidence;
- materially different queued alternatives were attempted or explicitly
  blocked;
- construction/proof route, source-theorem route, and obstruction-risk route
  were considered when relevant;
- the latest status names the evidence files for each stopped branch;
- no remaining specialist trigger applies without missing human input.

If these are not true, continue orchestration.
