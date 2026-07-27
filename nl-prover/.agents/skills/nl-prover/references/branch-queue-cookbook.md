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

Allowed statuses:

- `active`: currently dispatched or ready to dispatch.
- `queued`: available after the active branch fails or completes.
- `blocked`: cannot proceed until a named missing input appears.
- `rejected`: specialist or Verifier rejected the branch with evidence.
- `done`: branch produced an accepted artifact.
- `superseded`: another accepted branch made this one unnecessary.

## Queue Update Rules

- Every recovery packet, Regulator decision, and Synthesizer output should update
  the queue or explain why no alternative exists.
- When the active branch fails, mark it `blocked`, `rejected`, or
  `inconclusive`, then pop the next queued branch.
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
