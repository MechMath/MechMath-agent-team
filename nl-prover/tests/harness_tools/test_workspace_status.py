"""`workspace status`: what a run's page says, and what it refuses to say.

The tests that matter most here are the negative ones. A dashboard is the point
where a silently-wrong number reaches a person rather than a log, so every one
of these fixes that an unmeasurable field prints its reason instead of a zero.
"""

import json
from pathlib import Path
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "cli_tools"))
from _workspace import status as status_tool


BASE = 1_800_000_000.0
HOUR = 3600.0


class Fixture:
    def __init__(self, root: Path):
        self.root = root

    def run_root(self, relative, *, status_text="# s\n\n## Phase\nprove\n"):
        directory = self.root / relative if relative else self.root
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "STATUS.md").write_text(status_text, encoding="utf-8")
        return directory

    def lemma(self, directory, name, *, verdict=None, at=BASE):
        import os

        path = directory / "lemmas" / name
        path.mkdir(parents=True, exist_ok=True)
        statement = path / "statement.md"
        statement.write_text(
            f"# {name}\n\n## Statement\n\nX.\n\n## Dependencies\n\nDepends-on: NONE\n",
            encoding="utf-8",
        )
        os.utime(statement, (at, at))
        if verdict:
            verdict_path = path / "verifier" / "verdict.md"
            verdict_path.parent.mkdir(parents=True, exist_ok=True)
            verdict_path.write_text(f"# Verdict: {verdict}\n\nBecause.\n", encoding="utf-8")
            os.utime(verdict_path, (at, at))
        return path


class StatusPageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fixture = Fixture(self.root)

    # --- the graph --------------------------------------------------------

    def test_a_run_with_lemmas_reports_its_graph(self):
        run = self.fixture.run_root("r")
        self.fixture.lemma(run, "a", verdict="PASS")
        self.fixture.lemma(run, "b")
        report = status_tool.collect(run, now=BASE + HOUR)
        self.assertTrue(report["graph"]["available"])
        self.assertEqual(2, report["graph"]["nodes"])
        self.assertEqual(1, report["graph"]["status_counts"].get("PASS"))

    def test_a_run_with_no_lemmas_says_so_rather_than_reporting_zero(self):
        run = self.fixture.run_root("r")
        report = status_tool.collect(run, now=BASE)
        self.assertFalse(report["graph"]["available"])
        self.assertIn("no lemmas/", report["graph"]["why"])
        self.assertNotIn("nodes", report["graph"])

    def test_only_findings_that_fired_are_carried(self):
        """Nine findings all reading 0 is a wall the reader stops looking at."""
        run = self.fixture.run_root("r")
        self.fixture.lemma(run, "a", verdict="PASS")
        report = status_tool.collect(run, now=BASE)
        self.assertTrue(all(count > 0 for count in report["graph"]["findings"].values()))

    # --- liveness ---------------------------------------------------------

    def test_liveness_labels_track_the_newest_artifact(self):
        run = self.fixture.run_root("r")
        self.fixture.lemma(run, "a", at=BASE)
        for offset, expected in ((HOUR, "working"), (6 * HOUR, "quiet"), (40 * HOUR, "idle")):
            report = status_tool.collect(run, now=BASE + offset)
            self.assertEqual(expected, report["liveness"]["label"], offset)

    def test_liveness_says_what_it_is_derived_from(self):
        """mtimes cannot separate a stuck run from a human who went to lunch."""
        run = self.fixture.run_root("r")
        self.fixture.lemma(run, "a", at=BASE)
        why = status_tool.collect(run, now=BASE + HOUR)["liveness"]["why"]
        self.assertIn("mtimes", why)
        self.assertIn("away from", why)

    def test_a_run_with_nothing_at_all_is_empty(self):
        """`empty` now means no STATUS.md and no artifact under any run
        directory. It used to mean "nothing under lemmas/", which labelled a run
        worked entirely through STATUS.md as never started."""
        run = self.root / "bare"
        run.mkdir()
        report = status_tool.collect(run, now=BASE)
        self.assertEqual("empty", report["liveness"]["label"])
        self.assertNotIn("idle_seconds", report["liveness"])

    # --- refusing to invent ------------------------------------------------

    def test_the_four_unrecorded_fields_are_named_on_every_page(self):
        run = self.fixture.run_root("r")
        report = status_tool.collect(run, now=BASE)
        self.assertEqual(
            {"phase", "last_progress", "current_focus", "cost"},
            set(report["not_recorded"]),
        )
        for why in report["not_recorded"].values():
            self.assertTrue(why)

    def test_cost_is_unknown_with_a_reason_not_zero(self):
        run = self.fixture.run_root("r")
        report = status_tool.collect(run, now=BASE)
        cost = report["economics"]["cost"]
        self.assertFalse(cost["known"])
        self.assertIn("why", cost)

    def test_concurrency_carries_the_source_it_was_measured_from(self):
        run = self.fixture.run_root("r")
        self.fixture.lemma(run, "a", verdict="PASS")
        report = status_tool.collect(run, now=BASE)
        self.assertIsNotNone(report["economics"]["concurrency_source"])

    def test_memory_absence_says_which_command_fills_it(self):
        run = self.fixture.run_root("r")
        report = status_tool.collect(run, now=BASE)
        self.assertFalse(report["memory"]["available"])
        self.assertIn("memory.py refresh", report["memory"]["why"])

    def test_the_rendered_page_never_prints_a_bare_zero_for_cost(self):
        run = self.fixture.run_root("r")
        page = status_tool.render(status_tool.collect(run, now=BASE))
        self.assertIn("cost", page)
        self.assertIn("unknown", page)

    # --- the index --------------------------------------------------------

    def test_a_run_root_is_a_directory_holding_a_status_file(self):
        """Not a top-level directory: ESConjecture/ alone holds 15 of them."""
        self.fixture.run_root("container/first")
        self.fixture.run_root("container/second")
        self.fixture.run_root("alone")
        roots = status_tool.run_roots(self.root)
        self.assertEqual(3, len(roots))

    def test_a_tree_root_that_is_itself_a_run_is_counted_once(self):
        self.fixture.run_root("")
        self.fixture.run_root("child")
        self.assertEqual(2, len(status_tool.run_roots(self.root)))

    def test_the_index_is_keyed_on_the_relative_path_not_the_basename(self):
        """The corpus has two directories called `old`, and a `CLT` that is both
        a container of runs and a run. A basename index merges rows silently."""
        self.fixture.run_root("a/old")
        self.fixture.run_root("b/old")
        reports = []
        for path in status_tool.run_roots(self.root):
            report = status_tool.collect(path)
            report["relative"] = str(path.relative_to(self.root))
            reports.append(report)
        page = status_tool.render_index(reports, self.root)
        self.assertIn("a/old", page)
        self.assertIn("b/old", page)

    # --- shape ------------------------------------------------------------

    def test_the_report_is_json_serialisable(self):
        run = self.fixture.run_root("r")
        self.fixture.lemma(run, "a", verdict="PASS")
        json.dumps(status_tool.collect(run, now=BASE))

    def test_a_directory_with_no_status_file_is_not_a_run(self):
        (self.root / "notarun").mkdir()
        self.assertEqual([], status_tool.run_roots(self.root / "notarun"))

