"""A count is not progress when the one open item is the thing the run was for.

`workspace status --index` rendered `7/8 PASS` — seven trivial lemmas closed and the
target open reads as 87.5% and is no closer to a proof than an empty run. `gate summary`
already refuses that shape in the document a person reads at the stop ("a guess wearing
a measurement as a costume"); the index manufactured it mid-run. `dag.py` had computed
which assembly nodes nothing vouches for and handed them over in the same dict.
"""

import sys
import types
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "cli_tools"))

from _workspace import status  # noqa: E402


def report(counts, nodes, *, open_tops=(), tops=("assembly",), name="run-a"):
    return {
        "name": name,
        "relative": name,
        "graph": {
            "available": True,
            "nodes": nodes,
            "edges": 0,
            "status_counts": dict(counts),
            "top_nodes": list(tops),
            "unaccepted_top_nodes": list(open_tops),
            "statement_missing": 0,
            "status_dialect": None,
            "findings": {},
            "mtime_based": [],
        },
        "status": {"available": True, "modified": "2026-08-30", "lines": 10, "bytes": 200},
        "liveness": {"label": "idle", "why": "fixture"},
        "workspace": f"/tmp/{name}",
        "economics": {"available": False, "why": "not needed for this test"},
        "memory": {"available": False, "why": "not needed for this test"},
        "not_recorded": {},
        "documents": {},
    }


class IndexLineTests(unittest.TestCase):
    def line(self, rendered, name="run-a"):
        return next(l for l in rendered.splitlines() if name in l)

    def test_an_open_target_is_named_beside_the_fraction(self):
        text = status.render_index([report({"PASS": 7}, 8, open_tops=["assembly"])])
        self.assertIn("7/8 PASS", self.line(text))
        self.assertIn("target open", self.line(text))

    def test_a_closed_target_leaves_the_fraction_alone(self):
        text = status.render_index([report({"PASS": 7}, 8)])
        self.assertIn("7/8 PASS", self.line(text))
        self.assertNotIn("target open", self.line(text))

    def test_the_same_fraction_reads_differently_in_the_two_cases(self):
        """The whole point: 7/8 is one number and two opposite facts."""
        open_run = status.render_index([report({"PASS": 7}, 8, open_tops=["assembly"])])
        done_run = status.render_index([report({"PASS": 7}, 8)])
        self.assertNotEqual(self.line(open_run), self.line(done_run))

    def test_the_fraction_is_kept_because_it_is_a_real_count(self):
        text = status.render_index([report({"PASS": 7}, 8, open_tops=["assembly"])])
        self.assertIn("7/8", self.line(text))

    def test_a_run_with_no_pass_vocabulary_is_untouched(self):
        text = status.render_index([report({"done": 2}, 8, open_tops=["assembly"])])
        self.assertIn("no PASS", self.line(text))

    def test_a_run_with_no_graph_is_untouched(self):
        row = report({"PASS": 1}, 1)
        row["graph"] = {"available": False, "why": "no lemmas/ directory in this run"}
        self.assertIn("no lemmas/", self.line(status.render_index([row])))


class PerRunViewTests(unittest.TestCase):
    def test_the_target_line_appears_and_says_which(self):
        text = status.render(report({"PASS": 7}, 8, open_tops=["assembly"]))
        self.assertIn("target", text)
        self.assertIn("assembly", text)
        self.assertIn("OPEN", text)

    def test_an_accepted_target_says_accepted(self):
        text = status.render(report({"PASS": 8}, 8))
        self.assertIn("accepted", text)
        self.assertNotIn("OPEN", text)


class WiringTests(unittest.TestCase):
    """`graph()` used to drop these two keys on the floor. The defect was not that
    the information was missing — it was computed and then not carried."""

    def test_graph_carries_the_top_node_metrics(self):
        fake = types.SimpleNamespace(
            metrics={
                "nodes": 8,
                "edges": 7,
                "status_counts": {"PASS": 7},
                "top_nodes": ["assembly"],
                "unaccepted_top_node": ["assembly"],
                "statement_missing": [],
                "findings": {},
            }
        )
        original = status.dag_gate.analyse
        status.dag_gate.analyse = lambda workspace: fake
        try:
            out = status.graph(Path("/nonexistent"))
        finally:
            status.dag_gate.analyse = original
        self.assertEqual(out["top_nodes"], ["assembly"])
        self.assertEqual(out["unaccepted_top_nodes"], ["assembly"])


if __name__ == "__main__":
    unittest.main()
