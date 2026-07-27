---
name: source-theorem
description: "Use when a proof branch invokes a named theorem, folklore result, classification, major estimate, or theorem-shaped inequality that may carry the proof."
---

# Source Theorem Audit And Literature Tracing

Use this skill before a branch relies on a theorem-like premise that is not
already proved as a dependency. The purpose is premise selection discipline:
trace the literature, recover the exact statement, check that it is independent
of the target, and route missing parts as proof obligations.

## Audit Boundary

Searcher performs the **provenance** side of this skill and stops there:
what the result is, whose it is, where it came from, and whether it roughly
fits. Searcher is a divergent role and must not gatekeep.

**Correctness auditing belongs elsewhere** and Searcher never stands in for it:

| Question | Owner |
|----------|-------|
| Is this statement true / correctly specialized? Do its preconditions hold? Is it independent of the target? | fresh Verifier — its auto-FAIL #10 is the source-theorem trust audit (ADR 0019) |
| Is the named theorem admissible for this proof step? | `gate.py proof-attempt --status` (invariant 10) |
| Is the proof using it valid? | fresh Verifier (invariants 3, 12) |
| What does an ambiguous cited symbol / named family actually mean? | Auditor (definition/notation reading only — feeds the Verifier) |

Consequences: a complete specialized statement is desirable but **optional** —
record what you have, mark what is uncertain, and route the rest as a proof
obligation instead of dropping the candidate. Do not discard a plausible source
because you could not finish auditing it yourself.

## Who Uses It

- Searcher: primary owner for producing source theorem packages
  when the Orchestrator assigns a theorem obligation.
- Sketcher: before putting a named theorem or classification into the lemma DAG.
- Generator: before using a theorem-like premise as the main step of a lemma.
- Orchestrator: when a failed verification packet points to a missing,
  circular, or under-audited source theorem.
- Verifier: to judge whether the submitted theorem package is usable evidence.

## Entry Triggers

- A proof route, lemma statement, or decomposition uses a named theorem,
  folklore result, classification theorem, comparison theorem, major estimate,
  rigidity result, or theorem-shaped inequality as a load-bearing step.
- A Generator status file says a lemma needs an unavailable theorem,
  definition, or precondition package.
- A Verifier packet blocks merge because a named theorem is vague, circular,
  stronger than the target, or missing checked hypotheses.
- Two proof attempts fail at the same source-theorem invocation.
- A Sketcher route depends on a broad standard result but does not state the
  exact form used by the proof.

When in doubt, use this skill. It is cheaper to audit a theorem package before
generation than to discover after verification that the proof was carried by a
vague or circular theorem invocation.

## Workflow

1. Start with literature tracing using
   [reference-literature-tracing.md](reference-literature-tracing.md). Search in
   layers instead of treating source lookup as one web call:
   - local extracted references and paper notes;
   - existing query outputs;
   - relevant KB-Manager summaries or local knowledge;
   - Matlas theorem search;
   - arXiv or paper search;
   - at least one relevant citation layer from plausible papers.
2. Build or update paper cards for retained papers when a reference directory is
   assigned:
   - `references/papers/<paper_id>/note.md`;
   - `references/papers/<paper_id>/statements.jsonl`;
   - `references/papers/<paper_id>/citation_trail.md`.
3. Build a source theorem package using
   [reference-source-theorem-package.md](reference-source-theorem-package.md).
4. If the result is a theorem package rather than one atomic implication, split
   it into component bridge obligations before classification. Common
   components include:
   - exact theorem statement and scope;
   - application preconditions in the current problem;
   - comparison, invariance, normalization, quotient, or parameter bridge;
   - strict versus weak inequality or endpoint bridge;
   - equality, rigidity, uniqueness, or classification-case bridge;
   - final wording bridge from the theorem output to the requested conclusion.
   Each component needs a source, local lemma, dependency, or open status.
