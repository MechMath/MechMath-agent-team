---
name: proof-recovery
description: "Use when a proof route is stuck, a source theorem is unavailable, or a review packet reports an incomplete route that must be turned into restartable next work rather than a terminal answer."
---

# Proof Recovery

Use this skill when the current proof route has not produced a verified proof
and the surviving issue is missing knowledge, a missing bridge, a missing source
theorem, a definition ambiguity, or repeated local failure. The goal is to turn
an incomplete route into a ranked, restartable next action without treating the
agent's process failure as a mathematical result. A stuck route should become a
usable experience route: record what failed, what remains usable, and which
branch should be tried next, then continue the proof workflow through the
selected owner.

## Who Uses It

- Orchestrator: after a stuck Generator, exhausted attempts, failed final
  assembly, or a completion gate failure caused by unresolved obligations.
- Sketcher: when resuming from a blocked route and deciding whether to repair
  the DAG or replace the route.
- Generator: before writing `stuck` status for a lemma whose issue is not a
  verified counterexample to the lemma.
- Verifier: when a review packet identifies missing theorem support, missing
  definitions, or final-assembly gaps and must name the smallest next owner.

## Workflow

1. Read `memory.md`, `STATUS.md`, the latest review packet when present, and
   the current proof-writing status for the blocked lemma or assembly.
2. Extract one atomic blocker: the smallest missing construction, estimate,
   theorem statement, definition, dependency edge, or final bridge that prevents
   the route from closing.
3. Build a recovery packet using
   [reference-route-recovery.md](reference-route-recovery.md). The packet must
   record what has already been proved, what cannot be used yet, and why the
   issue is not a terminal mathematical result.
   It must also preserve the reusable lesson from the failed route: rejected
   terminal wording, failed theorem/source/definition assumptions, partial
   proof ingredients that can be reused, and the next route to try.
4. List at least three materially different next branches when possible:
   local derivation, audited theorem use, source or definition recovery, DAG
   repair, alternate invariant/construction, final-assembly bridge, or a
   concrete obstruction candidate.
5. If the blocker is non-local or the right owner is unclear, route it through
   the Regulator classification before retrying the same proof-writing agent.
6. If the selected branch would end the run without a proof, first use
   `.agents/skills/proof-review/SKILL.md` to compare the best proof route with the
   proposed refutation or missing-context route.
7. Rank the branches by statement-drift risk, number of open prerequisites, and
   dependency impact. Select exactly one active owner and file target, but keep
   the remaining materially different branches as queued alternates.
8. Update `STATUS.md` with the active branch queue, the rejected terminal
   language, and the owner. Do not edit `proof.tex` unless the selected branch
   later receives a passing review packet.
9. Continue through the selected owner immediately: return proof-only repairs to
   Generator, source-theorem blockers to Searcher or the
   source-theorem workflow, definition/target-reading blockers to Auditor or the target-reading workflow, strategy blockers to
   Explorer/Synthesizer, DAG or final assembly blockers to Sketcher plus fresh
   plan verification, and obstruction signals to CE-Hunter followed
   by Regulator using the proof-review workflow. Ask the human only when the
   selected branch is genuinely human clarification or human review.
10. If the active branch later fails, pop the next queued branch rather than
    stopping. A single recovery packet or Regulator decision is not proof of
    exhaustion.

## Status Classification

When deciding whether a run is terminal or restartable, choose exactly one
state and record it in `STATUS.md`, a route note, or a review handoff:

```md
## Proof Status Classification

- Run state: VERIFIED_PROOF | VERIFIED_OBSTRUCTION | RESTART_OBLIGATION | HUMAN_CLARIFICATION
- Original statement checked: YES/NO, path:
- Latest artifact reviewed: proof/plan/attempt/packet path:
- Accepted definitions/readings used:
- Open obligations:
- Smallest owner:
- Next route:
- Verifier packet required before terminal status: YES/NO
```

| State | Meaning | Required next action |
|-------|---------|----------------------|
| `VERIFIED_PROOF` | The exact original statement is proved, with all load-bearing obligations accepted. | Run the completion gate, then proof summarization. |
| `VERIFIED_OBSTRUCTION` | A fresh Verifier accepts a concrete counterexample, contradiction, or impossible precondition audit under accepted definitions. | Run proof-review workflow and the completion gate with the accepted obstruction packet. |
| `RESTART_OBLIGATION` | Some proof ingredient, source theorem, definition, object bridge, route, or final assembly step is missing or unverified. | Record the obligation in `STATUS.md` and route to the smallest owner. |
| `HUMAN_CLARIFICATION` | The original statement has no unique accepted reading after definition lookup and normalization attempts. | Ask for clarification or route through human review; do not present a mathematical result. |

## Object-Bridge Audit

Use this whenever a proof changes the object named in the problem into a related
object supplied by a construction or theorem:

```md
## Object Bridge

- Original object:
- Replacement object:
- Relation needed: equality | isomorphism | same invariant | compatible boundary | other:
- Proof location or owner:
- Preconditions for the relation:
- Verifier status: open | accepted | rejected
```

If this record is open, the proof has not yet established the original
statement. Route to the owner who can prove the bridge or revise the
decomposition.

## Restart Routes

| Blocker type | Route |
|--------------|-------|
| Missing local proof detail | Return the packet to the responsible proof writer. |
| Missing named theorem or preconditions | Route to Searcher or the source theorem skill. |
| Missing definition or accepted reading | Route to Auditor, local context, KB-Manager, or human clarification as available. |
| Object replacement without bridge | Add a bridge lemma or revise the statement/DAG. |
| Dependency edge or final bridge absent | Return to Sketcher and rerun plan verification. |
| Repeated route failure | Use Regulator, then Explorer/Synthesizer for a small branch portfolio before another attempt. |
| Concrete falsehood candidate | Route to CE-Hunter, then Regulator using proof-review workflow; require fresh Verifier only if obstruction-ready. |

## Hard Stops

- Do not write a final answer whose mathematical content is only that the
  source theorem, definition, construction, or route was not found.
- Do not treat a failed search, unavailable tool, exhausted proof-writing
  attempts, absent local definition, or circular route warning as terminal
  mathematics unless a fresh Verifier accepts positive proof or obstruction
  evidence.
- Do not keep retrying the same failed proof branch without adding a new source,
  lemma, definition reading, or concrete local derivation.
- Do not stop with `future Sketcher/Human after a new idea` while the recovery
  packet contains queued branches or untried specialist triggers.
- Do not mark an obstruction branch terminal unless it contains a specific
  object, contradiction, or impossible precondition audit and a fresh Verifier
  accepts it under the original hypotheses.
- Do not turn a theorem-use blocker into a stronger assumption on the original
  problem. Either prove the needed premise, source it independently, or resketch
  the route.