class NoFabricatedNumbersTests(unittest.TestCase):
    """125 rendered lines across the corpus broke this module's headline rule.

    Each test here is one of the shapes that produced them. The distinction the
    module has to hold is between a measured zero — no dependency edges, no
    artifacts on disk — and a zero derived from an empty sample, which is the
    `wall_clock_ms = 0.0` lie printed on a page a person reads.
    """

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fixture = Fixture(self.root)

    def page(self, run):
        return status_tool.render(status_tool.collect(run, now=BASE + HOUR))

    def test_a_run_worked_through_status_md_alone_is_not_empty(self):
        """One corpus run has a 472-line STATUS.md and nothing under lemmas/,
        and read as `empty` — never started."""
        run = self.fixture.run_root("r")
        report = status_tool.collect(run, now=BASE + HOUR)
        self.assertNotEqual("empty", report["liveness"]["label"])

    def test_no_versioned_families_prints_a_reason_not_zero_bytes(self):
        run = self.fixture.run_root("r")
        page = self.page(run)
        self.assertNotIn("bytes written         0", page)
        self.assertIn("no versioned artifact families", page)

    def test_nothing_overlapping_prints_unmeasured_not_zero(self):
        run = self.fixture.run_root("r")
        page = self.page(run)
        self.assertNotIn("concurrency           0 of", page)
        self.assertIn("unmeasured", page)

    def test_promotion_never_run_says_so_rather_than_None(self):
        run = self.fixture.run_root("r")
        (run / "memory").mkdir(exist_ok=True)
        (run / "memory" / "index.json").write_text('{"channels": {}}', encoding="utf-8")
        page = self.page(run)
        self.assertNotIn("None promoted", page)
        self.assertIn("promotion not run", page)

    def test_a_dialect_without_PASS_is_not_scored_as_zero_progress(self):
        """11 of 54 run roots use a vocabulary with no PASS value at all; one
        has two lemmas `done` and the index read `0/3 PASS`."""
        run = self.fixture.run_root("r")
        self.fixture.lemma(run, "a", verdict="done")
        report = status_tool.collect(run, now=BASE + HOUR)
        report["relative"] = "r"
        line = status_tool.render_index([report], self.root)
        self.assertNotIn("0/1 PASS", line)

    def test_a_measured_zero_is_still_printed_as_zero(self):
        """No dependency edges is a fact, not an absence of measurement."""
        run = self.fixture.run_root("r")
        self.fixture.lemma(run, "a", verdict="PASS")
        report = status_tool.collect(run, now=BASE + HOUR)
        self.assertEqual(0, report["graph"]["edges"])


if __name__ == "__main__":
    unittest.main()
