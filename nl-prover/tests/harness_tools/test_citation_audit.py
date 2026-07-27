#!/usr/bin/env python3
"""Tests for the final-article citation audit (ADR 0019 §5)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "cli_tools"))

from _gate import citation_audit as ca  # noqa: E402
from _workspace import ledger  # noqa: E402


class Helpers(unittest.TestCase):
    def test_cited_keys_parses_all_cite_forms(self):
        tex = r"\citep{a} \citet[see]{b} \cite{c,d}"
        self.assertEqual(ca.cited_keys(tex), {"a", "b", "c", "d"})

    def test_bib_keys(self):
        self.assertEqual(ca.bib_keys("@article{k1,\n}\n@misc{k2,}"), {"k1", "k2"})

    def test_theorem_blocks_detects_attribution(self):
        tex = r"\begin{theorem}[\citep{x}]body\end{theorem}\begin{lemma}plain\end{lemma}"
        blocks = ca.theorem_blocks(tex)
        self.assertEqual(len(blocks), 2)
        self.assertTrue(blocks[0]["attributed"])
        self.assertFalse(blocks[1]["attributed"])


class AuditTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)
        (self.ws / "references").mkdir(parents=True)
        (self.ws / "writer").mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, tex, bib=""):
        (self.ws / "writer" / "a.tex").write_text(tex, encoding="utf-8")
        (self.ws / "references" / "refs.bib").write_text(bib, encoding="utf-8")

    def test_unresolved_cite_key_fails(self):
        self._write(r"see \citep{ghost}", bib="")
        result = ca.audit(self.ws, "writer/a.tex")
        self.assertFalse(result["ok"])
        self.assertTrue(any("does not resolve" in e for e in result["errors"]))

    def test_cite_as_existing_must_be_cited(self):
        ledger.add_row(self.ws, "L1", paper_id="Z2014")
        ledger.set_trust(self.ws, "L1", trust="cite-as-existing")
        self._write("no citations here", bib="")
        result = ca.audit(self.ws, "writer/a.tex")
        self.assertTrue(any("never cited" in e for e in result["errors"]))

    def test_pending_audit_key_used_as_settled_fails(self):
        ledger.add_row(self.ws, "L1", paper_id="Z2014")   # stays pending-audit
        self._write(r"by \citep{Z2014} we win", bib="@article{Z2014,}")
        result = ca.audit(self.ws, "writer/a.tex")
        self.assertTrue(any("trust" in e and "pending-audit" in e for e in result["errors"]))

    def test_borrowed_key_used_as_settled_fails(self):
        ledger.add_row(self.ws, "L1", paper_id="Z2014")
        ledger.set_trust(self.ws, "L1", trust="borrowed")
        self._write(r"by \citep{Z2014}", bib="@article{Z2014,}")
        result = ca.audit(self.ws, "writer/a.tex")
        self.assertTrue(any("borrowed" in e for e in result["errors"]))

    def test_attribution_detector_flags_unattributed_original(self):
        ledger.add_row(self.ws, "L1", paper_id="Z2014",
                       statement="bounded gaps between consecutive primes exist infinitely",
                       source_quality="original theorem")
        ledger.set_trust(self.ws, "L1", trust="cite-as-existing")
        tex = (r"\begin{theorem}bounded gaps between consecutive primes exist "
               r"infinitely often\end{theorem}")
        self._write(tex, bib="@article{Z2014,}")
        result = ca.audit(self.ws, "writer/a.tex")
        self.assertTrue(any("presented as original" in e for e in result["errors"]))

    def test_attributed_original_passes(self):
        ledger.add_row(self.ws, "L1", paper_id="Z2014",
                       statement="bounded gaps between consecutive primes exist infinitely",
                       source_quality="original theorem")
        ledger.set_trust(self.ws, "L1", trust="cite-as-existing")
        tex = (r"\begin{theorem}[\citet{Z2014}]bounded gaps between consecutive primes "
               r"exist infinitely often\end{theorem}")
        self._write(tex, bib="@article{Z2014,}")
        result = ca.audit(self.ws, "writer/a.tex")
        self.assertTrue(result["ok"], result["errors"])

    def test_clean_article_passes(self):
        ledger.add_row(self.ws, "L1", paper_id="Z2014", statement="some result")
        ledger.set_trust(self.ws, "L1", trust="cite-as-existing")
        self._write(r"As shown in \citet{Z2014}, the claim holds.", bib="@article{Z2014,}")
        result = ca.audit(self.ws, "writer/a.tex")
        self.assertTrue(result["ok"], result["errors"])


if __name__ == "__main__":
    unittest.main()
