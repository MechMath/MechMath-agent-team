import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "cli_tools"))
from _gate import completion as completion_gate


def packet(
    *,
    external="ran; raw files: verifier/external.json",
    next_action="MERGE",
    include_obstruction_audit=False,
):
    obstruction_section = (
        "\n## Target Obstruction Audit\n"
        "- Obstruction kind: concrete counterexample\n"
        "- Object and hypotheses audit: object satisfies the original hypotheses\n"
        "- Conclusion failure: target conclusion fails for the object\n"
        "- Accepted reading challenge: accepted definitions and conventions checked\n"
        "- Boundary and degenerate variants checked: variants checked under accepted conventions\n"
        "- Process-failure dependence: NO\n"
        if include_obstruction_audit
        else ""
    )
    return f"""# Review Packet: lem:test (v1)

## Inputs Checked
- Problem: problem.md
- Statement: lemmas/lem:test/statement.md
- Proof: lemmas/lem:test/generator/proof_v1.md
- Dependencies read: NONE
- Generator response read: NONE

## Verdict Snapshot
- Verdict: PASS
- Score: 1
- Statement preservation: PASS
- Problem-reading audit: PASS
- Hypotheses/preconditions audit: PASS
- Proof-obligation classification: PASS
- Definition/notation audit: PASS
- Source theorem audit: PASS
- Adversarial route audit: PASS
- External cross-verification: {external}

## Blocking Issues
NONE

## Problem Reading and Normalization
- Normalized reading used: NONE
- Source of reading: N/A
- Material ambiguity remains: NO
- Boundary conventions audited: N/A

## Dependency and Theorem Ledger
| Item used | Required preconditions | Where established | Status |
|-----------|------------------------|-------------------|--------|

## Definition and Source-Theorem Audit
- Specialized definitions used: NONE
- Source theorem warrant: PASS
- Circularity check: PASS

## Load-Bearing Obligation Ledger
| Obligation | Type | Where supplied or assigned | Preconditions checked | Status |
|------------|------|----------------------------|-----------------------|--------|
| main implication | final bridge | proof step 4 | YES | resolved |

## Adversarial Route Audit
- Target polarity: implication
- Opposite-polarity examples or obstructions considered: NONE
- Global compatibility checks: NONE NEEDED
- Known theorem or invariant collisions checked: NONE FOUND
- Unresolved adversarial blockers: NONE
{obstruction_section}

## Open Proof Obligations
NONE

## Uncertainty
NONE

## Next Action
{next_action}
"""


def status(*, phase="complete", obligation_section="NONE", lemma_status="verified"):
    return f"""# Proof Status: sample

## Problem
Sample theorem.

## Phase
{phase}

## Lemma Status
| Lemma | Dependencies | Status | Generator Attempts | Verifier Verdict | Review Packet |
|-------|--------------|--------|--------------------|------------------|---------------|
| lem:test | - | {lemma_status} | 1/3 | PASS | lemmas/lem:test/verifier/review_packet_v1.md |

## History
- Run completed.

## Open Proof Obligations
{obligation_section}
"""


def proof_review(
    *,
    selected_status="SOURCE_OR_DEFINITION_RECOVERY",
    unresolved="NONE",
    proof_missing="source theorem is missing",
    refutation_object="NONE",
    hypotheses="not checked",
    conclusion="not checked",
    boundary="not checked",
    reason="recover the missing definition before deciding",
):
    return f"""# Proof Review

## Target Reading Check
- Exact target or direction: original theorem direction
- Accepted parameter range and boundary conventions: stated range
- Accepted definitions, named constructions, and presentations: problem definitions
- Unresolved reading obligations: {unresolved}

## Proof Route
- Best available proof route: derive the main estimate and assemble the theorem
- Missing evidence, if any: {proof_missing}
- Next owner if pursued: Sketcher

## Refutation Route
- Proposed object, contradiction, or impossible precondition: {refutation_object}
- Hypotheses satisfied under accepted reading: {hypotheses}
- Conclusion failure under accepted reading: {conclusion}
- Boundary/presentation dependence: {boundary}
- Next owner if pursued: Verifier

## Decision
- Selected status: {selected_status}
- Owner: Sketcher
- File target: sketch/decomposition.md
- Reason: {reason}
"""


