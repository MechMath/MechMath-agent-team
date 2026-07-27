import importlib.util
from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "cli_tools"))
from _gate import proof_review as proof_review_lint


def proof_review(
    *,
    status="SOURCE_OR_DEFINITION_RECOVERY",
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
- Selected status: {status}
- Owner: Sketcher
- File target: sketch/decomposition.md
- Reason: {reason}
"""


class ProofReviewLintTests(unittest.TestCase):
    def test_accepts_restart_state_with_missing_source(self):
        result = proof_review_lint.lint_text(proof_review())
        self.assertEqual([], result.errors)
        self.assertEqual("SOURCE_OR_DEFINITION_RECOVERY", result.selected_status)

    def test_rejects_missing_required_section(self):
        result = proof_review_lint.lint_text("## Decision\n- Selected status: RESKETCH\n")
        self.assertTrue(any("Missing required section" in error for error in result.errors))

    def test_rejects_multiple_statuses(self):
        result = proof_review_lint.lint_text(
            proof_review(status="PROOF_REVISION | RESKETCH")
        )
        self.assertTrue(any("exactly one status" in error for error in result.errors))

    def test_accepts_concrete_obstruction_routing(self):
        result = proof_review_lint.lint_text(
            proof_review(
                status="OBSTRUCTION_VERIFICATION",
                proof_missing="source theorem is missing",
                refutation_object="explicit object x with stated parameters",
                hypotheses="the object satisfies every original hypothesis",
                conclusion="the target conclusion fails for x",
                boundary="no dependence; boundary and presentation checked",
                reason="send the concrete obstruction to a fresh Verifier",
            )
        )
        self.assertEqual([], result.errors)

    def test_rejects_obstruction_from_missing_context(self):
        result = proof_review_lint.lint_text(
            proof_review(
                status="OBSTRUCTION_VERIFICATION",
                refutation_object="the required source theorem is missing",
                hypotheses="not checked",
                conclusion="not checked",
                boundary="not checked",
                reason="the route cannot prove the statement",
            )
        )
        self.assertTrue(
            any("process" in error.casefold() for error in result.errors),
            result.errors,
        )

    def test_rejects_obstruction_with_unresolved_reading(self):
        result = proof_review_lint.lint_text(
            proof_review(
                status="OBSTRUCTION_VERIFICATION",
                unresolved="definition of the named construction is unresolved",
                refutation_object="explicit object x",
                hypotheses="x satisfies the hypotheses",
                conclusion="the conclusion fails",
                boundary="presentation checked",
                reason="send concrete obstruction for verification",
            )
        )
        self.assertTrue(
            any("Unresolved reading obligations" in error for error in result.errors),
            result.errors,
        )

    def test_accepts_final_proof_ready_when_no_missing_evidence(self):
        result = proof_review_lint.lint_text(
            proof_review(
                status="FINAL_PROOF_READY",
                proof_missing="NONE",
                reason="proof route is complete and ready for final verification",
            )
        )
        self.assertEqual([], result.errors)

    def test_rejects_final_proof_ready_with_missing_evidence(self):
        result = proof_review_lint.lint_text(
            proof_review(
                status="FINAL_PROOF_READY",
                proof_missing="definition is missing",
                reason="proof seems close",
            )
        )
        self.assertTrue(
            any("Missing evidence" in error for error in result.errors),
            result.errors,
        )

    def test_rejects_final_proof_ready_with_omitted_missing_evidence_field(self):
        text = proof_review(
            status="FINAL_PROOF_READY",
            proof_missing="NONE",
            reason="proof route is complete and ready for final verification",
        )
        text = text.replace("- Missing evidence, if any: NONE\n", "")
        result = proof_review_lint.lint_text(text)
        self.assertTrue(
            any("Missing evidence, if any" in error for error in result.errors),
            result.errors,
        )


if __name__ == "__main__":
    unittest.main()
