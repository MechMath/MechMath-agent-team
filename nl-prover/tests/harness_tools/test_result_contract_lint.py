import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "cli_tools"))
from _gate import result_contract as result_contract_lint


def proof_tex(main_body: str, problem_body: str = "Prove the theorem.") -> str:
    return f"""\\documentclass{{article}}
\\begin{{document}}
\\section{{Problem Statement}}
{problem_body}

\\section{{Main Results}}
\\begin{{theorem}}T\\end{{theorem}}
\\begin{{proof}}
{main_body}
\\end{{proof}}
\\end{{document}}
"""


def obstruction_packet(*, evidence=True):
    if evidence:
        ledger = (
            "| concrete counterexample | obstruction | object satisfies original "
            "hypotheses and target conclusion fails | YES | resolved |"
        )
        conclusion = "target conclusion fails for the object"
        process = "NO"
    else:
        ledger = "| main assertion | final bridge | proof step | YES | resolved |"
        conclusion = "not checked"
        process = "YES, proof route was missing"
    return f"""# Review Packet: obstruction (v1)

## Inputs Checked
- Problem: problem.md
- Statement: problem.md
- Proof: proof.tex
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
- External cross-verification: unavailable

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
- Specialized definitions used: accepted definitions from problem context
- Source theorem warrant: PASS
- Circularity check: PASS

## Load-Bearing Obligation Ledger
| Obligation | Type | Where supplied or assigned | Preconditions checked | Status |
|------------|------|----------------------------|-----------------------|--------|
{ledger}

## Adversarial Route Audit
- Target polarity: obstruction
- Opposite-polarity examples or obstructions considered: checked against accepted reading
- Global compatibility checks: boundary and degenerate cases checked
- Known theorem or invariant collisions checked: NONE FOUND
- Unresolved adversarial blockers: NONE

## Target Obstruction Audit
- Obstruction kind: concrete counterexample
- Object and hypotheses audit: object satisfies the original hypotheses
- Conclusion failure: {conclusion}
- Accepted reading challenge: accepted definitions and conventions checked
- Boundary and degenerate variants checked: variants checked under accepted conventions
- Process-failure dependence: {process}

## Open Proof Obligations
NONE

## Uncertainty
NONE

## Next Action
ACCEPT_OBSTRUCTION
"""


class ResultContractLintTests(unittest.TestCase):
    def make_workspace(self, proof_body: str, problem_body: str = "Prove the theorem."):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "proof.tex").write_text(
            proof_tex(proof_body, problem_body=problem_body),
            encoding="utf-8",
        )
        return temp, root

    def test_accepts_final_proof_without_process_failure(self):
        temp, root = self.make_workspace("Therefore the theorem follows.")
        with temp:
            result = result_contract_lint.lint_workspace(root)
        self.assertEqual([], result.errors)

    def test_rejects_process_gap_in_result_body(self):
        temp, root = self.make_workspace("The source theorem is missing, so gap found.")
        with temp:
            result = result_contract_lint.lint_workspace(root)
        self.assertTrue(any("gap/process-gap" in error for error in result.errors))

    def test_rejects_unresolved_case_in_result_body(self):
        temp, root = self.make_workspace(
            "The generic case follows. The boundary case remains unresolved."
        )
        with temp:
            result = result_contract_lint.lint_workspace(root)
        self.assertTrue(
            any("unresolved case claim" in error for error in result.errors),
            result.errors,
        )

    def test_rejects_terminal_false_claim_without_obstruction_packet(self):
        temp, root = self.make_workspace(
            "Thus the target assertion is false under the stated hypotheses."
        )
        with temp:
            result = result_contract_lint.lint_workspace(root)
        self.assertTrue(
            any("uncertified target false" in error for error in result.errors),
            result.errors,
        )
        self.assertEqual(1, len(result.terminal_obstruction_claims))

    def test_ignores_problem_statement_language(self):
        temp, root = self.make_workspace(
            "Therefore the theorem follows.",
            problem_body="Find whether a gap found claim can be justified.",
        )
        with temp:
            result = result_contract_lint.lint_workspace(root)
        self.assertEqual([], result.errors)

    def test_accepts_positive_obstruction_packet(self):
        temp, root = self.make_workspace(
            "Thus the target assertion is false under the stated hypotheses."
        )
        with temp:
            packet_path = root / "review_packet.md"
            packet_path.write_text(obstruction_packet(), encoding="utf-8")
            result = result_contract_lint.lint_workspace(
                root,
                extra_packets=[Path("review_packet.md")],
            )
        self.assertEqual([], result.errors)
        self.assertEqual([str(packet_path)], result.obstruction_packets)

    def test_rejects_obstruction_packet_with_bad_target_obstruction_audit(self):
        temp, root = self.make_workspace(
            "Thus the target assertion is false under the stated hypotheses."
        )
        with temp:
            packet_path = root / "review_packet.md"
            packet_path.write_text(obstruction_packet(evidence=False), encoding="utf-8")
            result = result_contract_lint.lint_workspace(
                root,
                extra_packets=[Path("review_packet.md")],
            )
        self.assertTrue(
            any("Process-failure dependence" in error for error in result.errors),
            result.errors,
        )


if __name__ == "__main__":
    unittest.main()
