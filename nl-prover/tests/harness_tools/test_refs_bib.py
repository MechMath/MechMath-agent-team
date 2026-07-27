#!/usr/bin/env python3
"""Tests for the refs.bib generator (ADR 0019 §4). No network — fake provider."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "cli_tools"))

from _workspace import ledger  # noqa: E402
from _workspace import refs_bib  # noqa: E402


class FakeProvider(refs_bib.BibtexProvider):
    def __init__(self, by_doi_map):
        self._map = by_doi_map

    def by_doi(self, doi):
        return self._map.get(refs_bib._clean_doi(doi))


class RefsBibTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_fetches_real_bibtex_when_doi_resolves(self):
        ledger.add_row(self.ws, "L1", paper_id="Z2014", doi="10.1/z")
        provider = FakeProvider({"10.1/z": "@article{orig, title={Bounded gaps}}"})
        result = refs_bib.build(self.ws, provider=provider)
        self.assertEqual(result["fetched"], ["Z2014"])
        bib = (self.ws / "references" / "refs.bib").read_text()
        self.assertIn("@article{Z2014,", bib)   # rekeyed to our cite_key
        self.assertNotIn("orig", bib)

    def test_synthesizes_when_no_doi(self):
        ledger.add_row(self.ws, "L1", paper_id="Z2014", statement="bounded gaps result")
        result = refs_bib.build(self.ws, provider=FakeProvider({}))
        self.assertEqual(result["synthesized"], ["Z2014"])
        self.assertEqual(result["missing"], [])
        bib = (self.ws / "references" / "refs.bib").read_text()
        self.assertIn("@misc{Z2014", bib)
        self.assertIn("bounded gaps result", bib)

    def test_doi_present_but_unresolvable_is_missing_not_todo(self):
        ledger.add_row(self.ws, "L1", paper_id="Z2014", doi="10.1/gone")
        result = refs_bib.build(self.ws, provider=FakeProvider({}))
        self.assertEqual(result["missing"], ["Z2014"])
        bib = (self.ws / "references" / "refs.bib").read_text()
        self.assertNotIn("TODO", bib)
        self.assertIn("@misc{Z2014", bib)   # still a real (sparse) entry

    def test_updates_cite_key_in_ledger(self):
        ledger.add_row(self.ws, "L1", paper_id="Z2014")
        refs_bib.build(self.ws, provider=FakeProvider({}))
        self.assertEqual(ledger.get(self.ws, "L1")["cite_key"], "Z2014")

    def test_one_entry_per_cite_key_across_claims(self):
        ledger.add_row(self.ws, "L1", paper_id="Z2014")
        ledger.add_row(self.ws, "L2", paper_id="Z2014")   # same paper, two claims
        result = refs_bib.build(self.ws, provider=FakeProvider({}))
        self.assertEqual(result["entries"], 1)

    def test_clean_doi_strips_url(self):
        self.assertEqual(refs_bib._clean_doi("https://doi.org/10.1/x"), "10.1/x")

    def test_rekey_replaces_citation_key(self):
        out = refs_bib._rekey("@article{whatever, title={t}}", "MYKEY")
        self.assertIn("@article{MYKEY,", out)


if __name__ == "__main__":
    unittest.main()
