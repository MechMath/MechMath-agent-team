---
name: target-reading
description: "Use before decomposing, proving, or refuting a mathematical target whose logical shape, displayed conditions, named constructions, or standard definitions could be misread."
---

# Target Reading

Use this skill before the first decomposition and again after any review says
the proof changed the target, proved only a displayed side condition, or used a
named object under an unaudited interpretation. The purpose is to make the
original theorem's logical contract explicit before agents search for a proof
or counterexample.

## Who Uses It

- Orchestrator: create or require `sketch/target_contract.md` before plan
  verification, and route target-drift failures to the smallest owner.
- Sketcher: fill the target contract before writing the lemma DAG.
- Generator: read the target contract when proving a terminal lemma or proposing
  a counterexample/obstruction.
- Verifier: compare the submitted proof or obstruction against the target
  contract during statement-preservation and problem-reading audits.
- Auditor: resolve specialized notation, named constructions,
  boundary conventions, and accepted readings when the target contract cannot
  normalize them from local context.

## Workflow

1. Read `problem.md` without assuming that every displayed formula is itself
   the whole target.
2. Build `sketch/target_contract.md` from
   [reference-target-contract.md](reference-target-contract.md).
3. Classify the logical shape: implication, equivalence, characterization,
   classification, existence, uniqueness, construction, computation, or another
   explicit form.
4. Record the answer polarity and terminal evidence needed to settle it. For
   example, an existential question needs a witness and verification, a
   universal claim needs a proof for an arbitrary object or a counterexample
   to the universal statement, and a nonexistence claim needs a proof that no
   admissible object exists. If wording such as "possible" or "can" has more
   than one defensible reading, record the selected reading and why; if the
   reading cannot be fixed from context, route it as an open obligation.
5. For each displayed condition, formula, named object, or named construction,
   record its role: hypothesis, definition, equivalent condition, conclusion,
   auxiliary notation, or unresolved definition obligation.
6. If the theorem is an equivalence or characterization, assign proof ownership
   for each direction. A counterexample must name the direction it refutes and
   satisfy the hypotheses for that direction under the accepted definitions.
7. If a named or canonical construction is used, record the accepted
   construction rule or a source-definition obligation. Do not replace it with a
   convenient object unless an object bridge proves the replacement is the same
   object for the target.
8. Route unresolved target shape, definition, construction semantics, or answer
   polarity as an open obligation. Use Auditor for notation,
   construction, or convention blockers; Sketcher for DAG/target-shape repair;
   Regulator when the owner is unclear; and Human only when accepted context
   cannot determine the reading. Do not turn ambiguity into a proof, disproof,
   or final answer.

## Hard Stops

- Do not refute an isolated displayed condition when the target is a conditional
  theorem, equivalence, characterization, or definition involving that
  condition.
- Do not prove only one direction of an equivalence unless the target contract
  and final assembly record that only that direction was requested.
- Do not use one counterexample to answer an existential or "can there exist"
  target unless that object is the requested witness, and do not use one
  positive example to answer a universal target unless the target contract
  explicitly identifies that as the requested resolution.
- Do not use a counterexample built from a guessed definition, arbitrary
  replacement object, or unaudited construction semantics.
- Do not continue a proof branch after a target-drift warning until the target
  contract has been updated or the branch is routed to the responsible owner.
