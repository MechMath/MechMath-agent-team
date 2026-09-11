# Certification Mode

Normative rules for any agent dispatched with `mode: certification`.
The dispatch names the mode; this file defines it. Your role file defines who you
are and what you own — it does not repeat anything below.

Authority: ADR 0023. This file and `discovery-mode.md` are the only two places
where mode-dependent rules live. If your role file appears to contradict this
file, this file wins and the contradiction is a bug to report.

**This mode's standards are unchanged.** ADR 0023 lowered no proof standard.
Everything below already held before that ADR; it is collected here so the two
modes can be stated side by side, not because anything was relaxed.

## 1. What your output is

Certification output **carries proof weight**. What passes here can support
`proof.tex`. Accordingly:

- Nothing enters on your word alone. A prior `PASS` covers exactly the artifact
  it checked; any later mathematical change needs the responsible specialist and
  fresh verification (invariants 13, 15).
- Verification is single-pass and stateless: one fresh review packet per check,
  no structural pre-check gate (invariant 12). Mechanical tools — compilers,
  grep, linters, result gates — are checks, not mathematical verification
  (invariant 16).

## 2. Coverage is exhaustive

Unlike discovery mode, you do not stop early and you do not cap depth. Every
load-bearing step is checked, and each concern is chased to a verdict.

The rigor standard is `ADR 0005` plus `Rules for All Agents`: no axioms, no
unproved assertions, no "obvious" or "by inspection", atomic and explicitly
justified steps, preconditions checked before use, and no silently added or
strengthened hypotheses.

## 3. You are the only source of `rejected`

A route becomes `rejected` — a hard wall, no way back — **only** through an
exact counterexample or a fresh Verifier FAIL issued in this mode.

Nothing else qualifies. Not budget exhaustion, not an unmet precondition, not a
missing ingredient, not an inconclusive search, not a failed literature lookup.
Those leave the route `open` and it may be re-proposed at any time.

Set `blocked` only when you can name the external condition being waited on.
Without a named condition it is `open`.

`NO_OBJECT` — the claim that some object does not exist — is available only here,
and only with an exhaustiveness argument. Discovery mode's
`NO_RESULT_IN_DECLARED_SCOPE` is a statement about a scope and never implies it.

## 4. Obligations

Load-bearing estimates, constructions, theorem inputs, case splits, dependency
bridges, and final assembly steps appear in the obligation ledger before they
support a proof (invariants 7, 8). Missing constructions, maps, invariants,
cases, named statements, definitions, and bridges are obligations — not final
answers.

An obligation is a **gap list, not a risk list**. Each entry names a concrete
construction, bound, or bridge still missing if the central claim holds. "This
step might not be rigorous" is not an obligation — finding that is your job, not
the proposer's. A candidate arriving with no obligations does not enter this mode.

## 5. Provenance

A named theorem carries proof weight only once its exact usable statement,
its source **or derivation route**, its preconditions, and its non-circularity
are recorded (invariant 10).

Note the disjunction: a local derivation is a legitimate alternative to a
citation. A negative literature search therefore never blocks a fact — it only
means the second branch must be taken.

Specialized notation, named families, classification labels, and boundary
conventions need accepted readings before supporting either a proof or an
obstruction (invariant 9).

Mathematical content supplied from outside the run is a **provenance fact, not
run history**. It must be disclosed in reader-facing output; stripping agent
history must not strip it.

## 6. Freshness

Verifiers are fresh and stateless for every check (ADR 0003, invariant 3);
the Orchestrator may not resume one. Auditors performing an independent audit
are dispatched fresh for the same anti-anchoring reason.

Every verification round leaves a restartable review packet with verdict,
blockers, audit status, external verification status, proof-obligation status,
and next action (invariant 6).

## 7. Failure is an input to discovery, not a terminus

When you FAIL something, the finding goes back to discovery as a **specific
break point** — which step, what is missing. In discovery that reads as a gap
specification and the route continues from there.

Only an exact counterexample ends a route. A FAIL on a repairable proof does not.
