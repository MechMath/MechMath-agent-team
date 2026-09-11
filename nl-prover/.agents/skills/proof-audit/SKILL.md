---
name: proof-audit
description: "Adjudication checklist for one mathematical proof route — intake and freeze, dependency graph, step chain, error terms and effective constants, mechanization scope, adversarial validation, archival. Use before accepting a proof, during adversarial review, when a dependency changed under an already-accepted lemma, and before declaring a run complete. Trigger on 'audit this proof', 'is this step justified', 'check the error term', 'does the chain close', 'this dependency was rewritten', 'can we mark the run done', or a Verifier dispatch that needs more than packet shape. Not resident text: read it when a proof is on the table, and not otherwise."
---

# Proof Audit Checklist

A stage-by-stage adjudication checklist for **one** proof route. It is a **gate**,
not a suggestion: the pass condition below is what a Verifier's verdict is
measured against.

The stages live in [references/generic-audit.md](references/generic-audit.md) —
intake and freeze (B.1), the dependency graph and assumption cards (B.5), the
step chain (B.6), residual terms and effective bounds (B.8), mechanization scope
(B.11.2), adversarial validation and archival (B.12). Load that file when you are
auditing; this page is the typing rule, the pass gate, and the map of what is
already mechanized.

## Why this checklist, in this harness

Not a speculative import. An audit of this harness's own workspaces — 20
workspaces, 345 lemma directories, 196 accepted lemmas, 111 of them
dependency-bearing — measured:

- **11 of 111** lemmas accepted *before* a dependency they declare reached its
  own accepting verdict (B5.1, B5.8);
- **8 of 111** whose dependency's proof was rewritten *after* the dependent's
  PASS, with nothing re-verifying it — invariant 15 in your platform file
  (`AGENTS.md` on Codex, `CLAUDE.md` on Claude Code) (B12.16);
- **7** obligation-ledger rows still reading `open`/`blocker`, out of 1347 rows,
  inside proofs carrying a PASS verdict (B12.13);
- **one** genuine dependency cycle between two lemmas both marked PASS (B5.7);
- **four** completed runs that exported a `proof.pdf` while lemma directories
  reachable from the assembly held only a statement (B6.7, B12.16).

Every one of those has a checklist item that names it. Read the list as a list of
defects this harness has been measured to produce, not as generic hygiene.

## Scope of one run

This checklist audits **one** proof route. If the artifact contains multiple `OR`
proof routes, run the checklist **separately for every route**. Their `AND`/`OR`
aggregation is then audited on its own against the dependency graph. **A pass for
one route never substitutes for another.**

## B.0 Item typing

- **`[M]` Mandatory** — every audit must adjudicate the item. It cannot be marked
  `not_applicable`.
- **`[A]` Applicability-gated** — applicability is adjudicated *first*. An
  applicable item must then be audited. A non-applicable item must record the
  decision predicate, the rationale, the evidence reference, and who decided.
  **Unchecked, not found, and budget-exhausted are not `not_applicable`.**

Record every item with a stable `check_id` and one of
`pass / revise / blocked / not_applicable`, plus evidence references, findings,
required remediation, and the exact path and version of the frozen artifact you
read.

## B.0 Pass gate

> A proof audit passes only when every `[M]` item and every applicable `[A]` item
> is `pass`, no item is `blocked`, the evidence obligation set is closed, and the
> review packet is a fresh Verifier's, bound to the exact artifact it read.

The trailing clause is adapted. The source specification requires a
platform-signed attestation, and this harness has no attestation service. What
replaces it is the thing this harness *does* have — a fresh, stateless Verifier
who did not write the proof (invariants 3 and 12 in your platform file:
`AGENTS.md` on Codex, `CLAUDE.md` on Claude Code), whose packet names
under `Inputs Checked` the exact proof file, statement, and version it read. A
packet that cannot say which artifact it audited cannot close the gate, and a
packet bound to `proof_v3` does not license `proof_v4`.

An open obligation, conflicting evidence, or an applicable item you cannot decide
produces `INCONCLUSIVE` or a revision route. It does **not** produce a pass.

