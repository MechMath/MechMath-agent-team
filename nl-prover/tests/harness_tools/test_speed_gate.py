"""Speed gate (ADR 0024): a run must be able to report what it cost itself.

The metrics here are chosen to be problem-independent. A harder problem makes a
run longer; it does not make a later version of a document reproduce an earlier
one, and it does not make `STATUS.md` accumulate closed rows. So each test fixes
a *shape* and asserts the number that shape must produce, never a wall-clock.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "cli_tools"))
from _gate import speed as speed_gate


class SpeedGateTests(unittest.TestCase):
    def make_workspace(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "STATUS.md").write_text("# Proof Status\n", encoding="utf-8")
        (root / "problem.md").write_text("# Problem\n", encoding="utf-8")
        return root

    def write_versions(self, root, lemma, sizes, kind="generator", stem="proof"):
        directory = root / "lemmas" / lemma / kind
        directory.mkdir(parents=True, exist_ok=True)
        for index, size in enumerate(sizes, start=1):
            (directory / f"{stem}_v{index}.md").write_text("x" * size, encoding="utf-8")
        return directory

    # --- rewrite waste -----------------------------------------------------

    def test_single_version_family_is_not_waste(self):
        """One version is the product, not a rewrite. It must not be counted."""
        root = self.make_workspace()
        self.write_versions(root, "lem_a", [1000])
        result = speed_gate.lint_workspace(root)
        self.assertEqual(result.metrics["families"], 0)
        self.assertEqual(result.metrics["rewrite_waste_ratio"], 0.0)

    def test_waste_is_the_superseded_fraction(self):
        """Three equal versions: two of the three were paid for and discarded."""
        root = self.make_workspace()
        self.write_versions(root, "lem_a", [1000, 1000, 1000])
        result = speed_gate.lint_workspace(root)
        self.assertEqual(result.metrics["bytes_written"], 3000)
        self.assertEqual(result.metrics["bytes_final"], 1000)
        self.assertAlmostEqual(result.metrics["rewrite_waste_ratio"], 2 / 3, places=3)

    def test_re_emission_loop_is_flagged(self):
        """The measured shape: 11 versions of one lemma, each larger than the last."""
        root = self.make_workspace()
        self.write_versions(root, "lem_big", [66000 + 9000 * i for i in range(11)])
        result = speed_gate.lint_workspace(root)
        self.assertGreater(result.metrics["rewrite_waste_ratio"], 0.8)
        self.assertTrue(
            any("re-emitting" in w for w in result.warnings),
            f"expected a rewrite-waste warning, got {result.warnings}",
        )

    def test_repair_loop_is_not_flagged(self):
        """The behaviour P1 asks for: many revisions, but the document stays put.

        This is the test that keeps the gate honest — it must not simply punish
        revision count, or it would push against verification.
        """
        root = self.make_workspace()
        self.write_versions(root, "lem_ok", [100000, 100500, 100200, 100600])
        result = speed_gate.lint_workspace(root, waste_ratio=0.8)
        self.assertFalse(
            any("re-emitting" in w for w in result.warnings),
            f"a repair loop must not trip the waste warning: {result.warnings}",
        )

    # --- accretion ---------------------------------------------------------

    def test_monotone_growth_is_reported(self):
        root = self.make_workspace()
        self.write_versions(root, "lem_grow", [1000, 2000, 3000, 4000])
        result = speed_gate.lint_workspace(root)
        families = [f["family"] for f in result.metrics["monotone_growth_families"]]
        self.assertEqual(len(families), 1)
        self.assertIn("lem_grow", families[0])

    def test_shrinking_family_is_not_growth(self):
        root = self.make_workspace()
        self.write_versions(root, "lem_shrink", [4000, 3000, 2000])
        result = speed_gate.lint_workspace(root)
        self.assertEqual(result.metrics["monotone_growth_families"], [])

    def test_two_versions_is_not_yet_a_trend(self):
        """Growth needs at least three points; two is noise, not accretion."""
        root = self.make_workspace()
        self.write_versions(root, "lem_two", [1000, 2000])
        result = speed_gate.lint_workspace(root)
        self.assertEqual(result.metrics["monotone_growth_families"], [])

    # --- required-read set -------------------------------------------------

    def test_required_read_counts_status_and_problem(self):
        root = self.make_workspace()
        (root / "STATUS.md").write_text("s" * 5000, encoding="utf-8")
        (root / "problem.md").write_text("p" * 1000, encoding="utf-8")
        result = speed_gate.lint_workspace(root)
        self.assertEqual(result.metrics["required_read_bytes"], 6000)

    def test_only_the_latest_review_packet_counts(self):
        """The cookbook says *latest* packets. Counting superseded ones would
        double-count them into the waste metric, which measures something else."""
        root = self.make_workspace()
        self.write_versions(
            root, "lem_a", [1000, 2000, 3000], kind="verifier", stem="review_packet"
        )
        result = speed_gate.lint_workspace(root)
        breakdown = result.metrics["required_read_breakdown"]
        packets = {k: v for k, v in breakdown.items() if "review_packet" in k}
        self.assertEqual(list(packets.values()), [3000])
        self.assertIn("review_packet_v3.md", next(iter(packets)))

    def test_budget_warning_names_the_biggest_file(self):
        root = self.make_workspace()
        (root / "STATUS.md").write_text("s" * 70000, encoding="utf-8")
        result = speed_gate.lint_workspace(root, read_budget_kb=60)
        self.assertTrue(any("STATUS.md" in w and "budget" in w for w in result.warnings))

    def test_references_are_inputs_not_products(self):
        """`references/` holds papers the run read, not artifacts it wrote."""
        root = self.make_workspace()
        papers = root / "references" / "papers"
        papers.mkdir(parents=True)
        (papers / "note_v1.md").write_text("x" * 10000, encoding="utf-8")
        (papers / "note_v2.md").write_text("x" * 10000, encoding="utf-8")
        result = speed_gate.lint_workspace(root)
        self.assertEqual(result.metrics["families"], 0)

    # --- observed concurrency (ADR 0024 §5 case A) -------------------------

    def land_generator(self, root, lemma, offset_s):
        import os

        directory = root / "lemmas" / lemma / "generator"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "proof_v1.md"
        path.write_text("proof\n", encoding="utf-8")
        base = 1_700_000_000
        os.utime(path, (base + offset_s, base + offset_s))

    def test_a_batch_that_lands_together_reads_as_concurrent(self):
        """Case A: N independent lemmas dispatched as one batch land together."""
        root = self.make_workspace()
        for i in range(6):
            self.land_generator(root, f"lem_{i}", i * 30)
        result = speed_gate.lint_workspace(root)
        self.assertEqual(result.metrics["observed_concurrency"], 6)
        self.assertFalse(any("one at a time" in w for w in result.warnings))

    def test_serial_dispatch_is_caught(self):
        """The failure it exists to catch: same lemmas, 30 minutes apart."""
        root = self.make_workspace()
        for i in range(6):
            self.land_generator(root, f"lem_{i}", i * 1800)
        result = speed_gate.lint_workspace(root)
        self.assertEqual(result.metrics["observed_concurrency"], 1)
        self.assertTrue(any("one at a time" in w for w in result.warnings))

    def test_dispatch_windows_beat_lemma_mtimes(self):
        """A one-lemma run cannot show concurrency in lemma landings, but its
        specialists can still overlap. Measured on `testprime`: mtimes said 1,
        the dispatch log said 4, and the human had watched the 4 happen."""
        root = self.make_workspace()
        self.land_generator(root, "lem_only", 0)
        (root / "logs").mkdir(exist_ok=True)
        windows = [("15:47", "16:00"), ("15:47", "15:55"), ("15:48", "15:54"), ("15:51", "15:59")]
        (root / "logs" / "dispatch.jsonl").write_text(
            "".join(
                json.dumps(
                    {
                        "role": "verifier",
                        "started": f"2026-08-15T{begin}:00Z",
                        "ended": f"2026-08-15T{end}:00Z",
                        "batch": "serial",
                    }
                )
                + "\n"
                for begin, end in windows
            ),
            encoding="utf-8",
        )
        result = speed_gate.lint_workspace(root)
        self.assertEqual(result.metrics["observed_concurrency"], 4)
        self.assertEqual(result.metrics["concurrency_source"], "dispatch log")
        # `batch: "serial"` means "sent individually", not "ran alone". (The A3
        # batch-spread warning uses the same phrase and is a separate finding,
        # so match the concurrency warning specifically.)
        self.assertFalse(
            any("nothing ever overlapped" in w for w in result.warnings)
        )

    def test_touching_windows_do_not_overlap(self):
        root = self.make_workspace()
        (root / "logs").mkdir(exist_ok=True)
        (root / "logs" / "dispatch.jsonl").write_text(
            json.dumps({"role": "a", "started": "2026-08-15T10:00:00Z",
                        "ended": "2026-08-15T10:10:00Z"}) + "\n"
            + json.dumps({"role": "b", "started": "2026-08-15T10:10:00Z",
                          "ended": "2026-08-15T10:20:00Z"}) + "\n",
            encoding="utf-8",
        )
        result = speed_gate.lint_workspace(root)
        self.assertEqual(result.metrics["observed_concurrency"], 1)
        self.assertTrue(any("nothing ever overlapped" in w for w in result.warnings))

    def test_a_single_lemma_is_not_a_concurrency_failure(self):
        """One lemma cannot be batched with anything. Must not warn."""
        root = self.make_workspace()
        self.land_generator(root, "lem_only", 0)
        result = speed_gate.lint_workspace(root)
        self.assertFalse(any("one at a time" in w for w in result.warnings))

    def test_impossible_concurrency_is_reported_as_unmeasured(self):
        """An archive extraction rewrites every mtime at once. That must read as
        'not measured', never as 'excellent batching'."""
        root = self.make_workspace()
        # Keyed off the constant, not a literal: this test failed the day the
        # declared ceiling was corrected from a stale 6 to the policy's 12,
        # because its fixture landed exactly 12.
        impossible = speed_gate.DECLARED_CONCURRENCY + 8
        for i in range(impossible):
            self.land_generator(root, f"lem_{i}", 0)
        result = speed_gate.lint_workspace(root)
        self.assertGreater(
            result.metrics["observed_concurrency"], speed_gate.DECLARED_CONCURRENCY
        )
        self.assertTrue(any("unmeasured" in w for w in result.warnings))

    # --- status hygiene (ADR 0024 §5 case C) -------------------------------

    def write_status(self, root, body):
        (root / "STATUS.md").write_text(body, encoding="utf-8")

    def test_history_section_is_flagged(self):
        root = self.make_workspace()
        self.write_status(root, "# S\n\n## Phase\nprove\n\n## History\n- [t] did a thing\n")
        result = speed_gate.lint_workspace(root)
        self.assertTrue(result.metrics["status_hygiene"]["has_history_section"])
        self.assertTrue(any("STATUS_history.md" in w for w in result.warnings))

    def test_closed_rows_are_flagged(self):
        root = self.make_workspace()
        self.write_status(
            root,
            "# S\n\n## Active Branch Queue\n"
            "| 1 | a | Explorer | f.md | e | active |\n"
            "| 2 | b | Explorer | g.md | e | rejected |\n"
            "| 3 | c | Explorer | h.md | e | done |\n",
        )
        result = speed_gate.lint_workspace(root)
        self.assertEqual(result.metrics["status_hygiene"]["closed_rows"], 2)
        self.assertTrue(any("STATUS_closed.md" in w for w in result.warnings))

    def test_blocked_rows_stay(self):
        """`blocked` is waiting on a named condition, not finished."""
        root = self.make_workspace()
        self.write_status(root, "# S\n\n| 1 | a | Explorer | f.md | e | blocked |\n")
        result = speed_gate.lint_workspace(root)
        self.assertEqual(result.metrics["status_hygiene"]["closed_rows"], 0)

    def test_template_conformance_is_reported(self):
        root = self.make_workspace()
        self.write_status(
            root,
            "# S\n\n## Problem\nx\n\n## Target Contract\nx\n\n## Phase\nprove\n\n"
            "## Lemma Status\nx\n\n## Open Proof Obligations\nx\n\n## Active Branch Queue\nx\n",
        )
        hygiene = speed_gate.lint_workspace(root).metrics["status_hygiene"]
        self.assertEqual(hygiene["template_sections"], 6)
        self.assertEqual(hygiene["template_total"], 6)

    def test_drift_into_a_narrative_file_is_caught(self):
        """The measured August shape: many ad-hoc sections, almost none of the
        routing shape. This is what the July runs did not do."""
        root = self.make_workspace()
        body = "# S\n\n## Phase\nprove\n\n" + "".join(
            f"## A recurring defect {i}\nprose\n\n" for i in range(15)
        )
        self.write_status(root, body)
        result = speed_gate.lint_workspace(root)
        self.assertTrue(any("drifted into a narrative" in w for w in result.warnings))

    def test_a_conforming_status_does_not_trip_drift(self):
        root = self.make_workspace()
        self.write_status(
            root,
            "# S\n\n## Problem\nx\n\n## Target Contract\nx\n\n## Phase\nprove\n\n"
            "## Lemma Status\nx\n\n## Open Proof Obligations\nx\n\n## Active Branch Queue\nx\n",
        )
        result = speed_gate.lint_workspace(root)
        self.assertFalse(any("drifted" in w for w in result.warnings))

    # --- timing record (ADR 0024 §5 case H) --------------------------------

    def test_run_times_is_no_longer_asked_for(self):
        root = self.make_workspace()
        result = speed_gate.lint_workspace(root)
        self.assertNotIn("has_run_times", result.metrics)
        self.assertFalse(any("RUN_TIMES" in w for w in result.warnings))

    def test_incomplete_dispatch_log_is_caught(self):
        """An incomplete log is worse than none: it makes a floor look measured.
        Every artifact took at least one dispatch, so artifacts bound it below."""
        root = self.make_workspace()
        self.write_versions(root, "lem_a", [1000, 1000, 1000])  # 3 generator artifacts
        (root / "logs").mkdir()
        (root / "logs" / "dispatch.jsonl").write_text('{"role":"generator"}\n', encoding="utf-8")
        result = speed_gate.lint_workspace(root)
        self.assertEqual(result.metrics["dispatch_lines"], 1)
        self.assertEqual(result.metrics["lane_artifacts"], 3)
        self.assertTrue(any("went unlogged" in w for w in result.warnings))

    def test_complete_dispatch_log_is_quiet(self):
        root = self.make_workspace()
        self.write_versions(root, "lem_a", [1000, 1000, 1000])
        (root / "logs").mkdir()
        (root / "logs" / "dispatch.jsonl").write_text(
            '{"role":"generator"}\n' * 3, encoding="utf-8"
        )
        result = speed_gate.lint_workspace(root)
        self.assertFalse(any("went unlogged" in w for w in result.warnings))

    def test_present_dispatch_log_is_quiet(self):
        root = self.make_workspace()
        (root / "logs").mkdir()
        (root / "logs" / "dispatch.jsonl").write_text('{"role":"generator"}\n', encoding="utf-8")
        result = speed_gate.lint_workspace(root)
        self.assertTrue(result.metrics["has_dispatch_log"])
        self.assertFalse(any("RUN_TIMES" in w or "dispatch.jsonl" in w for w in result.warnings))

    # --- gate contract -----------------------------------------------------

    def test_missing_workspace_is_an_error(self):
        result = speed_gate.lint_workspace(Path("/nonexistent-workspace-for-test"))
        self.assertFalse(result.ok)
        self.assertTrue(result.errors)

    def test_reports_but_does_not_block(self):
        """A cost gate that blocks a run is a new way to lose work."""
        root = self.make_workspace()
        self.write_versions(root, "lem_big", [66000 + 9000 * i for i in range(11)])
        self.assertEqual(speed_gate.main([str(root), "--json"]), 0)

    def test_strict_blocks_when_asked(self):
        root = self.make_workspace()
        self.write_versions(root, "lem_big", [66000 + 9000 * i for i in range(11)])
        self.assertEqual(speed_gate.main([str(root), "--json", "--strict"]), 1)

    def test_clean_workspace_passes_strict(self):
        """A workspace is only clean if it also left its timing record behind."""
        root = self.make_workspace()
        (root / "logs").mkdir()
        (root / "logs" / "dispatch.jsonl").write_text('{"role":"generator"}\n', encoding="utf-8")
        self.assertEqual(speed_gate.main([str(root), "--json", "--strict"]), 0)

    def test_registered_in_the_gate_dispatch(self):
        """gate.py enumerates its subcommands in three places with nothing
        checking they agree. This is that check."""
        import gate

        self.assertIn("speed", gate.DISPATCH)
        self.assertIn("speed", gate.USAGE)
        self.assertIn("gate speed", gate.__doc__)

class BatchSpreadTests(unittest.TestCase):
    """ADR 0024 §3.A3: a batch is real iff its landing spread is below one
    agent's median turnaround. This is the criterion the cookbook now states."""

    def make(self, offsets, durations=None):
        import os

        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        base = 1_700_000_000
        if durations:
            (root / "logs").mkdir()
            (root / "logs" / "dispatch.jsonl").write_text(
                "".join(
                    '{"role":"generator","started":"2026-08-10T00:00:00Z",'
                    f'"ended":"2026-08-10T00:{d // 60:02d}:{d % 60:02d}Z"}}\n'
                    for d in durations
                ),
                encoding="utf-8",
            )
        for i, offset in enumerate(offsets):
            d = root / "lemmas" / f"lem_{i}" / "generator"
            d.mkdir(parents=True)
            p = d / "proof_v1.md"
            p.write_text("x\n", encoding="utf-8")
            os.utime(p, (base + offset, base + offset))
        return root

    def test_without_a_dispatch_log_it_is_unmeasured_not_estimated(self):
        """Turnaround cannot come from artifact gaps: when a run is one batch,
        those gaps ARE the batch spread, so the estimate chases its own tail."""
        result = speed_gate.batch_spread(self.make([0, 5, 10, 15, 3000, 6000]))
        self.assertFalse(result["known"])
        self.assertIn("dispatch.jsonl", result["reason"])

    def test_a_real_batch_is_recognised(self):
        # Six lemmas land within 30s; each dispatch took ~5 minutes.
        result = speed_gate.batch_spread(
            self.make([0, 5, 10, 15, 20, 30], durations=[300, 300, 300, 300])
        )
        self.assertTrue(result["known"])
        self.assertTrue(result["concurrent"])
        self.assertEqual(result["widest_real_batch"], 6)

    def test_serial_dispatch_is_not_a_batch(self):
        """Same six lemmas, each landing a full turnaround after the last."""
        result = speed_gate.batch_spread(
            self.make([i * 300 for i in range(6)], durations=[300, 300, 300, 300])
        )
        self.assertTrue(result["known"])
        self.assertEqual(result["widest_real_batch"], 1)
        self.assertFalse(result["concurrent"])

    def test_serial_dispatch_warns(self):
        root = self.make([i * 300 for i in range(6)], durations=[300, 300, 300, 300])
        result = speed_gate.lint_workspace(root)
        self.assertTrue(any("no real batch" in w for w in result.warnings))


