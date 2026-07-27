#!/usr/bin/env python3
"""Tests for the provenance ledger (ADR 0019 §1)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "cli_tools"))

from _workspace import ledger  # noqa: E402


class LedgerTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_add_defaults_to_pending_audit(self):
        result = ledger.add_row(self.ws, "L1", paper_id="Z2014", source_quality="original theorem")
        self.assertTrue(result["ok"])
        self.assertEqual(result["row"]["trust"], "pending-audit")

    def test_add_is_idempotent_and_updates_provenance(self):
        ledger.add_row(self.ws, "L1", paper_id="Z2014")
        r = ledger.add_row(self.ws, "L1", locator="Thm 3.2")
        self.assertFalse(r["created"])
        row = ledger.get(self.ws, "L1")
        self.assertEqual(row["paper_id"], "Z2014")
        self.assertEqual(row["locator"], "Thm 3.2")
        self.assertEqual(len(ledger.load_rows(self.ws)), 1)

    def test_add_requires_claim_id(self):
        self.assertFalse(ledger.add_row(self.ws, "")["ok"])

    def test_add_rejects_bad_source_quality(self):
        self.assertFalse(ledger.add_row(self.ws, "L1", source_quality="made up")["ok"])

    def test_add_does_not_reset_existing_verdict(self):
        ledger.add_row(self.ws, "L1", paper_id="Z2014")
        ledger.set_trust(self.ws, "L1", trust="cite-as-existing")
        ledger.add_row(self.ws, "L1", locator="Thm 1")  # Searcher touches provenance again
        self.assertEqual(ledger.get(self.ws, "L1")["trust"], "cite-as-existing")

    def test_set_trust_writes_verdict(self):
        ledger.add_row(self.ws, "L1")
        r = ledger.set_trust(self.ws, "L1", trust="borrowed", audit_status="needs-local-derivation",
                             independent_warrant="UNCLEAR")
        self.assertTrue(r["ok"])
        row = ledger.get(self.ws, "L1")
        self.assertEqual(row["trust"], "borrowed")
        self.assertEqual(row["audit_status"], "needs-local-derivation")
        self.assertEqual(row["independent_warrant"], "UNCLEAR")

    def test_set_trust_rejects_bad_level(self):
        ledger.add_row(self.ws, "L1")
        self.assertFalse(ledger.set_trust(self.ws, "L1", trust="trusted")["ok"])

    def test_set_trust_unknown_claim(self):
        self.assertFalse(ledger.set_trust(self.ws, "nope", trust="borrowed")["ok"])

    def test_set_cite_key(self):
        ledger.add_row(self.ws, "L1")
        ledger.set_cite_key(self.ws, "L1", "Z2014")
        self.assertEqual(ledger.get(self.ws, "L1")["cite_key"], "Z2014")

    def test_validate_flags_duplicate_claim_id(self):
        path = ledger.ledger_path(self.ws)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            '{"claim_id": "L1", "trust": "pending-audit"}\n'
            '{"claim_id": "L1", "trust": "pending-audit"}\n',
            encoding="utf-8",
        )
        result = ledger.validate(self.ws)
        self.assertFalse(result["ok"])
        self.assertTrue(any("duplicate" in e for e in result["errors"]))

    def test_validate_flags_bad_trust(self):
        path = ledger.ledger_path(self.ws)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"claim_id": "L1", "trust": "bogus"}\n', encoding="utf-8")
        self.assertFalse(ledger.validate(self.ws)["ok"])

    def test_load_rows_raises_on_malformed(self):
        path = ledger.ledger_path(self.ws)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            ledger.load_rows(self.ws)

    def test_status_counts_by_trust(self):
        ledger.add_row(self.ws, "L1")
        ledger.add_row(self.ws, "L2")
        ledger.set_trust(self.ws, "L2", trust="cite-as-existing")
        report = ledger.status(self.ws)
        self.assertEqual(report["by_trust"]["pending-audit"], 1)
        self.assertEqual(report["by_trust"]["cite-as-existing"], 1)
        self.assertEqual(report["pending"], ["L1"])

    def test_cli_roundtrip(self):
        ledger.main(["add", str(self.ws), "--claim-id", "L1", "--paper-id", "Z2014"])
        ledger.main(["set-trust", str(self.ws), "--claim-id", "L1", "--trust", "cite-as-existing"])
        self.assertEqual(ledger.get(self.ws, "L1")["trust"], "cite-as-existing")


if __name__ == "__main__":
    unittest.main()