5. Run the equivalence smoke tests in that reference. Pay special attention to
   algebraic reformulation, specialization, limiting, dualizing, optimizing, or
   renaming transformations that turn the theorem into the current target.
6. Classify the theorem package:
   - `usable`: exact statement, source or derivation route, all preconditions,
     bridge, and independence check are recorded.
   - `needs-source`: the statement is plausible but no independent source or
     derivation route is recorded.
   - `needs-local-derivation`: the theorem is exactly the missing lemma, or its
     proof must be supplied inside the current DAG.
   - `needs-bridge-lemma`: the theorem is independently available, but a
     strictness, equality-case, normalization, endpoint, or final-wording bridge
     still needs its own proof obligation.
   - `resketch`: the theorem needs a new dependency edge, intermediate lemma, or
     final bridge.
   - `definition/human-review`: accepted terminology or conventions affect the
     theorem statement.
   - `obstruction-candidate`: only after a concrete incompatible precondition,
     contradiction, or counterexample has been written for fresh verification.
7. Record the package where the proof route can restart from it: `routes/`,
   research notes, decomposition, lemma statement, generator `status.md`, or the
   review packet.
8. If the package is not `usable`, do not cite the theorem as proof support.
   Route the next action to the smallest owner named by the classification.
   Use Searcher for missing theorem statements or precondition
   packages, Auditor for terminology or convention blockers,
   Sketcher for dependency/DAG changes, Generator for local derivations, and
   Regulator when the owner is mixed or unclear. Treat the missing source as
   restart state, not as a terminal result.

## Recovery Discipline

- Re-read the exact lemma and original problem statement. Confirm that the
  missing result is really needed for the current route and is not a disguised
  added hypothesis.
- Inventory every load-bearing source theorem in the branch. Separate theorem
  statement recovery from local precondition checking.
- Check local context first: existing decomposition notes, verified dependency
  proofs, relevant `memory.md` source findings or failed paths, extracted
  references, and KB-Manager summary. Use a deep KB-Manager read only when the
  summary shows a relevant concept.
- If research tools are unavailable or sparse, record that fact and continue
  with local derivation or alternate-route planning. Do not terminate merely
  because a tool could not run.
- If one query misses, vary the keyword family, inspect related work, or trace a
  plausible paper's references before declaring the source unavailable.
- Build a small route portfolio before declaring the branch stuck:

| Branch | Route type | Needed theorem package | Local obligations | Risk | Next owner |
|--------|------------|------------------------|-------------------|------|------------|
| A | theorem application | <label or NONE> | <preconditions/bridge> | low/medium/high | Searcher/Generator/Sketcher/Human |
| B | direct construction or reduction | <label or NONE> | <construction/cases> | low/medium/high | Explorer/Generator/Sketcher/Human |
| C | definition or convention audit | <label or NONE> | <accepted reading> | low/medium/high | Auditor/KB-Manager/Human |

Choose the lowest-risk branch whose obligations have named owners. If the
branch requires a new lemma, dependency edge, or final bridge, return to
Sketcher and then run fresh plan verification. If the route choice itself is
unclear, ask Regulator to classify the blocker before retrying.

## Hard Stops

- A theorem whose conclusion is the current target after a routine
  transformation is not an external premise; prove it, source it independently,
  or resketch around it.
- An internal audit, successful lint run, or agent confidence is not a
  mathematical source.
- A theorem stronger than the original target cannot be used as a shortcut
  unless the stronger theorem has its own independent source or derivation.
- Do not hide a strict bound, endpoint passage, equality case, rigidity
  direction, or normalization step inside the phrase that a theorem applies.
  Make it an explicit bridge obligation or local lemma.
- A change from max to sup, compactified to open parameter space, normalized to
  original object, or representative to whole family is a theorem-bridge
  obligation unless it is already proved in the accepted context.
- Missing source material is restart state, not a proof or disproof.