class StalledDispatchTests(unittest.TestCase):
    """A dispatch that produced nothing is the expensive kind and the invisible
    kind: the workspace shows a gap, and only the dispatch log shows the cost."""

    def make(self, entries, existing=()):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "STATUS.md").write_text("# S\n", encoding="utf-8")
        (root / "logs").mkdir()
        (root / "logs" / "dispatch.jsonl").write_text(
            "".join(f'{{"role":"generator","target":"{t}"}}\n' for t in entries),
            encoding="utf-8",
        )
        for target in existing:
            path = root / target
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x\n", encoding="utf-8")
        return root

    def test_no_log_means_unknown_not_zero(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.assertFalse(speed_gate.stalled_dispatches(Path(temp.name))["known"])

    def test_missing_target_counts_as_produced_nothing(self):
        root = self.make(["a.md", "b.md", "c.md"], existing=["a.md"])
        result = speed_gate.stalled_dispatches(root)
        self.assertEqual(result["dispatches"], 3)
        self.assertEqual(result["produced_nothing"], 2)

    def test_all_targets_present_is_quiet(self):
        root = self.make(["a.md", "b.md"], existing=["a.md", "b.md"])
        self.assertEqual(speed_gate.stalled_dispatches(root)["produced_nothing"], 0)
        result = speed_gate.lint_workspace(root)
        self.assertFalse(any("produced\nno artifact" in w for w in result.warnings))

    def test_stalls_are_warned_about(self):
        root = self.make(["a.md", "b.md"], existing=["a.md"])
        result = speed_gate.lint_workspace(root)
        self.assertTrue(any("produced" in w and "no artifact" in w for w in result.warnings))


class WindowAttributionTests(unittest.TestCase):
    """Hook-written entries carry no `target` — the hook records the window a
    dispatch ran in and lets mtimes say what landed. The failure this guards
    against is an unattributable log reading as a log with no stalls."""

    def make(self, entries, artifacts=()):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "STATUS.md").write_text("# S\n", encoding="utf-8")
        (root / "logs").mkdir()
        (root / "logs" / "dispatch.jsonl").write_text(
            "".join(json.dumps(entry) + "\n" for entry in entries), encoding="utf-8"
        )
        for name, when in artifacts:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x\n", encoding="utf-8")
            os.utime(path, (when, when))
        return root

    def _at(self, hour, minute):
        return datetime(2026, 8, 14, hour, minute, tzinfo=timezone.utc)

    def _entry(self, start, end):
        return {
            "role": "generator",
            "started": self._at(*start).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ended": self._at(*end).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": "hook",
        }

    def test_artifact_inside_the_window_is_not_a_stall(self):
        root = self.make(
            [self._entry((10, 0), (10, 10))],
            artifacts=[("lemmas/a/generator/proof_v1.md", self._at(10, 5).timestamp())],
        )
        result = speed_gate.stalled_dispatches(root)
        self.assertEqual(result["produced_nothing"], 0)
        self.assertEqual(result["unattributable"], 0)

    def test_empty_window_is_a_stall(self):
        root = self.make(
            [self._entry((10, 0), (10, 10))],
            artifacts=[("lemmas/a/generator/proof_v1.md", self._at(12, 0).timestamp())],
        )
        self.assertEqual(speed_gate.stalled_dispatches(root)["produced_nothing"], 1)

    def test_missing_timestamps_are_unattributable_not_clean(self):
        """The dangerous reading: a log we cannot interpret must not come back
        as `produced_nothing: 0`, which is indistinguishable from a healthy run."""
        root = self.make([{"role": "generator", "source": "hook"}])
        result = speed_gate.stalled_dispatches(root)
        self.assertEqual(result["unattributable"], 1)
        self.assertEqual(result["produced_nothing"], 0)

    def test_duration_unknown_is_not_attributed(self):
        entry = self._entry((10, 0), (10, 10))
        entry["duration_unknown"] = True
        root = self.make(
            [entry],
            artifacts=[("lemmas/a/generator/proof_v1.md", self._at(10, 5).timestamp())],
        )
        self.assertEqual(speed_gate.stalled_dispatches(root)["unattributable"], 1)

    def test_the_dispatch_log_itself_is_never_counted_as_output(self):
        """`logs/` is where the log lives. Counting it would make every dispatch
        look productive, since writing the log is what ends one."""
        root = self.make(
            [self._entry((10, 0), (10, 10))],
            artifacts=[("logs/note.md", self._at(10, 5).timestamp())],
        )
        self.assertEqual(speed_gate.stalled_dispatches(root)["produced_nothing"], 1)


