---
type: experience
kind: negative-constraint
id: neg-do-not-infer-differential-factor-exclusions-beyond-the-last
statement: Do not infer differential-factor exclusions beyond the last completely certified order, or full-order minimality, merely because the required exact factor runtime is unavailable.
trigger: An increasing-order exact factorization contract stops at an implementation gate after one or more lower orders were disposed completely.
why: Software absence supplies no incidence, factor, Ore-quotient, or minimality certificate for the unprocessed orders; preserving the first untested order prevents an operational stop from becoming a false mathematical obstruction.
failure_modes: Do not use this boundary to discard genuinely complete certificates from a different exact implementation, and do not rerun already certified lower orders unless their hash-bound inputs changed.
provenance: ['regulator-classification']
scope: general
refs: ['[[Concept_DifferentialOperatorFactorization]]', 'recovery/regulator_decision_factorial_borel_two_germ_1.md', 'routes/computation_audit_factorial_borel_two_germ_minimal_1.md']
source: 2_5
---
Do not infer differential-factor exclusions beyond the last completely certified order, or full-order minimality, merely because the required exact factor runtime is unavailable.
