---
name: formalize
description: "Use when turning textbook, paper, blueprint, or user-written mathematics into faithful Lean 4 declarations with sorry proofs, or when auditing/correcting an existing Lean statement to match its informal source."
---

# Formalize

Turn informal mathematics into Lean 4 statement skeletons. The output should be
faithful declarations with real mathematical content and proofs left as
`:= by sorry`.

## When to Use

Use this skill when:

- A theorem, lemma, proposition, corollary, or definition needs to be
  formalized from informal mathematics.
- An existing Lean declaration's statement needs to be corrected to match its
  informal source.
- A blueprint, textbook excerpt, paper note, or user-written statement needs a
  Lean declaration skeleton.

## Workflow

1. Read the source statement and the local Lean context where the declaration
   will live.
2. Extract the mathematical structure:
   - objects and ambient types
   - hypotheses and typeclass assumptions
   - conclusion
   - subclaims, directions, uniqueness clauses, and indexed families
3. Audit the source definitions first: resolve each named concept and list every
   condition it entails (continuity, topology, completeness, etc.), so nothing
   implicit is dropped. See [reference-formalizer.md](reference-formalizer.md).
4. Acid-test the Mathlib definitions: use the `lean-search` skill tools (leandex,
   lean-explore, loogle, …) to find candidate types, read their actual
   definitions, and confirm the axioms match the source condition by condition.
   Prefer bundled Mathlib structures; bridge or define custom only when needed.
5. Choose the declaration kind (`def` for a constructed object, `structure` for
   data-plus-properties, `theorem` for an asserted proposition).
6. Write the Lean declaration and any necessary supporting definitions. Leave
   theorem proofs as `:= by sorry`.
7. Review the draft against [reference-reviewer.md](reference-reviewer.md).
   Fix semantic mismatches before accepting the declaration.
8. Verify with the local Lean checker from the `verification` skill, usually:

```bash
python cli_tools/lean.py check FILE
```

Only accept the result when the semantic review passes and Lean reports no
errors other than intentional `sorry` warnings.

## Boundaries

- Do not prove the theorem.
- Do not do proof search.
- Do not weaken, specialize, or otherwise distort the statement just to make it
  compile.

## References

- Read [reference-formalizer.md](reference-formalizer.md) for statement-writing
  rules and common Lean encodings.
- Read [reference-reviewer.md](reference-reviewer.md) for the strict audit
  checklist.
