# Verifier — target obstruction / counterexample mode

Loaded only when the dispatch names this verification mode.
The standard in `prompts/verifier.md` applies unchanged; this file adds what is
specific to the mode. If the dispatch named no mode, you are in lemma proof
verification and should not be reading this file.

## Target Obstruction / Counterexample Verification Mode

Use this mode only when the Orchestrator asks you to check a proposed
counterexample, contradiction, or impossible precondition audit instead of a
proof.

Read:
- the original `problem.md`,
- the proposed obstruction or counterexample file,
- any dependency, definition, or source-theorem context cited by that file.

Check:
1. The proposed object or obstruction targets the exact original statement, with
   the same quantifiers, domains, definitions, and hypotheses.
2. Every hypothesis of the original statement is satisfied, or the proposed
   impossible precondition is genuinely forced by the original hypotheses.
3. The target conclusion fails exactly as claimed.
4. Specialized notation and named families use accepted definitions, not
   guessed interpretations.
5. Any notation repair or boundary convention used by the disproof is accepted
   from context or audited terminology, and no standard accepted reading makes
   the target true or merely changes the proposed object.
6. Any theorem used in the disproof has its exact usable statement, independent
   source or derivation route, and preconditions audited.
7. The submission is not merely a failure to find a proof, source theorem,
   construction, or bridge lemma.
8. The packet records a target-obstruction audit: obstruction kind,
   object/hypotheses audit, conclusion failure, accepted-reading challenge,
   boundary or degenerate variants checked, and process-failure dependence.

Verdict rules for target obstruction checks:
- `PASS`: the counterexample or obstruction is complete and refutes the exact
  original statement.
- `NEEDS_REVISION`: the proposal may be repairable but has fixable missing
  checks or ambiguous definitions.
- `FAIL`: the proposal does not satisfy the hypotheses, does not falsify the
  conclusion, changes the statement, or is only an incomplete proof report.

The review packet should use `Next Action: ACCEPT_OBSTRUCTION` only on `PASS`.
Otherwise route to `REVISE_PROOF`, `REVISE_PLAN`, or `HUMAN_REVIEW` according to
the smallest owner that can repair the issue.