class CompletionGateTests(unittest.TestCase):
    def make_workspace(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        packet_path = root / "lemmas/lem:test/verifier/review_packet_v1.md"
        packet_path.parent.mkdir(parents=True)
        packet_path.write_text(packet(), encoding="utf-8")
        (root / "proof.tex").write_text(
            "\\begin{theorem}T\\end{theorem}\\begin{proof}Done.\\end{proof}\n",
            encoding="utf-8",
        )
        (root / "STATUS.md").write_text(status(), encoding="utf-8")
        return temp, root

    def test_accepts_complete_workspace(self):
        temp, root = self.make_workspace()
        with temp:
            result = completion_gate.lint_workspace(root)
        self.assertEqual([], result.errors)
        self.assertEqual(1, len(result.packets_checked))

    def test_rejects_pending_proof_marker(self):
        temp, root = self.make_workspace()
        with temp:
            (root / "proof.tex").write_text("\\sorry{}\n", encoding="utf-8")
            result = completion_gate.lint_workspace(root)
        self.assertTrue(any("pending proof marker" in error for error in result.errors))

    def test_rejects_process_gap_final_proof(self):
        temp, root = self.make_workspace()
        with temp:
            (root / "proof.tex").write_text(
                "\\begin{theorem}T\\end{theorem}\n"
                "\\begin{proof}The route is unavailable, so gap found.\\end{proof}\n",
                encoding="utf-8",
            )
            result = completion_gate.lint_workspace(root)
        self.assertTrue(any("result contract" in error for error in result.errors))

    def test_rejects_noncomplete_phase(self):
        temp, root = self.make_workspace()
        with temp:
            (root / "STATUS.md").write_text(status(phase="prove"), encoding="utf-8")
            result = completion_gate.lint_workspace(root)
        self.assertTrue(any("Phase is not complete" in error for error in result.errors))

    def test_rejects_unaggregated_candidate_cards(self):
        # ADR 0016 Phase 3.5: candidate cards present but not aggregated blocks completion.
        temp, root = self.make_workspace()
        with temp:
            cand = root / "memory" / "candidates"
            cand.mkdir(parents=True)
            (cand / "verifier-run1.jsonl").write_text(
                '{"kind":"negative-constraint","statement":"do not divide by zero","trigger":"div"}\n',
                encoding="utf-8",
            )
            result = completion_gate.lint_workspace(root)
        self.assertTrue(any("not aggregated" in e for e in result.errors))

    def test_accepts_aggregated_candidate_cards_promoted_to_the_long_term_tier(self):
        temp, root = self.make_workspace()
        with temp:
            cand = root / "memory" / "candidates"
            cand.mkdir(parents=True)
            card = '{"kind":"negative-constraint","statement":"do not divide by zero","trigger":"div"}\n'
            (cand / "verifier-run1.jsonl").write_text(card, encoding="utf-8")
            (root / "memory" / "candidates_aggregated.jsonl").write_text(card, encoding="utf-8")
            (root / "memory" / "candidates_promoted.json").write_text('{"promoted": []}\n', encoding="utf-8")
            result = completion_gate.lint_workspace(root)
        self.assertEqual([], result.errors)

    def test_rejects_open_status_obligation(self):
        temp, root = self.make_workspace()
        open_table = (
            "| Obligation | Owner | Source | Status | Next Action |\n"
            "|------------|-------|--------|--------|-------------|\n"
            "| fill final bridge | Generator | packet.md | open | revise proof |\n"
        )
        with temp:
            (root / "STATUS.md").write_text(
                status(obligation_section=open_table), encoding="utf-8"
            )
            result = completion_gate.lint_workspace(root)
        self.assertTrue(any("open obligation row" in error for error in result.errors))

    def test_rejects_unlintable_review_packet(self):
        temp, root = self.make_workspace()
        with temp:
            packet_path = root / "lemmas/lem:test/verifier/review_packet_v1.md"
            packet_path.write_text(packet(external="TODO"), encoding="utf-8")
            result = completion_gate.lint_workspace(root)
        self.assertTrue(
            any("External cross-verification" in error for error in result.errors),
            result.errors,
        )

    def test_rejects_completion_without_any_review_packet(self):
        temp, root = self.make_workspace()
        with temp:
            (root / "STATUS.md").write_text(
                "# Proof Status: sample\n\n"
                "## Phase\ncomplete\n\n"
                "## Lemma Status\nNONE\n\n"
                "## Open Proof Obligations\nNONE\n",
                encoding="utf-8",
            )
            result = completion_gate.lint_workspace(root)
        self.assertTrue(
            any("No review packets" in error for error in result.errors),
            result.errors,
        )

    def test_rejects_restart_proof_review_at_completion(self):
        temp, root = self.make_workspace()
        with temp:
            review_path = root / "review/proof_review.md"
            review_path.parent.mkdir()
            review_path.write_text(proof_review(), encoding="utf-8")
            result = completion_gate.lint_workspace(root)
        self.assertTrue(
            any("selected restart status" in error for error in result.errors),
            result.errors,
        )

    def test_accepts_final_proof_ready_review_at_completion(self):
        temp, root = self.make_workspace()
        with temp:
            review_path = root / "review/proof_review.md"
            review_path.parent.mkdir()
            review_path.write_text(
                proof_review(
                    selected_status="FINAL_PROOF_READY",
                    proof_missing="NONE",
                    reason="proof route is complete and ready for final verification",
                ),
                encoding="utf-8",
            )
            result = completion_gate.lint_workspace(root)
        self.assertEqual([], result.errors)

    def test_rejects_obstruction_review_without_accepted_packet(self):
        temp, root = self.make_workspace()
        with temp:
            review_path = root / "review/proof_review.md"
            review_path.parent.mkdir()
            review_path.write_text(
                proof_review(
                    selected_status="OBSTRUCTION_VERIFICATION",
                    refutation_object="explicit object x with stated parameters",
                    hypotheses="the object satisfies every original hypothesis",
                    conclusion="the target conclusion fails for x",
                    boundary="no dependence; boundary and presentation checked",
                    reason="send the concrete obstruction to a fresh Verifier",
                ),
                encoding="utf-8",
            )
            result = completion_gate.lint_workspace(root)
        self.assertTrue(
            any("no accepted obstruction review packet" in error for error in result.errors),
            result.errors,
        )

    def test_accepts_obstruction_review_with_accepted_packet(self):
        temp, root = self.make_workspace()
        with temp:
            review_path = root / "review/proof_review.md"
            review_path.parent.mkdir()
            review_path.write_text(
                proof_review(
                    selected_status="OBSTRUCTION_VERIFICATION",
                    refutation_object="explicit object x with stated parameters",
                    hypotheses="the object satisfies every original hypothesis",
                    conclusion="the target conclusion fails for x",
                    boundary="no dependence; boundary and presentation checked",
                    reason="send the concrete obstruction to a fresh Verifier",
                ),
                encoding="utf-8",
            )
            obstruction_path = root / "verifier/obstruction_review_packet.md"
            obstruction_path.parent.mkdir()
            obstruction_path.write_text(
                packet(
                    next_action="ACCEPT_OBSTRUCTION",
                    include_obstruction_audit=True,
                ),
                encoding="utf-8",
            )
            (root / "proof.tex").write_text(
                "\\begin{proof}Thus the target assertion is false.\\end{proof}\n",
                encoding="utf-8",
            )
            result = completion_gate.lint_workspace(
                root,
                extra_packets=[obstruction_path],
            )
        self.assertEqual([], result.errors)


if __name__ == "__main__":
    unittest.main()
