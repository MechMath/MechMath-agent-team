# Route Recovery Packet

Use this packet when a route stalls before a verified proof or verified
counterexample. It is a restart artifact, not a proof artifact.

## Minimal Packet

| Field | Required content |
|-------|------------------|
| Blocked target | Lemma id or final assembly step, with exact statement |
| Current route | Short description of the attempted proof route |
| Atomic blocker | Smallest missing construction, estimate, theorem, definition, dependency, or bridge |
| Already established | Accepted dependencies or verified facts that remain usable |
| Unusable support | Claims, theorems, conventions, or shortcuts that cannot currently carry the proof |
| Reusable lesson | What the failed route taught future attempts not to repeat |
| Non-terminal reason | Why the blocker is a proof-workflow obligation rather than a counterexample or obstruction |
| Branch portfolio | Ranked alternatives with owner, needed evidence, statement-drift risk, and queue status |
| Active branch queue | Current active branch plus queued alternates |
| Selected next action | Exactly one active owner and file target |

## Branch Portfolio

Include distinct branches rather than paraphrases of the same attempt. Use as
many of these as apply, and add domain-specific branches when they are genuinely
different.

| Branch | Owner | Needed evidence | Risk | Decision |
|--------|-------|-----------------|------|----------|
| Local derivation | Generator | Missing calculation, construction, or estimate to prove directly | low/medium/high | try/reject/defer |
| Audited theorem use | Searcher, then Generator or Sketcher | Exact theorem statement, preconditions, independence, and bridge | low/medium/high | try/reject/defer |
| Source or definition recovery | Auditor, KB-Manager, Sketcher, or Human | Accepted definition, convention, source statement, or terminology reading | low/medium/high | try/reject/defer |
| DAG repair | Sketcher | New lemma, dependency edge, or revised terminal assembly | low/medium/high | try/reject/defer |
| Alternate route | Explorer, Synthesizer, Sketcher, or Generator | Different invariant, construction, reduction, or case split | low/medium/high | try/reject/defer |
| Final bridge | Sketcher or Generator | Verified terminal lemmas plus a precise implication to the target | low/medium/high | try/reject/defer |
| Obstruction candidate | CE-Hunter, then Regulator using proof-review workflow, then Verifier if obstruction-ready | Object satisfying hypotheses and conclusion failure, or impossible precondition audit | high unless explicit | try/reject/defer |
| Failure classification | Regulator | Ambiguous owner, repeated failure, or mixed blocker class | low/medium/high | try/reject/defer |

## Record Format

```markdown
# Route Recovery Packet: <blocked target>

## Blocked Target
<exact lemma or final assembly statement>

## Current Route
<what was attempted, with paths to the latest proof/status/review files>

## Atomic Blocker
<one smallest missing item and why it blocks the route>

## Already Established
- <accepted dependency or verified fact>

## Unusable Support
- <claim/theorem/convention that cannot currently be used as proof support>

## Reusable Lesson
<failed assumption, missing bridge, source-theorem gap, or convention issue that future routes must account for>

## Non-Terminal Reason
<why this is not a counterexample, contradiction, or impossible precondition audit>

## Branch Portfolio
| Rank | Branch | Owner | Needed evidence | Statement-drift risk | Decision |
|------|--------|-------|-----------------|----------------------|----------|
| 1 | <branch> | <owner> | <evidence> | low/medium/high | try |
| 2 | <branch> | <owner> | <evidence> | low/medium/high | defer |
| 3 | <branch> | <owner> | <evidence> | low/medium/high | defer |

## Active Branch Queue
| Rank | Branch | Owner | File target | Needed evidence | Status |
|------|--------|-------|-------------|-----------------|--------|
| 1 | <active branch> | <agent> | <path> | <evidence> | active |
| 2 | <queued branch> | <agent> | <path> | <evidence> | queued |

## Selected Next Action
- Owner:
- File target:
- Action:
- Completion check:
```

## Selection Rules

- Prefer a branch that preserves the exact original statement and has the fewest
  unproved prerequisites.
- Prefer resketching over repeated local proof revision when the blocker is a
  missing dependency edge, missing terminal bridge, or theorem equivalent to the
  target.
- Prefer Searcher for missing theorem packages and Auditor for unclear terminology before using obstruction language.
- Prefer Regulator classification over repeating a failed branch when the
  packet mixes proof-local, source, definition, DAG, and route-strategy
  blockers.
- Select an obstruction branch only when the packet already contains the
  proposed object or contradiction to send through Regulator with proof-review
  context and, if obstruction-ready, a fresh Verifier.
- Do not mark Human or `future Sketcher after new idea` as the selected next
  action while materially different queued branches remain.
