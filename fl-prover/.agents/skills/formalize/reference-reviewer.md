# Formalization Reviewer Checklist

Use this checklist before accepting a formalized statement. The reviewer should
compare the source statement against the Lean declaration, not merely check that
the Lean code compiles.

For each declaration, identify:

- Source variables, hypotheses, conclusion, and subclaims.
- Lean variables, hypotheses, return type, and supporting definitions.
- Any difference between the source statement and Lean statement.

## 1. Anti-Laziness

Reject if the declaration uses `True`, `False`, tautologies, vacuous predicates,
or dummy definitions to stand in for missing mathematics.

## 2. Completeness

Reject if any source content is missing:

- hypotheses
- conclusions
- subpoints
- uniqueness clauses
- existence clauses
- exactness conditions
- local/global alternatives
- forward or backward implications

This is the most common failure mode: the draft states a convenient consequence
while dropping the structural content of the source theorem.

## 3. Generality

Reject if the statement was specialized without justification:

- arbitrary family downgraded to two objects
- finite family downgraded to binary operation
- arbitrary module downgraded to a ring or ideal case
- polymorphic type restricted to an unnecessary universe
- theorem over all objects restricted to a special class

## 4. Object Fidelity

Reject if a mathematical object has been replaced by a different object:

- ideal vs submodule
- quotient ring vs quotient module
- `A / I ^ n` vs `I ^ n / I ^ (n + 1)`
- localization at primes vs localization at maximals
- finite generation vs finite length
- equality of objects vs isomorphism or equivalence

## 5. Morphism Fidelity

Reject if a structured morphism was downgraded:

- ring homomorphism should be `A →+* B`
- ring isomorphism should be `A ≃+* B`
- module map should be `M →ₗ[A] N`
- algebra morphisms should use bundled Mathlib structures when available

Bare functions with preservation hypotheses are acceptable only when the source
or local API truly requires that shape.

## 6. Directionality

Reject if source logical direction is changed:

- "if and only if" must use `↔`
- "equivalent conditions" should use `TFAE` or an equivalent full conjunction
- one-to-one correspondence must include both directions
- uniqueness must not become existence

## 7. Finiteness and Generation

Reject if finite hypotheses or conclusions are missing or misencoded:

- finite family
- finitely generated module, ideal, or algebra
- finite basis
- finite length
- Noetherian hypotheses or conclusions

Check that `Finite`, `Fintype`, `Finset`, `Module.Finite`, finite generation,
and finite length are not being confused.

## 8. Typeclass Fidelity

Reject if typeclasses are too weak, too strong, or mathematically misplaced.

Check especially:

- `[CommRing A]` vs `[Ring A]`
- `[Nontrivial A]` when prime, maximal, field, or domain behavior requires it
- `IsDomain`, `IsLocalRing`, `IsNoetherianRing`, and algebra assumptions
- extra assumptions that turn a theorem into a weaker statement

## 9. Universe Polymorphism

Reject unnecessary universe restrictions. If the source quantifies over rings or
modules independently, avoid forcing all types into the same universe unless the
local API requires it.

## 10. Declaration Kind

Reject if the declaration kind does not match what the source does:

- constructive content (a map, an isomorphism, a specific object) stated as
  `theorem … : Nonempty (A ≃* B)` or `theorem … : ∃ f, …` instead of a `def`
  returning the bundled object
- data-plus-properties that should be a `structure`/`class` written as a loose
  `def` returning a conjunction or anonymous constructor
- `def` overuse where a `theorem` (a plain assertion) is what the source states

## 11. Definition Acid Test and Source Conditions

Reject if a Mathlib type was adopted by name without verifying its axioms match
the source definition condition by condition. Reject in particular if a
condition entailed by a source concept — continuity, topology, completeness,
measurability, compactness, or similar — is implied by the source but missing
from the Lean statement. The reviewer should confirm the formalizer actually
checked the definition, not just the name.

## 12. Readability and Bundling

Prefer Mathlib's bundled structures/typeclasses. If an object is pinned down by a
long list of inline hypotheses that an available Mathlib bundle already provides,
require reuse of that bundle. If no bundle exists but the same pinning is
repeated across declarations, recommend packaging it once into a local
`structure`/`class`. Treat pure verbosity with no available bundle as a
recommendation, not a hard reject.

## 13. Compilation Gate

Run Lean only after semantic review is acceptable. Compilation errors should be
fixed without weakening or specializing the source statement. The final accepted
state may contain intentional `sorry` warnings but no Lean errors.

## Verdict Format

For substantial reviews, report:

```text
[Auditing: declaration_name]
Anti-Laziness: Pass/Fail - reason
Completeness: Pass/Fail - reason
Generality: Pass/Fail - reason
Object Fidelity: Pass/Fail - reason
Morphism Fidelity: Pass/Fail - reason
Directionality: Pass/Fail - reason
Finiteness: Pass/Fail - reason
Typeclasses: Pass/Fail - reason
Universe: Pass/Fail - reason
Declaration Kind: Pass/Fail - reason
Definition Acid Test: Pass/Fail - reason
Readability/Bundling: Pass/Fail - reason

Verdict: APPROVE or REJECT
Required changes: ...
```