class PlanWidthTests(unittest.TestCase):
    """The Orchestrator dispatches from `sketch/decomposition.md`, so a plan
    that does not say how wide it is gets walked one lemma at a time. Measured
    on four workspaces: the three that stated a frontier reached concurrency
    4, 6 and 6; the one that did not reached 1."""

    def make(self, plan_text):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "STATUS.md").write_text("# S\n", encoding="utf-8")
        (root / "sketch").mkdir()
        (root / "sketch" / "decomposition.md").write_text(plan_text, encoding="utf-8")
        return root

    def test_no_plan_is_unknown_not_silent(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.assertFalse(speed_gate.plan_width(Path(temp.name))["known"])

    def test_chain_without_a_frontier_is_flagged(self):
        root = self.make("# D\n## Dependency DAG\ndef:X -> lem:A -> lem:B -> thm:main\n")
        self.assertEqual(speed_gate.plan_width(root)["silent"], ["decomposition.md"])
        self.assertTrue(
            any("Parallel Frontier" in w for w in speed_gate.lint_workspace(root).warnings)
        )

    def test_the_declared_heading_satisfies_it(self):
        root = self.make("# D\n## Parallel Frontier\n- Dispatchable: lem:A, lem:B\n")
        self.assertEqual(speed_gate.plan_width(root)["silent"], [])

    def test_a_frontier_stated_in_the_authors_own_words_counts(self):
        """Two real workspaces did this before any rule asked. Requiring the
        exact heading would have scored a run with six concurrent specialists
        as silent — the information is what matters, not the formatting."""
        for phrasing in (
            "Roots (dispatchable immediately, in parallel): lem:A, lem:B",
            "Dispatchable immediately, no unresolved dependencies: lem:A, lem:B",
        ):
            root = self.make(f"# D\n## Dependency DAG\n...\n\n{phrasing}\n")
            self.assertEqual(
                speed_gate.plan_width(root)["silent"], [], f"missed phrasing: {phrasing}"
            )


class UnsplitChainTests(unittest.TestCase):
    """A wider DAG cannot take a run below its worst lemma's revision chain. On
    the 26-hour run that chain was 11 rounds and 7.9 hours for one lemma, so even
    perfect lemma-level parallelism left 7.9 hours on the clock."""

    def make(self, family, sizes):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "STATUS.md").write_text("# S\n", encoding="utf-8")
        directory = root / family
        directory.mkdir(parents=True)
        for index, size in enumerate(sizes, start=1):
            (directory / f"proof_v{index}.md").write_text("x" * size, encoding="utf-8")
        return root

    def test_short_chain_is_quiet(self):
        root = self.make("lemmas/a/generator", [1000, 1100, 1200])
        self.assertEqual(speed_gate.unsplit_chains(root)["chains"], [])

    def test_long_growing_chain_is_flagged(self):
        root = self.make("lemmas/a/generator", [1000, 1200, 1400, 1600, 1800])
        chains = speed_gate.unsplit_chains(root)["chains"]
        self.assertEqual(len(chains), 1)
        self.assertEqual(chains[0]["versions"], 5)
        self.assertTrue(
            any("not converging" in w for w in speed_gate.lint_workspace(root).warnings)
        )

    def test_a_converging_chain_is_left_alone(self):
        """Shrinking versions mean blocking issues are narrowing. That is a lemma
        finishing, and interrupting it to re-decompose throws the work away."""
        root = self.make("lemmas/a/generator", [4000, 3500, 3000, 2500, 2000])
        self.assertEqual(speed_gate.unsplit_chains(root)["chains"], [])

    def test_a_log_file_is_not_a_proof_attempt(self):
        """The real shape that fooled the first version of this check:
        `logs/generator_<lemma>_v8.md` — a file whose *name* starts with
        "generator", not a proof in a `generator/` directory. Advising a split
        because a dispatch note has many versions is advice about the wrong
        object, and it fired on a real workspace."""
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "STATUS.md").write_text("# S\n", encoding="utf-8")
        (root / "logs").mkdir()
        for index, size in enumerate([1000, 1200, 1400, 1600, 1800], start=1):
            (root / "logs" / f"generator_lem_a_v{index}.md").write_text(
                "x" * size, encoding="utf-8"
            )
        self.assertEqual(speed_gate.unsplit_chains(root)["chains"], [])

    def test_a_generator_directory_under_logs_is_also_ignored(self):
        root = self.make("logs/generator", [1000, 1200, 1400, 1600, 1800])
        self.assertEqual(speed_gate.unsplit_chains(root)["chains"], [])


