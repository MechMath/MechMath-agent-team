# Verifier — global proof refinement mode

Loaded only when the dispatch names this verification mode.
The standard in `prompts/verifier.md` applies unchanged; this file adds what is
specific to the mode. If the dispatch named no mode, you are in lemma proof
verification and should not be reading this file.

## Global Proof Refinement Verification Mode

Use this mode when asked to verify `refinement/proof_refined.tex`.

Read:
- the original `problem.md`,
- `sketch/research_notes.md` when present,
- `refinement/original_proof.tex`,
- `refinement/proof_refinement.md`,
- `refinement/proof_refined.tex`,
- the selected decomposition and lemma statements,
- any `queries/<query_id>/kb-manager.md` files named by Verifier risk checklists,
- accepted generator proofs — the proofs themselves, **not** the reports on them:
  a refinement is judged against what was proved, and reading what an earlier
  referee concluded replaces your judgement with theirs here exactly as it does
  in lemma mode (see `prompts/verifier.md`, "What you must not open"),
- optional `refinement/decomposition_refined.md` if the DAG changed.

Check:
1. The refined proof proves the exact original theorem.
2. If the DAG changed, the new DAG is acyclic, sufficient, and consistent with
   the refined proof.
3. Deleted or bypassed lemmas are truly unnecessary for the refined route.
4. Every dependency lemma and theorem is used only after its preconditions are
   established.
5. The proof does not add, strengthen, or hide hypotheses.
6. The proof is not merely shorter by becoming hand-wavy; every substantive step
   remains justified.
7. Any normalized notation, accepted convention, or boundary case reading is the
   same as in the accepted proof or is independently audited.
8. The refined version is materially shorter, cleaner, or structurally simpler
   than the original accepted proof.
9. The refined proof does not remove the adversarial checks that made the
   original proof safe: global obstructions, local-to-global compatibility,
   invariants, boundary conditions, compact support, regularity, and degenerate
   cases remain audited where relevant.
10. Any analysis/preflight risk checklist item that applies to the refined proof
   remains satisfied.

Verdict rules for global proof refinement:
- `PASS`: the refined proof is correct, preserves all hypotheses, and is a real
  improvement over the original.
- `NEEDS_REVISION`: the proof route looks promising but has fixable gaps or
  insufficient justification.
- `FAIL`: the refined proof is incorrect, changes the theorem, adds/strengthens
  hypotheses, misuses dependencies, or is not actually an improvement.

Write the report and verdict to the output paths requested by the Orchestrator,
normally `refinement/verifier_report.md` and `refinement/verdict.md`.
Also write `refinement/review_packet.md` unless the Orchestrator assigns a
different packet path.

