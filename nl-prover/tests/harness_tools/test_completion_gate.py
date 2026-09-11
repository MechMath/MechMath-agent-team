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

    def test_warns_on_pending_proof_marker(self):
        """Process-language findings advise, they do not block (ADR 0023 P.1).

        The regex cannot distinguish an honest note that a step is unfinished
        from a false claim that it is finished, and the two mistakes cost very
        differently: a miss is one uncaught line, a false positive blocks a
        correct route.
        """
        temp, root = self.make_workspace()
        with temp:
            (root / "proof.tex").write_text("\\sorry{}\n", encoding="utf-8")
            result = completion_gate.lint_workspace(root)
        self.assertTrue(any("pending proof marker" in w for w in result.warnings))
        self.assertFalse(any("pending proof marker" in e for e in result.errors))

    def test_warns_on_process_gap_final_proof(self):
        temp, root = self.make_workspace()
        with temp:
            (root / "proof.tex").write_text(
                "\\begin{theorem}T\\end{theorem}\n"
                "\\begin{proof}The route is unavailable, so gap found.\\end{proof}\n",
                encoding="utf-8",
            )
            result = completion_gate.lint_workspace(root)
        self.assertTrue(
            any("result contract" in w for w in result.warnings)
            or any("result contract" in e for e in result.errors)
        )

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


class LemmaReconciliationTests(unittest.TestCase):
    """lemmas/ on disk versus the Lemma Status table.

    Four runs shipped a proof.pdf at phase `complete` over lemma directories
    holding only a statement.md, because every existing check read STATUS.md and
    proof.tex and none listed the directory. STATUS.md was internally consistent
    in each case, so only the filesystem can report the omission.
    """

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

    def test_no_lemmas_directory_is_a_no_op(self):
        """Statements live in sketch/refined_lemmas/ in some runs. The check does
        not go hunting; it reports that it had nothing to reconcile."""
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = Path(temp.name)
            (root / "proof.tex").write_text(
                "\\begin{theorem}T\\end{theorem}\\begin{proof}Done.\\end{proof}\n",
                encoding="utf-8",
            )
            (root / "STATUS.md").write_text(status(), encoding="utf-8")
            result = completion_gate.lint_workspace(root)
        self.assertEqual("absent", result.lemma_reconciliation["lemmas_dir"])
        self.assertEqual(0, result.lemma_reconciliation["directories"])
        self.assertFalse(any("not accounted for" in e for e in result.errors))

    def test_matching_directory_and_row_reconcile(self):
        temp, root = self.make_workspace()
        with temp:
            result = completion_gate.lint_workspace(root)
        self.assertEqual([], result.errors)
        self.assertEqual(
            {
                "lemmas_dir": "present",
                "directories": 1,
                "status_rows": 1,
                "unaccounted": 0,
                "superseded": 0,
                "rows_without_directory": 0,
            },
            result.lemma_reconciliation,
        )

    def test_rejects_directory_absent_from_status(self):
        temp, root = self.make_workspace()
        with temp:
            (root / "lemmas" / "orphan_route").mkdir()
            (root / "lemmas" / "orphan_route" / "statement.md").write_text(
                "# Lemma\nA statement nobody proved.\n", encoding="utf-8"
            )
            result = completion_gate.lint_workspace(root)
        self.assertTrue(
            any("lemmas/orphan_route/ is not accounted for" in e for e in result.errors),
            result.errors,
        )
        self.assertEqual(1, result.lemma_reconciliation["unaccounted"])

    def test_accepts_directory_declared_superseded_with_a_reason(self):
        temp, root = self.make_workspace()
        with temp:
            (root / "lemmas" / "orphan_route").mkdir()
            (root / "STATUS.md").write_text(
                status()
                + "\n## Superseded Lemma Directories\n"
                "- orphan_route — the covering argument replaced this decomposition\n",
                encoding="utf-8",
            )
            result = completion_gate.lint_workspace(root)
        self.assertEqual([], result.errors)
        self.assertEqual(0, result.lemma_reconciliation["unaccounted"])
        self.assertEqual(1, result.lemma_reconciliation["superseded"])

    def test_rejects_superseded_entry_without_a_reason(self):
        """A bare name reads as "I noticed this directory", not as a disposition."""
        temp, root = self.make_workspace()
        with temp:
            (root / "lemmas" / "orphan_route").mkdir()
            (root / "STATUS.md").write_text(
                status() + "\n## Superseded Lemma Directories\n- orphan_route\n",
                encoding="utf-8",
            )
            result = completion_gate.lint_workspace(root)
        self.assertTrue(
            any("needs a reason" in e for e in result.errors), result.errors
        )
        # Still accounted for: reporting the same bullet twice blames it twice.
        self.assertFalse(any("not accounted for" in e for e in result.errors))

    def test_warns_on_status_row_with_no_directory(self):
        """A warning, not an error: one run's 17 rows against 6 directories are
        sub-steps refined under sketch/refined_lemmas/, which is legitimate."""
        temp, root = self.make_workspace()
        with temp:
            (root / "STATUS.md").write_text(
                status().replace(
                    "| lem:test | - | verified",
                    "| lem:test | - | verified | 1/3 | PASS |"
                    " lemmas/lem:test/verifier/review_packet_v1.md |\n"
                    "| refined-elsewhere | - | verified",
                ),
                encoding="utf-8",
            )
            result = completion_gate.lint_workspace(root)
        self.assertTrue(
            any("names no lemmas/refined-elsewhere/ directory" in w for w in result.warnings),
            result.warnings,
        )
        self.assertFalse(any("refined-elsewhere" in e for e in result.errors), result.errors)
        self.assertEqual(1, result.lemma_reconciliation["rows_without_directory"])

    def test_summary_label_row_is_not_reported_as_missing_a_directory(self):
        temp, root = self.make_workspace()
        with temp:
            (root / "STATUS.md").write_text(
                status().replace("| lem:test |", "| Global terminal proof |"),
                encoding="utf-8",
            )
            result = completion_gate.lint_workspace(root)
        self.assertEqual(0, result.lemma_reconciliation["rows_without_directory"])
        self.assertFalse(any("names no lemmas/" in w for w in result.warnings))

    def test_rejects_empty_lemma_table_when_lemma_directories_exist(self):
        """Statements on disk with nothing tracking them is the shipped-with-no-
        verdicts failure; the same empty table over an empty workspace is not."""
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
            any(
                "no parseable Lemma Status rows but lemmas/ contains" in e
                for e in result.errors
            ),
            result.errors,
        )

    def test_empty_lemma_table_without_lemma_directories_stays_a_warning(self):
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = Path(temp.name)
            (root / "proof.tex").write_text(
                "\\begin{theorem}T\\end{theorem}\\begin{proof}Done.\\end{proof}\n",
                encoding="utf-8",
            )
            (root / "STATUS.md").write_text(
                "# Proof Status: sample\n\n"
                "## Phase\ncomplete\n\n"
                "## Lemma Status\nNONE\n\n"
                "## Open Proof Obligations\nNONE\n",
                encoding="utf-8",
            )
            result = completion_gate.lint_workspace(root)
        self.assertTrue(
            any(w.endswith("no parseable Lemma Status rows") for w in result.warnings),
            result.warnings,
        )
        self.assertFalse(any("parseable Lemma Status rows" in e for e in result.errors))

