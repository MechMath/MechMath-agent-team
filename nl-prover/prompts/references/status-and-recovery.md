# STATUS and Recovery State

`STATUS.md` should be concise and restartable.

It is re-read at the start of **every** round, so it is the one file whose size is
paid for once per round for the rest of the run. Keep it to what routing needs
*now*. Two sections are split out because they only ever grow:

- `STATUS_history.md` — the append-only `## History` narrative. Not read for
  routing; `recovery/route_history.md` already carries the routing-relevant part.
- `STATUS_closed.md` — branch-queue rows that reached `rejected` or `done`. Rows
  keep their status and their evidence paths; they just stop being re-read.
  `blocked` rows stay in `STATUS.md` — waiting on a named condition is not
  finished. **Archiving is not closing, and a row archived by mistake must be
  findable in the archive by its id.** When in doubt, leave it in `STATUS.md`:
  re-opening a settled branch costs far more than re-reading a line.

Check the size with `uv run python cli_tools/gate.py speed <workspace>`.

```markdown
# Proof Status: <problem_id>

## Problem
<one-line summary>

## Target Contract
- Path: sketch/target_contract.md
- Status: missing | complete | needs definition/source/human review

## Phase
sketch | plan_check | prove | refine | summarize | complete

## Lemma Status
| Lemma | Dependencies | Status | Generator Attempts | Verifier Verdict | Review Packet |
|-------|--------------|--------|--------------------|------------------|---------------|

## Open Proof Obligations
| Obligation | Owner | Source | Status | Next Action |
|------------|-------|--------|--------|-------------|

## Active Branch Queue
| Rank | Branch | Owner | File target | Needed evidence | Status |
|------|--------|-------|-------------|-----------------|--------|
<active | queued | open | blocked rows only; rejected and done rows go to STATUS_closed.md>

## Archives
- History: STATUS_history.md
- Closed branches: STATUS_closed.md
```

`STATUS_history.md` and `STATUS_closed.md` use the same row shapes, appended
under a dated heading. They are written when `STATUS.md` is updated, not on a
separate pass, and they are read only when something specific is being looked up.

Every stuck route must preserve:

- atomic blocker;
- latest artifact paths;
- reusable work;
- unusable support;
- non-terminal reason;
- selected active owner;
- queued alternates.

Use `.agents/skills/proof-recovery/SKILL.md` and
`.agents/skills/proof-recovery/reference-route-recovery.md` for the detailed
packet.
