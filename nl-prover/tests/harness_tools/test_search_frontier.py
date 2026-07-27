#!/usr/bin/env python3
"""Tests for the deep-search frontier state store (ADR 0018 O3)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "cli_tools"))

from _search import frontier  # noqa: E402


class FrontierTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)
        frontier.init(self.ws, "bounded gaps between primes", max_depth=2)

    def tearDown(self):
        self._tmp.cleanup()

    # -- init ------------------------------------------------------------
    def test_init_creates_state_under_knowledge(self):
        self.assertTrue(frontier.nodes_path(self.ws).exists())
        self.assertTrue(frontier.meta_path(self.ws).exists())
        self.assertEqual(frontier.load_meta(self.ws)["obligation"], "bounded gaps between primes")

    def test_init_refuses_to_clobber_without_force(self):
        frontier.push(self.ws, "arxiv:1", title="keep me")
        result = frontier.init(self.ws, "different obligation")
        self.assertFalse(result["ok"])
        self.assertEqual(len(frontier.load_nodes(self.ws)), 1)

    def test_init_force_resets(self):
        frontier.push(self.ws, "arxiv:1")
        result = frontier.init(self.ws, "new obligation", force=True)
        self.assertTrue(result["ok"])
        self.assertEqual(frontier.load_nodes(self.ws), [])

    # -- push ------------------------------------------------------------
    def test_push_is_idempotent_on_id(self):
        frontier.push(self.ws, "arxiv:1", title="first", score=0.5)
        result = frontier.push(self.ws, "arxiv:1", title="second", score=0.9)
        self.assertFalse(result["created"])
        nodes = frontier.load_nodes(self.ws)
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["title"], "second")
        self.assertEqual(nodes[0]["score"], 0.9)

    def test_repush_does_not_resurrect_processed_node(self):
        """A citation-graph cycle must not make the loop non-terminating."""
        frontier.push(self.ws, "arxiv:1")
        frontier.mark(self.ws, "arxiv:1", "expanded")
        frontier.push(self.ws, "arxiv:1", title="seen again via another path")
        self.assertEqual(frontier.load_nodes(self.ws)[0]["status"], "expanded")

    def test_push_keeps_shallowest_depth(self):
        frontier.push(self.ws, "arxiv:1", depth=2)
        frontier.push(self.ws, "arxiv:1", depth=1)
        self.assertEqual(frontier.load_nodes(self.ws)[0]["depth"], 1)

    # -- next ------------------------------------------------------------
    def test_next_orders_by_score_descending(self):
        frontier.push(self.ws, "low", score=0.1)
        frontier.push(self.ws, "high", score=0.9)
        frontier.push(self.ws, "mid", score=0.5)
        batch = frontier.next_batch(self.ws, n=3)["batch"]
        self.assertEqual([n["id"] for n in batch], ["high", "mid", "low"])

    def test_next_respects_hop_budget(self):
        frontier.push(self.ws, "shallow", depth=1, score=0.1)
        frontier.push(self.ws, "deep", depth=5, score=0.9)
        batch = frontier.next_batch(self.ws, n=5, max_depth=1)["batch"]
        self.assertEqual([n["id"] for n in batch], ["shallow"])

    def test_next_defaults_to_stored_max_depth(self):
        frontier.push(self.ws, "within", depth=2, score=0.5)
        frontier.push(self.ws, "beyond", depth=3, score=0.9)
        batch = frontier.next_batch(self.ws, n=5)["batch"]
        self.assertEqual([n["id"] for n in batch], ["within"])

    def test_next_is_non_mutating_by_default(self):
        frontier.push(self.ws, "a", score=0.5)
        frontier.next_batch(self.ws, n=1)
        self.assertEqual(frontier.load_nodes(self.ws)[0]["status"], "queued")

    def test_next_claim_marks_expanded(self):
        frontier.push(self.ws, "a", score=0.5)
        result = frontier.next_batch(self.ws, n=1, claim=True)
        self.assertTrue(result["claimed"])
        self.assertEqual(frontier.load_nodes(self.ws)[0]["status"], "expanded")

    def test_next_excludes_processed_nodes(self):
        frontier.push(self.ws, "a", score=0.9)
        frontier.push(self.ws, "b", score=0.5)
        frontier.mark(self.ws, "a", "skipped")
        batch = frontier.next_batch(self.ws, n=5)["batch"]
        self.assertEqual([n["id"] for n in batch], ["b"])

    # -- mark ------------------------------------------------------------
    def test_mark_rejects_unknown_status(self):
        frontier.push(self.ws, "a")
        self.assertFalse(frontier.mark(self.ws, "a", "bogus")["ok"])

    def test_mark_rejects_unknown_id(self):
        self.assertFalse(frontier.mark(self.ws, "nope", "expanded")["ok"])

    # -- status ----------------------------------------------------------
    def test_status_reports_counts_and_budget(self):
        frontier.push(self.ws, "a", depth=1, source="arxiv")
        frontier.push(self.ws, "b", depth=2, source="citation-graph")
        frontier.mark(self.ws, "a", "expanded")
        report = frontier.status(self.ws)
        self.assertEqual(report["total"], 2)
        self.assertEqual(report["by_status"]["expanded"], 1)
        self.assertEqual(report["by_status"]["queued"], 1)
        self.assertEqual(report["by_depth"]["2"], 1)
        self.assertEqual(report["by_source"]["citation-graph"], 1)
        self.assertEqual(report["depth_reached"], 2)

    def test_status_on_uninitialized_workspace(self):
        with tempfile.TemporaryDirectory() as blank:
            report = frontier.status(blank)
            self.assertFalse(report["initialized"])
            self.assertEqual(report["total"], 0)

    # -- robustness / cli ------------------------------------------------
    def test_malformed_lines_are_skipped_not_fatal(self):
        frontier.push(self.ws, "good")
        path = frontier.nodes_path(self.ws)
        path.write_text(path.read_text(encoding="utf-8") + "{not json\n", encoding="utf-8")
        self.assertEqual([n["id"] for n in frontier.load_nodes(self.ws)], ["good"])

    def test_cli_roundtrip(self):
        with tempfile.TemporaryDirectory() as ws:
            frontier.main(["init", ws, "--obligation", "x", "--max-depth", "1"])
            frontier.main(["push", ws, "--id", "arxiv:9", "--score", "0.7", "--source", "arxiv"])
            frontier.main(["mark", ws, "--id", "arxiv:9", "--status", "expanded"])
            self.assertEqual(frontier.status(ws)["by_status"]["expanded"], 1)


if __name__ == "__main__":
    unittest.main()