class PreambleTests(unittest.TestCase):
    """The block before the first `##` went from 11 lines in v1 to 946 lines
    (61 KB) in v11 on the worst lemma — a stack of per-round change logs, 60 KB
    of the file's 92 KB growth, and the source of v10's only blocking issue."""

    def lint(self, text):
        sys.path.insert(0, str(REPO_ROOT / "cli_tools"))
        from _gate.proof_attempt import lint_preamble_is_mathematics

        return lint_preamble_is_mathematics(text)

    def test_a_short_preamble_is_quiet(self):
        self.assertEqual(self.lint("# Proof\n\nStatement as printed.\n\n## Setup\nx\n"), [])

    def test_a_change_log_preamble_is_named_as_one(self):
        body = "# Proof\n" + "\n".join(
            ["> **What changed in v7, and what did not.** Provenance:"] * 70
        ) + "\n## Setup\nx\n"
        found = self.lint(body)
        self.assertTrue(found and "change log" in found[0])
        self.assertIn("response_to_verifier.md", found[0])

    def test_a_long_preamble_without_change_log_wording_is_softer(self):
        body = "# Proof\n" + "\n".join(["Let x be an integer."] * 70) + "\n## Setup\nx\n"
        found = self.lint(body)
        self.assertTrue(found and "change log" not in found[0])

    def test_no_second_level_heading_at_all(self):
        """A file with no `##` is entirely preamble; it must not crash."""
        self.assertTrue(self.lint("# Proof\n" + "\n".join(["No mathematics is touched"] * 70)))


