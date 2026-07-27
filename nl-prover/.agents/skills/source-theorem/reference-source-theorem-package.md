# Source Theorem Package

Use this template for any named theorem, classification, folklore result, major
estimate, or theorem-shaped inequality that carries a proof branch.

## Minimum Package

| Field | Required content |
|-------|------------------|
| Local label | Short label used in this workspace |
| Role in branch | Main step, precondition bridge, definition source, estimate, case split, or final assembly |
| Exact usable statement | Quantifiers, objects, hypotheses, and conclusion in the form needed here |
| Source or derivation route | KB-Manager note, research note, local proof plan, verified dependency, or human clarification |
| Literature trace | Queries, local references, papers, and citation layers used to locate the statement |
| Preconditions | Every condition needed before applying the theorem |
| Current verification | Where each precondition is proved, assumed, or still open |
| Bridge to branch | How the theorem implies the current lemma or final target |
| Component bridge ledger | Any theorem-package subclaims that must be proved or sourced separately |
| Independence status | Independent, equivalent to current lemma, stronger than target, unknown, or circular |
| Next action | Use, source lookup, local derivation, bridge lemma, resketch, definition lookup, regulator classification, or human review |

## Equivalence Smoke Tests

Before marking a theorem `usable`, answer these questions.

- Exact-match test: after renaming symbols, is the theorem the same statement as
  the current lemma or main theorem?
- Reformulation test: does expanding definitions, taking reciprocals, moving
  terms across an equality or inequality, dualizing, or applying a standard
  monotone transform turn it into the target?
- Parameter test: does optimizing, minimizing, maximizing, averaging, or
  specializing a parameter yield exactly the target conclusion?
- Extremal-domain test: does the proof change `max` to `sup`, use a
  compactification, pass to a limit, or move between open and closed parameter
  spaces?
- Rigidity test: does the proof need an equality case, uniqueness statement,
  converse direction, or classification rigidity that is not part of the stated
  source theorem?
- Boundary test: does the theorem rely on endpoint, finiteness, regularity, or
  nondegeneracy conventions that are not established in the current problem?
- Strength test: does the theorem prove a strictly stronger statement than the
  target under the same or weaker hypotheses?
- Source-dependence test: is the only available justification another statement
  whose proof appears to use the target or an equivalent theorem?

If any test says `yes` and no independent source, derivation, or local bridge
is recorded, the theorem package is not usable evidence. Mark it
`needs-local-derivation`, `needs-source`, or `needs-bridge-lemma` and route the
branch instead of presenting a proof.

## Component Bridge Ledger

When a broad theorem package carries more than one step, split it into rows.
Each row must be justified by the source theorem itself, an accepted dependency,
a local lemma, or an open obligation. Use separate rows for:

- strict versus weak inequalities, positivity, nonvanishing, or lower bounds;
- equality cases, rigidity, uniqueness, converse directions, or classification
  exclusions;
- endpoint, compactification, maximum/supremum, limiting, or parameter-domain
  changes;
- normalization, invariance, representative-to-family, quotient, or
  object-replacement bridges;
- regularity, orientability, connectedness, genus/rank/dimension, genericity,
  or nondegeneracy preconditions.

If any component row is open, the theorem may still guide the route, but it
does not close the proof. Assign the row to a local lemma, Searcher, Auditor, DAG repair, human clarification, Regulator, or a
recovery branch.

## Generator Lint Hook

Before a Generator marks a proof attempt ready, it runs:

```bash
uv run python cli_tools/gate.py proof-attempt <proof_vN.md> --status <status.md>
```

The lint check rejects theorem-like citations such as standard estimates or
named theorems unless the proof attempt records a dependency, theorem
precondition audit, or source-theorem obligation. It also rejects a proof that
introduces a definition by the target criterion and then finishes by unfolding
that definition unless an accepted independent definition source is recorded.

## Record Format

```markdown
## Source Theorem Package: <local label>

- Role in branch:
- Exact usable statement:
- Source or derivation route:
- Literature trace:
  - Keyword families:
  - Local references:
  - Query outputs:
  - Papers retained:
  - Citation layers traced:
  - Paper cards:
- Independence status:
- Equivalence smoke tests:
  - Exact-match:
  - Reformulation:
  - Parameter:
  - Extremal-domain:
  - Rigidity:
  - Boundary:
  - Strength:
  - Source-dependence:

### Preconditions

| Precondition | Where established | Status |
|--------------|-------------------|--------|
| <condition> | <statement/dependency/step/source> | proved/open/blocker |

### Component Bridge Ledger

| Component | Where justified | Status |
|-----------|-----------------|--------|
| <strictness/equality/normalization/endpoint/final bridge> | <source/dependency/local lemma/open route> | proved/open/blocker |

### Bridge

<Step-by-step explanation of how the theorem yields the lemma or final target.>

### Classification

`usable` | `needs-source` | `needs-local-derivation` |
`needs-bridge-lemma` | `resketch` |
`definition/human-review` | `obstruction-candidate`

### Next Action

<smallest owner and concrete next route: Searcher, Auditor, Generator, Sketcher, Regulator, or Human>
```