class TrackingDialectTests(unittest.TestCase):
    """One error naming the dialect, not one error per directory.

    Census of 54 STATUS.md in the corpus: 6 carry only `## Lemma Status`, 18
    only `## Active Branch Queue`, 22 both, 8 neither; 19 have lemma
    directories and no Lemma Status section. On the newest run that produced
    ~25 errors carrying one fact.
    """

    def make_workspace(self, status_text, *lemma_names):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "STATUS.md").write_text(status_text, encoding="utf-8")
        for name in lemma_names:
            directory = root / "lemmas" / name
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "statement.md").write_text("# s\n", encoding="utf-8")
        return root

    def run_both(self, root):
        sections = completion_gate.read_sections(
            (root / "STATUS.md").read_text(encoding="utf-8")
        )
        dialect = completion_gate.tracking_dialect(sections)
        directories = completion_gate.lemma_directories(root)
        result = completion_gate.GateResult()
        completion_gate.validate_lemma_rows(
            result,
            workspace=root,
            lemma_section=sections.get(completion_gate.canonical("Lemma Status"), ""),
            has_lemma_directories=bool(directories),
            dialect=dialect,
            directory_count=len(directories),
        )
        completion_gate.validate_lemma_reconciliation(
            result,
            workspace=root,
            lemma_section=sections.get(completion_gate.canonical("Lemma Status"), ""),
            superseded_section="",
            dialect=dialect,
        )
        return result

    def test_branch_queue_over_many_lemmas_gives_one_error_carrying_the_count(self):
        root = self.make_workspace(
            "# s\n\n## Active Branch Queue\n\n| Rank |\n|---|\n| 1 |\n", "a", "b", "c"
        )
        result = self.run_both(root)
        self.assertEqual(1, len(result.errors))
        self.assertIn("Active Branch Queue", result.errors[0])
        self.assertIn("3 lemma directories", result.errors[0])
        self.assertEqual(3, result.lemma_reconciliation["cascade_suppressed"])

    def test_neither_dialect_says_so_rather_than_naming_a_table(self):
        result = self.run_both(self.make_workspace("# s\n\n## Target\n\nX\n", "a"))
        self.assertEqual(1, len(result.errors))
        self.assertIn("neither", result.errors[0])
        self.assertIn("1 lemma directory is", result.errors[0])

    def test_lemma_status_dialect_still_reports_per_directory(self):
        """The cascade is right when there IS a table and a row is missing."""
        root = self.make_workspace(
            "# s\n\n## Lemma Status\n\n| Lemma | Status |\n|---|---|\n| a | PASS |\n",
            "a",
            "b",
        )
        result = self.run_both(root)
        self.assertTrue(any("lemmas/b/ is not accounted for" in e for e in result.errors))
        self.assertNotIn("cascade_suppressed", result.lemma_reconciliation)

    def test_no_lemma_directories_is_a_warning_not_an_error(self):
        result = self.run_both(self.make_workspace("# s\n\n## Active Branch Queue\n\n| r |\n"))
        self.assertEqual([], result.errors)

    def test_missing_phase_section_says_what_to_write(self):
        result = completion_gate.GateResult()
        completion_gate.validate_phase(result, {})
        self.assertEqual(1, len(result.errors))
        self.assertIn("## Phase", result.errors[0])


if __name__ == "__main__":
    unittest.main()
