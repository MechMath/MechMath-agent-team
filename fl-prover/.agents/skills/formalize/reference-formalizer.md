# Formalizer Reference

The formalizer's job is statement formalization, not proof construction. A good
output gives future F-Generator agents the exact theorem they should prove.

## Core Rules

- Preserve the source statement's mathematical strength. Do not formalize only
  an easy consequence.
- Keep proofs as `:= by sorry`. Do not spend time proving the result.
- If the source has several subclaims, formalize all of them. Split them into
  separate declarations when that is clearer or more usable.
- If the source has an ambiguity, choose the interpretation best supported by
  the surrounding context and report the ambiguity.
- If a statement cannot be faithfully formalized without additional
  infrastructure, add real supporting definitions or structures. Do not use
  dummy predicates or tautological placeholders.

## Audit Source Definitions First

Before writing any Lean, resolve the definition and conventions of every concept
the source statement names. Do not assume you already know them.

- For each named concept, notation, or family, list **all** conditions it
  entails. Generate this list per problem; do not rely on a fixed template.
- Pay attention to conditions that are easy to drop silently because they live
  in the concept's definition rather than the sentence, such as continuity,
  topology, completeness, measurability, or compactness.
- Only after the source conditions are explicit should you map them to Lean.
  Every entailed condition must end up expressed in the Lean statement or
  bundled into a structure/typeclass it uses.
- The audit style may follow a short Accepted Reading / Source / Confidence /
  Ambiguity note when the concept is non-obvious.

## Mathlib Engagement: Acid-Test, Then Reuse and Bundle

This is one tool-driven pass over how the statement meets Mathlib. Do it before
committing to types.

**Acid test (tool-driven).** Before adopting any Mathlib type to carry a source
concept, do not name-match from memory:

- Actively call the search tools — leandex, lean-explore / leanfinder /
  state-search, loogle — to find candidate definitions.
- Read the actual definition (`#print`, hover, or the Mathlib source), not just
  its name.
- Align the source concept with Mathlib's axioms **condition by condition**. A
  name that sounds right is not evidence the definitions coincide.
- If they are not equivalent, do not silently adopt the Mathlib type. Bridge it
  or define a faithful custom concept, and record the deviation.

**Reuse and bundle.** In the same pass:

- Prefer Mathlib's bundled structures / typeclasses over a long list of inline
  hypotheses that re-derive an object's behavior.
- When an object would otherwise be pinned down by many inline hypotheses that
  bloat the signature, reuse a Mathlib bundle if one exists; otherwise package
  the data and axioms once into a local `structure` / `class` and reuse it.
- This is a readability guideline, not a hard threshold. Use judgment.

## Choosing the Declaration Kind

Pick `def`, `structure`, or `theorem` by what the source is doing, not by habit.

- The source **constructs or gives an object** (a map, an isomorphism, a
  specific element) → use a `def` that returns the bundled object (`A ≃* B`,
  `A →+* B`, `M →ₗ[A] N`, …). Do **not** write `theorem … : Nonempty (A ≃* B)`
  or `theorem … : ∃ f, …`; that discards the canonical object.
- The object carries **data plus properties** that belong together → package it
  with a `structure` (a `class` when it is meant to be inferred).
- The source **asserts a proposition holds** (an equality, inequality,
  divisibility, an honest existence/uniqueness claim) → use a `theorem`.
- Soft check: if you find yourself writing many `def`s and almost no
  `structure`s, re-examine whether some should be bundled. Do not enforce a
  fixed ratio.

## Canonical Lean Shapes

Prefer existing Mathlib structures when they match the source concept:

- Rings and commutative algebra: use `CommRing`, `Ring`, `Algebra`,
  `IsDomain`, `IsLocalRing`, `IsNoetherianRing`, `Ideal`, and related Mathlib
  structures as appropriate.
- Ideals: use `Ideal A`.
- Submodules: use `Submodule A M`, not `Ideal A`, when the source concerns
  submodules of a module.
- Ring homomorphisms: use `A →+* B`, not bare functions.
- Ring equivalences: use `A ≃+* B`.
- Module maps: use `M →ₗ[A] N`, not bare functions.
- Algebra maps and equivalences: use Mathlib's bundled algebraic morphisms
  rather than hand-written preservation hypotheses.
- Bijections and correspondences: use `Equiv`, `OrderIso`, `RelIso`, or
  explicit `Function.Injective` plus `Function.Surjective`, depending on the
  source statement.

## No Downgrades

Do not replace a general statement with a special case:

- Arbitrary indexed families must remain indexed families, such as
  `ι : Type*`, `I : ι → Ideal A`, or `N : ι → Submodule A M`.
- Finite families should use `Finset`, `[Fintype ι]`, `[Finite ι]`, or another
  faithful finite encoding.
- A finite sum, product, supremum, infimum, union, or intersection should not be
  collapsed to a binary operation unless the source is genuinely binary.
- A statement about modules or submodules should not be collapsed to a statement
  about ideals.
- A quotient object must be the one in the source. For example, do not confuse
  `A / I ^ n` with `I ^ n / I ^ (n + 1)`.

## Logical Fidelity

- "If and only if", "equivalent", and "TFAE" require `↔` or `TFAE`.
- A one-to-one correspondence should not become mere existence.
- A unique object should use `∃!` or a bundled unique construction when
  appropriate.
- Exactness statements should include every required map and every required
  exactness condition.
- Avoid extra assumptions that make the theorem easier unless the source or
  surrounding formal context requires them. If an extra assumption is needed to
  repair an implicit convention, report it.

## Custom Definitions

Use a custom definition only when Mathlib cannot express the source concept
faithfully.

When adding one:

- Give it real mathematical content.
- Place it near the declarations that need it, following local style.
- Prefer a thin wrapper or bridge to Mathlib when Mathlib has a close but not
  identical concept.
- Never define a concept as `True`, `False`, an empty structure with no
  semantics, or a predicate designed only to make a statement compile.

## Output Quality

- Preserve source text as a docstring when the project convention calls for it.
- Use stable, local naming conventions already present in the file.
- Keep signatures readable: group variables naturally and name hypotheses when
  they carry mathematical meaning.
- After Lean check, fix syntax and type errors without weakening the statement.
