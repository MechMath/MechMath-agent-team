# STATUS and Recovery State

`STATUS.md` should be concise and restartable.

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

## History
- [timestamp] <event>
```

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