## What is already mechanized, and what is not

Do not hand-check what a gate already checks, and do not assume a gate covers
more than it does. Every gate in `cli_tools/gate.py` is a **shape** check; none of
them reads mathematics. The third column is where the audit actually happens.

| Checklist item | Gate that covers it | What remains a human/model judgement |
|---|---|---|
| **B5.1** graph preserves `AND`/`OR` and within-route edges | `gate dag` parses each `statement.md` `## Dependencies`, resolves labels to directories, reports `dependency_without_directory` and `unreadable_dependency_field` | Whether a conjunction was flattened into prose, whether two branches are genuinely alternative routes, whether a declared edge is the one the proof actually uses |
| **B5.7** circular dependencies | `gate dag` — `dependency cycle`, a real traversal (`plan-logic.md`'s acyclicity check is a model reading the file) | Which edge in the cycle is the wrong one |
| **B5.8** freshness propagated downstream | `gate dag` — `accepted_before_dependency`, `stale_pass` | Whether an mtime hit is real consumption or a quotation/copy; whether the dependency's change was substantive |
| **B12.16** review valid only for the version it bound | `gate dag` `stale_pass`; `gate review-packet` requires `Inputs Checked` | Whether the rewritten dependency changed anything the dependent relied on |
| **B12.13** open obligation ≠ pass | `gate dag` `open_ledger_rows_in_accepted`; `gate proof-attempt` requires the Load-Bearing Obligation Ledger and rejects `TODO`/`FIXME`/`\sorry`/`[human-review]`/template placeholders | Whether a row marked `resolved` actually is; whether the argument's real obligations reached the ledger at all |
| **B12.9** no obligation silently omitted | `gate proof-attempt` required sections and audit subsections; `gate review-packet` required sections and `Verdict Snapshot` keys | Whether the ledger is complete against the proof as written — a gate counts rows, not obligations |
| **B1.x / B12.15** assembly complete, nothing reachable left unproved | `gate complete` reconciles every `lemmas/` directory against `STATUS.md` and requires lintable passing packets for accepted rows; `gate dag` `unproved_reachable`, `unaccepted_top_node` | Whether the frozen snapshot is the one the proof used; whether the archive replays |
| **B12.1** reviewer independence | `prompts/verifier.md` "What you must not open" — the prior report, packet, verdict, previous proof, generator `status.md` and `response_to_verifier.md` (ADR 0003), as a prohibition; the packet records `Anchoring inputs received` | Whether the dispatch text itself recited a prior verdict, and how much that contaminated the reading |
| **B12.8** scope of pass | `gate review-packet` — `Blocking Issues`, `Open Proof Obligations`, `Uncertainty`, `Next Action` sections must be present | Saying what the pass does **not** cover, in words a later reader can act on |
| **B12.12** evidence kinds not interchanged | `gate result-contract` catches a missing route / unavailable source / agent inability presented as a proof or an obstruction; `gate discovery` lints the schema of kill verdicts | Proof vs mechanized check vs numerical experiment vs heuristic *inside* an otherwise passing proof |
| **B1.6 / B12.5** external results frozen, errata checked | `gate citation-audit` — every key resolves in `refs.bib`, first-use rule, no `pending-audit` result used as settled support, attribution detector | Whether the cited statement is the one the proof actually used, and whether it has since been corrected, withdrawn, or beaten by a barrier |
| **B5.2–B5.6** assumption cards, exact variants, edge binding | none | All of it. There is no mechanical notion of a variant here |
| **B.6** the step chain | none | All of it |
| **B.8** residual terms, resource accounting, effective constants | none | All of it |
| **B.11.2** mechanization scope and TCB | none | All of it |
| **B12.2–B12.7, B12.14, B12.17** counterexample search, independent recomputation, sensitivity, aggregation | none | All of it |

The bottom half of that table is the point. The gates cover ordering, shape, and
provenance — the failures that are cheap to detect and were going undetected. The
mathematics is untouched by any of them, and a green gate run is not evidence for
a single item in B.6, B.8, or B.11.2.
