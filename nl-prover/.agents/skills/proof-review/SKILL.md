---
name: proof-review
description: "Use before accepting any terminal non-proof result, boundary-case counterexample, presentation-dependent disproof, or missing-context obstruction, AND whenever a human (professor, advisor, referee) voices a mathematical opinion, objection, doubt, or claim about the current proof or route; writes a two-sided proof/refutation review that selects the next owner."
---

# Proof Review

Use this skill when a run is close to a user-facing result but the result is not
an already verified proof of the original statement. Its purpose is to keep
proof failure, missing context, boundary artifacts, and presentation choices from
being packaged as mathematical conclusions.

This is a workflow and packet shape, not a standalone custom agent. When the
next owner is unclear or the result may affect routing, dispatch Regulator with
this proof-review artifact as context. Regulator selects the next owner and
branch queue.

## When To Use

- A Generator, Sketcher, or Verifier proposes a counterexample, obstruction,
  impossible precondition, target defect, or "cannot prove from available
  setup" conclusion.
- CE-Hunter proposes a boundary failure or obstruction candidate.
- Regulator classifies a failed branch as possible `target-obstruction` or
  mixed proof/refutation state.
- A proposed disproof depends on a minimal, quotient, degenerate, endpoint, or
  otherwise exceptional case.
- The target uses a named or canonical construction, presentation, generating
  family, parameter range, or convention that could differ from a convenient
  replacement used in the argument.
- Reviews disagree about whether the run has found mathematics or only exposed
  missing definitions, missing source theorems, or an unfinished route.
- **A human voices a mathematical opinion on the proof.** Whenever the input
  reports that a person — "the professor said…", "my advisor thinks…", "a
  referee objects that…", "someone claims the lemma is false because…" — offers
  a judgement, doubt, objection, or counter-claim about the current statement,
  route, or a proof step, treat it as a proof-review trigger. Do not act on the
  human opinion directly and do not fold it silently into `proof.tex`: open a
  two-sided review that carries the opinion into the Refutation Route (if it
  doubts the result) or the Proof Route (if it proposes a fix), record it under
  provenance, and let a fresh Verifier / Regulator adjudicate. This is the
  §2.3.1 human-in-the-loop signal — it must be routed, not obeyed.

## Output

Write a short artifact in the problem workspace, normally
`review/proof_review.md` or a route-specific `routes/proof_review_*.md`. This
is a routing artifact, not a proof artifact. It may be written by the
Orchestrator as a structured workflow artifact when it only records already
available claims and routes; mathematical classification belongs to Regulator
or Verifier.

```markdown
# Proof Review

## Target Reading Check
- Exact target or direction:
- Accepted parameter range and boundary conventions:
- Accepted definitions, named constructions, and presentations:
- Unresolved reading obligations:

## Proof Route
- Best available proof route:
- Missing evidence, if any:
- Next owner if pursued:

## Refutation Route
- Proposed object, contradiction, or impossible precondition:
- Hypotheses satisfied under accepted reading:
- Conclusion failure under accepted reading:
- Boundary/presentation dependence:
- Next owner if pursued:

## Decision
- Selected status: PROOF_REVISION | SOURCE_OR_DEFINITION_RECOVERY | RESKETCH |
  OBSTRUCTION_VERIFICATION | HUMAN_CLARIFICATION | FINAL_PROOF_READY
- Owner:
- File target:
- Reason:
```

## Review Discipline

1. Read `sketch/target_contract.md`, `STATUS.md`, the latest proof attempt or
   final assembly, and the latest review packet.
2. Record the accepted reading before scoring either side: exact claim,
   direction, hypotheses, parameter range, boundary conventions, named objects,
   and canonical presentations.
3. Build both sides of the review:
   - Proof route: the most plausible route that could prove the statement as
     read, including missing definitions, theorem statements, bridge lemmas, or
     final assembly steps.
   - Refutation route: the concrete object, contradiction, or impossible
     precondition, plus the hypotheses it satisfies and the conclusion it
     falsifies.
4. Stress-test presentation choices. If the target specifies a canonical
   presentation, construction, or generating family, do not replace it by a
   minimal or more convenient presentation unless an accepted bridge proves the
   replacement preserves the target conclusion.
5. Stress-test boundary cases. A degenerate or endpoint case supports a
   terminal obstruction only when the target contract includes that case under
   the same definitions and the conclusion fails there under the accepted
   presentation.
6. Select exactly one next status and owner. If the refutation route is
   plausible but lacks a concrete object or contradiction, use `RESKETCH` or
   `PROOF_REVISION` with owner `CE-Hunter`. Choose
   `OBSTRUCTION_VERIFICATION` only if the refutation route already contains a
   concrete mathematical obstruction that can be sent to a fresh Verifier. If
   the artifact mixes proof-local, source, definition, DAG, and obstruction
   blockers and the next owner is not clear, use a restart status with owner
   `Regulator`.
7. Before using the selected status, run
   `uv run python cli_tools/gate.py proof-review <proof_review_file>`.
   A lint failure means the artifact is still routing state; fix the review or
   send the blocker to the selected owner before any terminal answer.
8. The completion gate inspects `review/proof_review.md` when it exists.
   Restart statuses are incompatible with completion, and
   `OBSTRUCTION_VERIFICATION` also requires an accepted obstruction packet
   supplied to the gate with `--packet`.

## Hard Stops

- Do not present missing definitions, missing source theorems, unavailable
  context, or exhausted attempts as a mathematical obstruction.
- Do not accept a counterexample that changes the target's object, presentation,
  generating data, or parameter domain without an accepted bridge.
- Do not use a boundary case as the whole terminal result when the accepted
  reading treats that case as a separate convention or unresolved definition
  obligation.
- Do not edit `proof.tex` from this skill. The Orchestrator may merge only after
  the selected branch later receives the required verification artifacts.
- Do not narrate the human opinion in `proof.tex`. Phrases like "the professor
  said…", "a referee objected…", or any record of who raised a doubt must never
  appear in the proof text. The opinion is a routing signal only; it lives in
  `review/proof_review.md` and provenance. The final `proof.tex` carries clean
  mathematics that reads as an ordinary proof, with no trace of the review
  exchange.
