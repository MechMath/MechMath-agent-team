---
name: human-review
description: "Use when repairing NL-Prover proof text marked with [human-review]...[/human-review] using human feedback; route repair to the responsible proof-writing agent and verify before adoption."
---

# Human-Guided Proof Review and Repair

Use this command when the human has marked proof text with
`[human-review]...[/human-review]` and wants the system to repair that proof
using human feedback.

This is a targeted repair command, not a fixed proof pipeline restart.

## Arguments

The user request may include optional human feedback.

Examples:

```text
Run human review: This step assumes compactness, but compactness is not available.
Run human review: The marked argument proves only injectivity, not surjectivity.
```

The human may also put feedback directly in the file after the marked proof
block:

```text
[human-review]
<proof fragment needing repair>
[/human-review]

[review-content]
This uses compactness, which is not one of the hypotheses. Replace the argument
without adding assumptions.
[/review-content]
```

If both the user request and `[review-content]...[/review-content]` are present,
use both. Treat explicit human feedback as the highest-priority repair
instruction.

## Marker Semantics

The proof fragment to repair is always marked by:

```text
[human-review]
...
[/human-review]
```

Optional feedback may be marked by:

```text
[review-content]
...
[/review-content]
```

The human does not need to provide IDs. If multiple `[human-review]` blocks are
present, assign stable local IDs in file order:

- `human-review-1`
- `human-review-2`
- `human-review-3`

If feedback clearly refers to one block, repair that block. If several blocks
are marked and the target is ambiguous, summarize the numbered blocks and ask
the human which one to repair before editing.

## Orchestrator Responsibilities

You are the Orchestrator. Do not directly validate the mathematics yourself.

Your job:

1. Locate all `[human-review]...[/human-review]` blocks in the current problem
   workspace.
2. Locate any `[review-content]...[/review-content]` blocks and combine them
   with `$ARGUMENTS`.
3. Assign local IDs to marked proof blocks in file order.
4. Identify the mathematical task implied by the marked block and feedback. Do
   not route by file path alone: humans will usually mark the authoritative
   `proof.tex`, but the right repair agent depends on what needs to be fixed.
5. Read the relevant context:
   - `problem.md`,
   - the surrounding `proof.tex` theorem/lemma/proof environment,
   - the owning lemma statement if applicable,
   - dependency statements and preconditions,
   - prior generator proofs,
   - prior verifier reports,
   - the human feedback.
6. Route repair by task type:
   - use the persistent **Generator** for ordinary proof-correctness repair:
     local gaps, wrong implications, missing cases, invalid theorem use,
     missing precondition checks, added hypotheses, or unclear proof steps.
     This is the default for marked proof text in `proof.tex`, even though the
     human edited the final document rather than the generator workspace.
   - return to **Sketcher** when the feedback shows the lemma statement,
     dependency DAG, or final assembly path is insufficient: missing bridge
     lemmas, wrong target statement, impossible lemma, or a repair that would
     require adding hypotheses.
   - use **Refiner** only for optional global simplification or structural
     cleanup after a complete accepted proof exists, or for repair of an
     existing refinement candidate under `refinement/`. Do not use Refiner
     merely because the marked block is in the final `proof.tex`.
   - handle purely mechanical LaTeX, formatting, label, citation, or merge
     issues as **Orchestrator** work, followed by compilation or verification
     only if the mathematical content changed.
7. Require a targeted revision that addresses the human feedback without adding
   or strengthening hypotheses.
8. Spawn a fresh **Verifier** for one full review of the revised artifact.
9. Adopt the repair only if the fresh Verifier packet returns `PASS`, uses the
   correct accepting next action, and passes review-packet lint.

## Dynamic Routing

Initial routing is provisional. The Orchestrator should revise it whenever the
context shows a different agent is responsible.

Examples:

- If a Generator repair discovers that the lemma statement is false or missing a
  necessary hypothesis, stop the Generator repair and reactivate Sketcher plus
  plan logic verification.
- If a marked block asks for a shorter or more readable global route but the
  current proof is not complete and accepted, do not use Refiner yet; route
  any correctness work to Generator or Sketcher first.
- If a Refiner candidate exposes a local lemma gap, route that gap back to
  the responsible Generator instead of patching around it globally.
- If several marked blocks require different kinds of work, split them and route
  each block independently.
- If the feedback is ambiguous, inspect the surrounding theorem/proof structure,
  labels, dependencies, and verifier reports before asking the human. Ask only
  when multiple plausible repairs would change the mathematical target in
  incompatible ways.

## Repair Rules

- Prefer the smallest proof change that fully addresses the human feedback.
- The repair may edit surrounding context if the marked block cannot be fixed in
  isolation.
- Correctness repair is not proof refinement. Prefer Generator for mathematical
  repair unless the task is explicitly global simplification/refinement or a
  repair to an existing refinement candidate.
- Do not add hypotheses, weaken conclusions, or change theorem statements to make
  the repair pass.
- If the feedback reveals a missing hypothesis, missing bridge lemma, or invalid
  decomposition, stop local repair and escalate to Sketcher plus plan logic
  verification.
- Preserve the original proof version as fallback until the repaired version
  passes fresh verification.
- Remove or resolve `[human-review]` and `[review-content]` markers only after
  the repair is accepted.

## Generator Repair Prompt

When routing to a Generator, include:

```text
You are repairing a proof in response to human review.

Marked block id: <human-review-N>
Marked block:
<exact marked text>

Human feedback:
<combined user-request feedback and [review-content] text>

Repair requirements:
- Address the human feedback directly.
- Make the smallest sufficient change.
- Do not add or strengthen hypotheses.
- Re-check all dependency and theorem preconditions touched by the repair.
- Write a new proof_v<N+1>.md and response_to_verifier.md explaining the repair.
- Do not spawn Verifier; Orchestrator will do that.
```

## Refiner Repair Prompt

When routing to Refiner, include:

```text
You are repairing a global proof in response to human review.

Marked block id: <human-review-N>
Marked block:
<exact marked text>

Human feedback:
<combined user-request feedback and [review-content] text>

Repair requirements:
- Address the human feedback directly.
- Prefer a local repair, but revise surrounding proof structure if needed.
- Do not add or strengthen hypotheses.
- If the DAG or final assembly path changes, document the change explicitly.
- Write the repaired candidate under refinement/.
- Do not spawn Verifier; Orchestrator will do that.
```

## Verifier Prompts

After a repair candidate is produced, spawn a fresh Verifier and include:

```text
This is a human-review repair verification.

Marked block id: <human-review-N>
Original marked block:
<exact marked text>

Human feedback:
<combined user-request feedback and [review-content] text>

Check the revised proof normally, and additionally verify:
- the human feedback was actually addressed,
- no hypotheses were added or strengthened,
- no theorem/dependency preconditions were skipped,
- the repair did not break surrounding proof context.
```

## Final Response

After handling the command, report:

1. which marked block ID was handled,
2. which artifact was repaired,
3. which agent performed the repair,
4. the fresh Verifier verdict and review-packet lint result,
5. whether the repair was adopted or the original proof was kept.
