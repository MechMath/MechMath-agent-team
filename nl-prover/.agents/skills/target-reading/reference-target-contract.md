# Target Contract Reference

Write this artifact at `sketch/target_contract.md`. Keep it short enough to
read on resume; use it as the source of truth for statement preservation,
terminal-lemma assembly, and obstruction checks.

```markdown
# Target Contract

## Source
- Problem file: <path>
- Exact target passage: <quote or line reference, short enough to identify the claim>
- Local definitions read: <definitions, notation, and named constructions used by the target>

## Logical Shape
- Requested result: proof | counterexample | obstruction | computation | classification | other
- Main assertion form: implication | equivalence | characterization | existence | uniqueness | construction | equality | inequality | other
- Quantifier order and dependencies: <for all/exists variables, domains, and dependencies>
- Hypotheses: <conditions that must be satisfied before any conclusion is tested>
- Conclusions: <what must be proved or what may fail in a disproof>

## Answer Polarity and Resolution Criteria
- Accepted reading of the question: universal theorem | existential/witness
  theorem | nonexistence theorem | classification | computation |
  refutation of a universal principle | other
- Ambiguity audit: <why this reading is forced by the wording/context, or the
  unresolved alternative readings>
- What would prove the target: <arbitrary-object proof, witness plus checks,
  construction plus verification, bidirectional proof, exhaustive
  classification, computation certificate, etc.>
- What would refute the target: <counterexample to a universal claim,
  impossibility proof for an existential claim, failed classification case,
  inconsistent hypotheses, etc.>
- Single example sufficient? YES/NO, <only if a witness settles the accepted
  reading>
- Single counterexample sufficient? YES/NO, <only if refuting a universal or
  stated general principle settles the accepted reading>

## Displayed Conditions and Formula Roles
| Item | Text or label | Role in target | Notes |
|------|---------------|----------------|-------|
| <condition/formula> | <short text> | hypothesis/definition/equivalent condition/conclusion/notation/unresolved | <why this role is accepted> |

## Direction Ledger
Use for equivalences, characterizations, biconditionals, or classification
theorems.

| Direction | Assumptions for this direction | Conclusion for this direction | Owner |
|-----------|--------------------------------|-------------------------------|-------|
| forward | <left side plus shared hypotheses> | <right side> | <lemma/final bridge/source theorem/open> |
| reverse | <right side plus shared hypotheses> | <left side> | <lemma/final bridge/source theorem/open> |

## Named Objects and Construction Semantics
| Object | Accepted definition or construction rule | Source | Replacement/object bridge needed? |
|--------|------------------------------------------|--------|-----------------------------------|
| <object> | <definition/rule or unresolved> | problem/dependency/research/human clarification/open | NO/YES, <bridge obligation> |

## Obstruction Requirements
- Exact claim or direction an obstruction would refute: <claim/direction>
- Hypotheses that the proposed object must satisfy: <list>
- Accepted definitions and construction semantics required: <list>
- Conclusion failure that must be shown: <list>

## Open Reading Obligations
NONE
<or each target-shape, formula-role, definition, construction, convention, or human-review obligation>

## Branching Consequence
- Proof branch may proceed: YES | NO
- Required next owner if NO: Auditor | Sketcher | Generator | Verifier | Regulator | Human
```

## Review Questions

- Does the proof target the main assertion, not just a nearby displayed formula?
- Does the proposed terminal result match the accepted answer polarity and its
  stated resolution criteria?
- If the target is an equivalence or characterization, are all required
  directions assigned or proved?
- If a counterexample is proposed, does it satisfy the hypotheses for the exact
  direction it refutes?
- If the target asks for a witness or existence result, does the proof actually
  construct or source an admissible object and verify every required property?
- Are named constructions used with their accepted rule rather than replaced by
  easier objects?
- Are local definitions, conventions, and formula roles sourced from the problem
  or accepted context rather than guessed?