class PlatformAndTokenTests(unittest.TestCase):
    """A workspace is not a platform. `newtestb` was worked by 5 Claude Code
    sessions and 12 Codex ones; reading a difference between two such workspaces
    as a difference between two configurations compares two models instead."""

    def make(self, entries):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "STATUS.md").write_text("# S\n", encoding="utf-8")
        (root / "logs").mkdir()
        (root / "logs" / "dispatch.jsonl").write_text(
            "".join(json.dumps(entry) + "\n" for entry in entries), encoding="utf-8"
        )
        return root

    def test_hand_written_log_is_unstated_not_assumed(self):
        """The failure to avoid: defaulting an unlabelled entry to the platform
        that happens to be running the gate."""
        mix = speed_gate.platform_mix(self.make([{"role": "generator"}] * 3))
        self.assertEqual(mix["counts"], {"unstated": 3})
        self.assertFalse(mix["mixed"])

    def test_two_platforms_in_one_workspace_are_warned_about(self):
        root = self.make(
            [
                {"role": "generator", "platform": "claude-code"},
                {"role": "verifier", "platform": "codex"},
            ]
        )
        self.assertTrue(speed_gate.platform_mix(root)["mixed"])
        self.assertTrue(
            any("more than one platform" in w for w in speed_gate.lint_workspace(root).warnings)
        )

    def test_one_platform_is_not_warned_about(self):
        root = self.make([{"role": "generator", "platform": "claude-code"}] * 2)
        self.assertFalse(
            any("more than one platform" in w for w in speed_gate.lint_workspace(root).warnings)
        )

    def test_tokens_are_summed_and_cache_kept_separate(self):
        """Cache reads ran 160:1 against output on a real session. Folding them
        into one total hides the only number worth acting on."""
        root = self.make(
            [
                {"role": "generator", "tokens": {"in": 10, "out": 100,
                                                 "cache_read": 8000, "cache_write": 50}},
                {"role": "verifier", "tokens": {"in": 5, "out": 60,
                                                "cache_read": 4000, "cache_write": 10}},
            ]
        )
        cost = speed_gate.token_cost(root)
        self.assertEqual(
            cost["totals"],
            {"in": 15, "out": 160, "cache_read": 12000, "cache_write": 60, "total": 0},
        )
        self.assertTrue(cost["split_known"])
        self.assertEqual(cost["read_write_ratio"], 75.0)

    def test_a_scalar_token_total_is_kept_as_a_total(self):
        """Hand-kept logs record one number per dispatch. Inventing a split for
        it would be worse than saying only the total is known."""
        root = self.make([{"role": "generator", "tokens": 57118},
                          {"role": "verifier", "tokens": 42882}])
        cost = speed_gate.token_cost(root)
        self.assertEqual(cost["totals"]["total"], 100000)
        self.assertFalse(cost["split_known"])

    def test_a_log_without_tokens_is_unknown_not_zero(self):
        cost = speed_gate.token_cost(self.make([{"role": "generator"}]))
        self.assertFalse(cost["known"])
        self.assertNotIn("totals", cost)

    # --- dispatch prompt shape ---------------------------------------------

    def test_a_log_without_prompt_shape_is_unmeasured_not_zero_percent(self):
        """The distinction the whole block exists for. Every hand-kept log in
        the corpus predates the field; reporting those runs as 0% anchored says
        the opposite of what they did."""
        shape = speed_gate.prompt_shape(self.make([{"role": "verifier"}] * 3))
        self.assertFalse(shape["known"])
        self.assertNotIn("anchored", shape)
        self.assertEqual(shape["form"], "absent")

    def test_a_text_prompt_shape_is_reported_as_present_and_unscoreable(self):
        """`known: False` had two causes reported as one sentence. The connes
        log carries prompt_shape on 63 of 63 records as the hand-kept string
        convention, and the gate said no record carried it — a false statement
        about the data, which a reviewer then repeated. Present-but-unscoreable
        and absent are different findings."""
        root = self.make([
            {"role": "verifier", "prompt_shape": "artifact-statement-budget-no-prior-verdict"},
            {"role": "verifier", "prompt_shape": "fresh-standalone-target-no-prior-narrative"},
            {"role": "generator", "prompt_shape": "statement-accepted-inventory-scope"},
        ])
        shape = speed_gate.prompt_shape(root)
        self.assertFalse(shape["known"])
        self.assertEqual(shape["form"], "text")
        self.assertEqual(shape["with_text_shape"], 3)
        self.assertEqual(shape["verifier_records"], 2)
        # Not parsed into booleans. A substring match on free text would fail
        # silently in the flattering direction.
        self.assertNotIn("anchored", shape)

    def test_a_text_prompt_shape_does_not_contaminate_a_scoreable_log(self):
        """A log holding both forms is scored on the dict records only; the
        string ones must not be counted as unanchored."""
        root = self.make([
            {"role": "verifier", "prompt_shape": {
                "generator_framing": False, "prior_verdict": False,
                "budget": True, "stopping_condition": True, "chars": 100}},
            {"role": "verifier", "prompt_shape": "fresh-standalone-no-prior-verdict"},
        ])
        shape = speed_gate.prompt_shape(root)
        self.assertTrue(shape["known"])
        self.assertEqual(shape["with_shape"], 1)
        self.assertEqual(shape["verifier_records"], 1)
        self.assertEqual(shape["anchored"], 0)

    def test_percentages_are_over_verifier_records_only(self):
        """P25's thresholds are stated over verifier dispatches. A generator
        dispatch that recites a prior verdict is not a violation of them."""
        root = self.make(
            [
                {"role": "verifier", "prompt_shape": {
                    "chars": 400, "generator_framing": True, "prior_verdict": False,
                    "budget": True, "stopping_condition": False, "freshness_claim": False}},
                {"role": "verifier", "prompt_shape": {
                    "chars": 200, "generator_framing": False, "prior_verdict": False,
                    "budget": False, "stopping_condition": True, "freshness_claim": True}},
                {"role": "generator", "prompt_shape": {
                    "chars": 800, "generator_framing": True, "prior_verdict": True,
                    "budget": True, "stopping_condition": True, "freshness_claim": False}},
            ]
        )
        shape = speed_gate.prompt_shape(root)
        self.assertTrue(shape["known"])
        self.assertEqual(shape["with_shape"], 3)
        self.assertEqual(shape["verifier_records"], 2)
        self.assertEqual(shape["anchored"], 1)
        self.assertEqual(shape["budget"], 1)
        self.assertEqual(shape["stopping_condition"], 1)
        # Length spread is deliberately over every role: 800 / 200.
        self.assertEqual(shape["length_spread"], 4.0)

    def test_either_framing_or_a_prior_verdict_counts_as_anchored(self):
        root = self.make(
            [
                {"role": "verifier", "prompt_shape": {
                    "chars": 100, "generator_framing": False, "prior_verdict": True,
                    "budget": False, "stopping_condition": False, "freshness_claim": False}},
            ]
        )
        self.assertEqual(speed_gate.prompt_shape(root)["anchored"], 1)
        self.assertIsNone(speed_gate.prompt_shape(root)["length_spread"])

    def test_the_unmeasured_case_prints_that_it_is_not_zero(self):
        root = self.make([{"role": "verifier"}])
        metrics = speed_gate.lint_workspace(root).metrics
        self.assertFalse(metrics["prompt_shape"]["known"])


