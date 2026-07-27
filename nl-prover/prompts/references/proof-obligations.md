# Proof Obligations

## Load-Bearing Obligation Ledger

Each decomposition, proof attempt, and review packet must maintain a ledger of
steps that carry the main argument.

```markdown
## Load-Bearing Obligation Ledger
| Obligation | Type | Where supplied or assigned | Preconditions checked | Status |
|------------|------|----------------------------|-----------------------|--------|
| <name> | construction/estimate/theorem/cases/dependency/final bridge | <path/step/lemma> | YES/NO/N/A | resolved/assigned/open/blocker |
```

In plan verification, `PASS` may mark obligations as `assigned` only when the
responsible lemma or audited theorem-use obligation is named. In lemma
verification, `PASS` requires every lemma-local load-bearing obligation used by
the proof to be `resolved`.

## Target Contract

Before first decomposition, require `sketch/target_contract.md`. Sketcher
writes it using `.agents/skills/target-reading/SKILL.md`.

## Finite Case and Computation Audit

Use whenever a proof relies on exhaustive cases, finite classification,
symmetry reduction, enumeration, matrix/polynomial/algebraic computation, or
script output as a load-bearing step.

```markdown
## Finite Case and Computation Audit
- Applies: NO | YES, <ledger obligation names>
- Finite universe:
- Exhaustiveness argument:
- Symmetry or quotient reductions:
- Evidence checked:
- Boundary and degenerate cases:
- Conclusion mapping:
- Unresolved finite-check blockers:
```

## Source-Theorem Routing

When a route depends on a named theorem, folklore result, classification
theorem, major estimate, rigidity result, or theorem-shaped inequality, prefer
early source-theorem auditing over waiting for failed proof attempts.

If a Verifier packet marks source-theorem warrant as `FAIL`, or a Generator
status identifies a missing named theorem/precondition, route through
`.agents/skills/source-theorem/SKILL.md` before proof revision.

## Problem Reading and Normalization

Before accepting target-defect, gap, counterexample, or obstruction routes,
separate presentation repair from mathematical content.

```markdown
## Problem Reading and Normalization
- Normalized reading used: NONE | <exact symbol/phrase and accepted correction>
- Source of reading: problem context | dependency | research context | human clarification | N/A
- Material ambiguity remains: NO | YES, <definition/human-review obligation>
- Boundary conventions audited: N/A | <conventions checked and selected reading>
```
