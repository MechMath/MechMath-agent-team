#!/usr/bin/env python3
"""Tests for ADR 0020 stale-index detection and the completion-gate freshness /
long-term-read checks (P3, P4)."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "cli_tools"))

from _memory import local as mlocal  # noqa: E402
from _gate import completion as completion_gate  # noqa: E402
import memory as memory_facade  # noqa: E402  (the memory.py facade)


class StalenessTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)
        (self.ws / "STATUS.md").write_text("# STATUS\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_no_index_is_stale(self):
        st = mlocal.staleness(self.ws)
        self.assertTrue(st["stale"])
        self.assertIn("STATUS.md", st["newer_than_index"])

    def test_fresh_after_refresh(self):
        mlocal.refresh(self.ws, view="compact")
        st = mlocal.staleness(self.ws)
        self.assertFalse(st["stale"])
        self.assertEqual(st["newer_than_index"], [])

    def test_stale_when_status_newer(self):
        mlocal.refresh(self.ws, view="compact")
        idx = self.ws / "memory" / "index.json"
        future = idx.stat().st_mtime + 100
        os.utime(self.ws / "STATUS.md", (future, future))
        st = mlocal.staleness(self.ws)
        self.assertTrue(st["stale"])
        self.assertIn("STATUS.md", st["newer_than_index"])

    def test_check_does_not_rebuild(self):
        mlocal.refresh(self.ws, view="compact")
        idx = self.ws / "memory" / "index.json"
        past = idx.stat().st_mtime - 100
        os.utime(idx, (past, past))
        out = mlocal.refresh(self.ws, view="compact", check=True)
        self.assertIn("stale", out)
        self.assertEqual(idx.stat().st_mtime, past)  # probe did not rebuild

    def test_index_md_has_freshness_hint(self):
        mlocal.refresh(self.ws, view="compact")
        md = (self.ws / "memory" / "index.md").read_text(encoding="utf-8")
        self.assertIn("refresh --check", md)


class LongtermTraceTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stamp_writes_marker(self):
        ts = memory_facade._stamp_longterm_read(self.ws)
        self.assertIsNotNone(ts)
        marker = self.ws / "memory" / memory_facade.LONGTERM_READ_MARKER
        self.assertTrue(marker.exists())
        self.assertEqual(json.loads(marker.read_text())["read_at_utc"], ts)


class GateFreshnessTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)
        (self.ws / "STATUS.md").write_text("# STATUS\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_no_index_no_freshness_error(self):
        r = completion_gate.GateResult()
        completion_gate.validate_index_freshness(r, self.ws)
        self.assertEqual(r.errors, [])

    def test_stale_index_errors(self):
        mlocal.refresh(self.ws, view="compact")
        idx = self.ws / "memory" / "index.json"
        future = idx.stat().st_mtime + 100
        os.utime(self.ws / "STATUS.md", (future, future))
        r = completion_gate.GateResult()
        completion_gate.validate_index_freshness(r, self.ws)
        self.assertTrue(any("stale" in e for e in r.errors))

    def test_fresh_index_no_error(self):
        mlocal.refresh(self.ws, view="compact")
        r = completion_gate.GateResult()
        completion_gate.validate_index_freshness(r, self.ws)
        self.assertEqual(r.errors, [])

    def test_missing_longterm_marker_warns(self):
        r = completion_gate.GateResult()
        completion_gate.validate_longterm_read(r, self.ws)
        self.assertTrue(any("long-term" in w for w in r.warnings))

    def test_present_longterm_marker_no_warn(self):
        (self.ws / "memory").mkdir(parents=True, exist_ok=True)
        (self.ws / "memory" / ".longterm_read.json").write_text(
            '{"read_at_utc":"x"}', encoding="utf-8"
        )
        r = completion_gate.GateResult()
        completion_gate.validate_longterm_read(r, self.ws)
        self.assertEqual(r.warnings, [])


if __name__ == "__main__":
    unittest.main()