class DispatchLogHookTests(unittest.TestCase):
    """The hook is a silent parser and silent parsers rot: a renamed payload key
    makes it write nothing, and writing nothing looks exactly like a run that
    dispatched nothing. Its self-test is part of the suite, not optional."""

    def test_hook_self_test_passes(self):
        hook = REPO_ROOT / ".claude" / "hooks" / "dispatch_log.py"
        self.assertTrue(hook.is_file(), "dispatch_log.py is missing")
        completed = subprocess.run(
            [sys.executable, str(hook), "--self-test"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def _run_hook(self, payload, extra=None):
        hook = REPO_ROOT / ".claude" / "hooks" / "dispatch_log.py"
        return subprocess.run(
            [sys.executable, str(hook)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env={**os.environ, **(extra or {})},
        )

    def test_prompt_shape_survives_a_real_stdin_round_trip(self):
        """Pre then Post, the way Claude Code sends them, with no live session."""
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "STATUS.md").write_text("# S\n", encoding="utf-8")
        prompt = (
            "History: 2 prior rounds, all NEEDS_REVISION. The Generator reports "
            "the gap is closed. Budget: seconds-scale, no sweeps."
        )
        payload = {
            "session_id": "roundtrip",
            "cwd": str(root),
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "verifier", "prompt": prompt},
        }
        self._run_hook({**payload, "hook_event_name": "PreToolUse"})
        self._run_hook({**payload, "hook_event_name": "PostToolUse", "tool_response": "ok"})
        line = (root / "logs" / "dispatch.jsonl").read_text(encoding="utf-8").strip()
        entry = json.loads(line)
        self.assertEqual(entry["prompt_shape"]["generator_framing"], True)
        self.assertEqual(entry["prompt_shape"]["prior_verdict"], True)
        self.assertEqual(entry["prompt_shape"]["chars"], len(prompt))
        # The rule this field lives under: the mathematics never reaches the log.
        self.assertNotIn("Generator reports", line)

    def test_hook_is_registered_for_both_halves(self):
        """Pre stamps the start, Post writes the line. With only Post registered
        every duration is unknown and the A3 batch criterion has nothing to use."""
        settings = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
        for event in ("PreToolUse", "PostToolUse"):
            # The tool is called `Agent` in this build. The first version of this
            # hook matched `Task` — the name in most published examples — and so
            # never fired once, which is indistinguishable from a run that never
            # dispatched. Pin the real name.
            commands = [
                hook["command"]
                for block in settings.get("hooks", {}).get(event, [])
                if "Agent" in (block.get("matcher") or "")
                for hook in block.get("hooks", [])
            ]
            self.assertTrue(
                any("dispatch_log.py" in command for command in commands),
                f"dispatch_log.py not registered for {event} on the Agent tool",
            )


class ShadowAccountingTests(unittest.TestCase):
    """A losing shadow leaves no artifact by design. Counting it as a stall made
    a healthy run read as one that wasted a third of its dispatches — measured on
    a real workspace, which is the whole reason these two are separated."""

    def make(self, entries):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "STATUS.md").write_text("# S\n", encoding="utf-8")
        (root / "logs").mkdir()
        (root / "logs" / "dispatch.jsonl").write_text(
            "".join(json.dumps(entry) + "\n" for entry in entries), encoding="utf-8"
        )
        return root

    def test_discarded_shadow_is_not_a_stall(self):
        root = self.make(
            [
                {"role": "generator", "target": "a.md", "batch": "b-1"},
                {
                    "role": "generator",
                    "target": "a_shadow1.md",
                    "batch": "b-1-shadow-1",
                    "result": "interrupted_discarded_unread",
                },
            ]
        )
        result = speed_gate.stalled_dispatches(root)
        self.assertEqual(result["produced_nothing"], 1)  # a.md, which really is missing
        self.assertEqual(result["discarded_by_design"], 1)

    def _universal_shadowing(self, winner_index=None):
        entries = []
        for index in range(4):
            entries.append({"role": "generator", "target": f"p{index}.md", "batch": f"b{index}"})
            entries.append(
                {
                    "role": "generator",
                    "target": f"p{index}_shadow1.md",
                    "batch": f"b{index}-shadow-1",
                    "result": "adopted"
                    if index == winner_index
                    else "interrupted_discarded_unread",
                }
            )
        return self.make(entries)

    def test_universal_shadowing_that_never_pays_out_is_warned_about(self):
        result = speed_gate.lint_workspace(self._universal_shadowing())
        self.assertTrue(any("none was ever adopted" in w for w in result.warnings))

    def test_an_adopted_shadow_silences_the_warning(self):
        """The mechanism is not the defect — buying insurance that pays out is
        exactly what it is for. Only the never-claimed case is waste."""
        result = speed_gate.lint_workspace(self._universal_shadowing(winner_index=2))
        self.assertFalse(any("none was ever adopted" in w for w in result.warnings))


if __name__ == "__main__":
    unittest.main()
