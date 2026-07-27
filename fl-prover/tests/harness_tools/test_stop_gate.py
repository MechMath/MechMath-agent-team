"""Stop gate (ADR 0022): the run-end write-back must be mechanical at every stop."""

import os
from pathlib import Path
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "cli_tools"))
from _gate import stop as stop_gate


class StopGateTests(unittest.TestCase):
    def make_workspace(self, *, verified_proof=False):
        """A workspace that satisfies every stop-gate check, so each test can
        break exactly one thing."""
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "STATUS.md").write_text("# Proof Status\n\n## Phase\nprove\n", encoding="utf-8")
        mem = root / "memory"
        mem.mkdir()
        (mem / "index.json").write_text('{"channels": {}}\n', encoding="utf-8")
        (mem / ".longterm_read.json").write_text('{"read_at_utc": "2026-07-26T00:00:00Z"}\n', encoding="utf-8")
        if verified_proof:
            (root / "proof.pdf").write_text("pdf\n", encoding="utf-8")
        else:
            writer = root / "writer"
            writer.mkdir()
            (writer / "progress_notes.tex").write_text("notes\n", encoding="utf-8")
            (root / "progress_notes.pdf").write_text("pdf\n", encoding="utf-8")
        return temp, root

    def test_clean_workspace_passes(self):
        temp, root = self.make_workspace()
        with temp:
            result = stop_gate.lint_workspace(root)
        self.assertEqual([], result.errors)

    def test_missing_local_index_blocks_stop(self):
        # A run that never sedimented its routes and dead ends has nothing to
        # hand the next run; the completion gate skips this case entirely.
        temp, root = self.make_workspace()
        with temp:
            (root / "memory" / "index.json").unlink()
            result = stop_gate.lint_workspace(root)
        self.assertTrue(any("no local memory index" in e for e in result.errors))

    def test_missing_longterm_read_trace_is_an_error_not_a_warning(self):
        temp, root = self.make_workspace()
        with temp:
            (root / "memory" / ".longterm_read.json").unlink()
            result = stop_gate.lint_workspace(root)
        self.assertTrue(any("long-term-memory read trace" in e for e in result.errors))

    def test_recorded_failures_without_a_captured_lesson_block_stop(self):
        temp, root = self.make_workspace()
        with temp:
            (root / "memory" / "failed_paths.jsonl").write_text(
                '{"channel":"failed_paths","summary":"route died"}\n', encoding="utf-8"
            )
            result = stop_gate.lint_workspace(root)
        self.assertTrue(any("no candidate" in e for e in result.errors))

    def test_no_constraint_marker_satisfies_the_lesson_requirement(self):
        # The escape hatch must be cheap: a failure with no transferable lesson
        # is recorded as such rather than left silent.
        temp, root = self.make_workspace()
        with temp:
            (root / "memory" / "failed_paths.jsonl").write_text(
                '{"channel":"failed_paths","summary":"route died"}\n', encoding="utf-8"
            )
            cand = root / "memory" / "candidates"
            cand.mkdir()
            (cand / "regulator-run1.jsonl").write_text(
                '{"no_constraint":"arithmetic slip, nothing transferable"}\n', encoding="utf-8"
            )
            result = stop_gate.lint_workspace(root)
        self.assertEqual([], result.errors)

    def test_unaggregated_candidates_block_stop(self):
        temp, root = self.make_workspace()
        with temp:
            cand = root / "memory" / "candidates"
            cand.mkdir()
            (cand / "regulator-run1.jsonl").write_text(
                '{"kind":"negative-constraint","statement":"do not X","trigger":"t"}\n',
                encoding="utf-8",
            )
            result = stop_gate.lint_workspace(root)
        self.assertTrue(any("not aggregated" in e for e in result.errors))

    def test_aggregated_candidates_must_be_promoted_to_the_long_term_tier(self):
        temp, root = self.make_workspace()
        with temp:
            cand = root / "memory" / "candidates"
            cand.mkdir()
            card = '{"kind":"negative-constraint","statement":"do not X","trigger":"t"}\n'
            (cand / "regulator-run1.jsonl").write_text(card, encoding="utf-8")
            (root / "memory" / "candidates_aggregated.jsonl").write_text(card, encoding="utf-8")
            missing = stop_gate.lint_workspace(root)
            (root / "memory" / "candidates_promoted.json").write_text('{"promoted": []}\n', encoding="utf-8")
            present = stop_gate.lint_workspace(root)
        self.assertTrue(any("not promoted into the long-term tier" in e for e in missing.errors))
        self.assertEqual([], present.errors)

    def test_non_proof_stop_requires_progress_notes(self):
        # ADR 0021 made this mandatory; ADR 0022 makes it mechanical.
        temp, root = self.make_workspace()
        with temp:
            (root / "progress_notes.pdf").unlink()
            result = stop_gate.lint_workspace(root)
        self.assertTrue(any("progress_notes.pdf" in e for e in result.errors))

    def test_verified_proof_stop_requires_proof_pdf(self):
        temp, root = self.make_workspace(verified_proof=True)
        with temp:
            self.assertEqual([], stop_gate.lint_workspace(root, verified_proof=True).errors)
            (root / "proof.pdf").unlink()
            result = stop_gate.lint_workspace(root, verified_proof=True)
        self.assertTrue(any("without proof.pdf" in e for e in result.errors))

    def test_completion_gate_keeps_its_softer_classification(self):
        # ADR 0022 escalates only at the stop gate; `gate complete` must not
        # retro-block runs that predate this rule.
        from _gate import completion as completion_gate

        temp, root = self.make_workspace()
        with temp:
            (root / "memory" / ".longterm_read.json").unlink()
            result = completion_gate.GateResult()
            completion_gate.validate_longterm_read(result, root)
        self.assertEqual([], result.errors)
        self.assertTrue(any("long-term-memory read trace" in w for w in result.warnings))


if __name__ == "__main__":
    unittest.main()
