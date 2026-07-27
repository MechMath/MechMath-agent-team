#!/usr/bin/env python3
"""Tests for citation-graph multi-hop search (ADR 0018 O1).

Traversal is exercised against a fake EdgeProvider -- no network access.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "cli_tools"))

from _search import citation_graph as cg  # noqa: E402
from _search import frontier  # noqa: E402


class FakeProvider(cg.EdgeProvider):
    """In-memory citation graph: {id: (title, abstract, [referenced], [citing])}."""

    def __init__(self, graph, root="W1"):
        self.graph = graph
        self.root = root

    def _node(self, work_id):
        title, abstract, refs, _ = self.graph[work_id]
        return {
            "id": work_id, "title": title, "abstract": abstract,
            "year": 2020, "doi": "", "referenced_works": refs,
        }

    def resolve(self, seed):
        return self._node(self.root) if self.root in self.graph else None

    def fetch(self, work_ids):
        return [self._node(w) for w in work_ids if w in self.graph]

    def cited_by(self, work_id, limit):
        out = [self._node(w) for w, (_, _, _, citing) in self.graph.items() if work_id in citing]
        return out[:limit]


GRAPH = {
    "W1": ("seed paper", "about the seed", ["W2", "W3"], []),
    "W2": ("bounded gaps between primes", "sieve methods and bounded gaps", [], []),
    "W3": ("unrelated topology", "fibre bundles", ["W4"], []),
    "W4": ("deep prime gaps lemma", "bounded gaps sieve", [], []),
    "W5": ("later work citing seed", "bounded gaps follow-up", [], ["W1"]),
}


class ScoringTestCase(unittest.TestCase):
    def test_tokenize_drops_stopwords_and_short_tokens(self):
        self.assertEqual(cg.tokenize("The gaps of a Prime"), {"gaps", "prime"})

    def test_relevance_is_fraction_of_obligation_keywords_matched(self):
        tokens = cg.tokenize("bounded gaps primes")
        score, why = cg.relevance(tokens, "bounded gaps between primes", "")
        self.assertEqual(score, 1.0)
        self.assertIn("matched", why)

    def test_relevance_zero_on_no_overlap(self):
        tokens = cg.tokenize("bounded gaps primes")
        score, why = cg.relevance(tokens, "fibre bundles", "")
        self.assertEqual(score, 0.0)
        self.assertEqual(why, "no keyword overlap")

    def test_relevance_with_empty_obligation(self):
        self.assertEqual(cg.relevance(set(), "anything", "")[0], 0.0)

    def test_reconstruct_abstract_restores_word_order(self):
        inverted = {"bounded": [0], "gaps": [1], "primes": [2]}
        self.assertEqual(cg.reconstruct_abstract(inverted), "bounded gaps primes")

    def test_reconstruct_abstract_handles_missing_index(self):
        self.assertEqual(cg.reconstruct_abstract(None), "")


class SeedResolutionTestCase(unittest.TestCase):
    def test_openalex_id(self):
        self.assertEqual(cg._seed_paths("W2741809807"), ["/works/W2741809807"])

    def test_doi(self):
        self.assertEqual(cg._seed_paths("10.1234/foo"), ["/works/doi:10.1234/foo"])

    def test_arxiv_id_maps_to_arxiv_doi(self):
        self.assertEqual(cg._seed_paths("2103.01234"), [f"/works/doi:{cg.ARXIV_DOI_PREFIX}2103.01234"])

    def test_arxiv_id_strips_version_and_prefix(self):
        self.assertEqual(cg._seed_paths("arxiv:2103.01234v2"), [f"/works/doi:{cg.ARXIV_DOI_PREFIX}2103.01234"])

    def test_short_id_strips_url(self):
        self.assertEqual(cg.short_id("https://openalex.org/W123"), "W123")


class WalkTestCase(unittest.TestCase):
    def setUp(self):
        self.provider = FakeProvider(GRAPH)

    def test_unresolvable_seed_returns_error(self):
        provider = FakeProvider(GRAPH, root="MISSING")
        result = cg.walk("nope", "anything", provider=provider)
        self.assertFalse(result["ok"])

    def test_one_hop_collects_references_and_citations(self):
        result = cg.walk("W1", "bounded gaps primes", hops=1, provider=self.provider)
        self.assertTrue(result["ok"])
        ids = {r["id"] for r in result["results"]}
        self.assertEqual(ids, {"W2", "W3", "W5"})  # refs W2,W3 + citing W5
        self.assertTrue(all(r["hop"] == 1 for r in result["results"]))

    def test_hop_budget_limits_depth(self):
        """W4 is two hops out; it must not appear at hops=1."""
        one = cg.walk("W1", "bounded gaps", hops=1, provider=self.provider)
        self.assertNotIn("W4", {r["id"] for r in one["results"]})
        two = cg.walk("W1", "bounded gaps", hops=2, provider=self.provider)
        self.assertIn("W4", {r["id"] for r in two["results"]})

    def test_results_sorted_by_score_descending(self):
        result = cg.walk("W1", "bounded gaps primes", hops=1, provider=self.provider)
        scores = [r["score"] for r in result["results"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(result["results"][0]["id"], "W2")

    def test_seed_is_not_reported_as_its_own_neighbour(self):
        result = cg.walk("W1", "seed", hops=2, provider=self.provider)
        self.assertNotIn("W1", {r["id"] for r in result["results"]})

    def test_nodes_are_deduplicated_across_hops(self):
        result = cg.walk("W1", "bounded gaps", hops=2, provider=self.provider)
        ids = [r["id"] for r in result["results"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_cycle_does_not_hang(self):
        cyclic = {
            "W1": ("a", "", ["W2"], []),
            "W2": ("b", "", ["W1"], []),
        }
        result = cg.walk("W1", "a", hops=5, provider=FakeProvider(cyclic))
        self.assertTrue(result["ok"])
        self.assertEqual([r["id"] for r in result["results"]], ["W2"])


class FrontierIntegrationTestCase(unittest.TestCase):
    def test_results_merge_into_the_shared_frontier(self):
        """ADR 0018: O1 and O3 share one queue, not two."""
        with tempfile.TemporaryDirectory() as ws:
            frontier.init(ws, "bounded gaps primes", max_depth=2)
            payload = cg.walk("W1", "bounded gaps primes", hops=1, provider=FakeProvider(GRAPH))
            pushed = cg.push_to_frontier(ws, payload, limit=20)
            self.assertEqual(pushed, 3)
            nodes = frontier.load_nodes(ws)
            self.assertTrue(all(n["source"] == "citation-graph" for n in nodes))
            self.assertTrue(all(n["parent"] == "W1" for n in nodes))
            self.assertEqual(frontier.status(ws)["by_source"]["citation-graph"], 3)

    def test_push_limit_is_respected(self):
        with tempfile.TemporaryDirectory() as ws:
            frontier.init(ws, "x", max_depth=2)
            payload = cg.walk("W1", "bounded gaps primes", hops=1, provider=FakeProvider(GRAPH))
            self.assertEqual(cg.push_to_frontier(ws, payload, limit=1), 1)


if __name__ == "__main__":
    unittest.main()
