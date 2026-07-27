import importlib.util
import contextlib
import io
from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "cli_tools"))
from _gate import review_packet as review_packet_lint


def packet(
    *,
    verdict="PASS",
    next_action="MERGE",
    load_status="resolved",
    adversarial_blockers="NONE",
    include_adversarial=True,
    include_obstruction_audit=False,
    obstruction_process="NO",
    open_obligations="NONE",
    blocking="NONE",
    uncertainty="NONE",
    external="ran; raw files: verifier/external.json",
):
    adversarial_snapshot = "- Adversarial route audit: PASS\n" if include_adversarial else ""
    adversarial_section = (
        "\n## Adversarial Route Audit\n"
        "- Target polarity: implication\n"
        "- Opposite-polarity examples or obstructions considered: NONE\n"
        "- Global compatibility checks: NONE NEEDED\n"
        "- Known theorem or invariant collisions checked: NONE FOUND\n"
        f"- Unresolved adversarial blockers: {adversarial_blockers}\n"
        if include_adversarial
        else ""
    )
    obstruction_section = (
        "\n## Target Obstruction Audit\n"
        "- Obstruction kind: concrete counterexample\n"
        "- Object and hypotheses audit: object satisfies the original hypotheses\n"
        "- Conclusion failure: target conclusion fails for the object\n"
        "- Accepted reading challenge: accepted definitions and conventions checked\n"
        "- Boundary and degenerate variants checked: variants checked under accepted conventions\n"
        f"- Process-failure dependence: {obstruction_process}\n"
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
- Verdict: {verdict}
- Score: 1
- Statement preservation: PASS
- Problem-reading audit: PASS
- Hypotheses/preconditions audit: PASS
- Proof-obligation classification: PASS
- Definition/notation audit: PASS
- Source theorem audit: PASS
{adversarial_snapshot.rstrip()}
- External cross-verification: {external}

## Blocking Issues
{blocking}

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
| main implication | final bridge | proof step 4 | YES | {load_status} |
{adversarial_section}{obstruction_section}

## Open Proof Obligations
{open_obligations}

## Uncertainty
{uncertainty}

## Next Action
{next_action}
"""


class ReviewPacketLintTests(unittest.TestCase):
    def test_accepts_complete_lemma_pass_packet(self):
        result = review_packet_lint.lint_text(packet(), mode="lemma")
        self.assertEqual([], result.errors)

    def test_rejects_assigned_ledger_row_in_lemma_pass(self):
        result = review_packet_lint.lint_text(
            packet(load_status="assigned"), mode="lemma"
        )
        self.assertTrue(
            any("assigned" in error for error in result.errors), result.errors
        )

    def test_allows_assigned_ledger_row_in_plan_pass(self):
        result = review_packet_lint.lint_text(
            packet(
                next_action="PROCEED_WITH_PLAN",
                load_status="assigned",
                open_obligations=(
                    "| Obligation | Owner | Status |\n"
                    "|------------|-------|--------|\n"
                    "| prove local bound | lem:bound | assigned |"
                ),
            ),
            mode="plan",
        )
        self.assertEqual([], result.errors)

    def test_rejects_missing_external_status_in_pass_packet(self):
        result = review_packet_lint.lint_text(packet(external="TODO"), mode="lemma")
        self.assertTrue(
            any("External cross-verification" in error for error in result.errors),
            result.errors,
        )

    def test_rejects_pass_packet_without_adversarial_audit(self):
        result = review_packet_lint.lint_text(
            packet(include_adversarial=False), mode="lemma"
        )
        self.assertTrue(
            any("Adversarial Route Audit" in error for error in result.errors),
            result.errors,
        )

    def test_rejects_pass_packet_with_unresolved_adversarial_blocker(self):
        result = review_packet_lint.lint_text(
            packet(adversarial_blockers="boundary case not checked"),
            mode="lemma",
        )
        self.assertTrue(
            any("Unresolved adversarial blockers" in error for error in result.errors),
            result.errors,
        )

    def test_accepts_obstruction_packet_with_target_obstruction_audit(self):
        result = review_packet_lint.lint_text(
            packet(
                next_action="ACCEPT_OBSTRUCTION",
                include_obstruction_audit=True,
            ),
            mode="obstruction",
        )
        self.assertEqual([], result.errors)

    def test_rejects_obstruction_packet_without_target_obstruction_audit(self):
        result = review_packet_lint.lint_text(
            packet(next_action="ACCEPT_OBSTRUCTION"),
            mode="obstruction",
        )
        self.assertTrue(
            any("Target Obstruction Audit" in error for error in result.errors),
            result.errors,
        )

    def test_rejects_obstruction_packet_depending_on_process_failure(self):
        result = review_packet_lint.lint_text(
            packet(
                next_action="ACCEPT_OBSTRUCTION",
                include_obstruction_audit=True,
                obstruction_process="YES, source theorem is missing",
            ),
            mode="obstruction",
        )
        self.assertTrue(
            any("Process-failure dependence" in error for error in result.errors),
            result.errors,
        )

    def test_rejects_revision_packet_without_route_detail(self):
        result = review_packet_lint.lint_text(
            packet(
                verdict="NEEDS_REVISION",
                next_action="REVISE_PROOF",
                load_status="open",
            ),
            mode="lemma",
        )
        self.assertTrue(
            any("blocker, obligation, or uncertainty" in error for error in result.errors),
            result.errors,
        )

    def test_structural_mode_is_not_a_cli_choice(self):
        parser = review_packet_lint.build_parser()
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args(["review_packet.md", "--mode", "structural"])


if __name__ == "__main__":
    unittest.main()
