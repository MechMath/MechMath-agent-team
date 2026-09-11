#!/usr/bin/env python3
"""A gate's answer must not depend on how it was asked to print.

`gate dag` and `gate speed` suppressed their prose epilogue under `--json`, because
prose after a JSON document makes the document unparseable exactly when it carries
something to report. The `return 1` sat inside that suppression, so the same failing
workspace exited 1 in text and 0 in JSON — and `--json` is the mode a script runs.
No test covered `--json` with errors, which is why it survived.

`workspace.py` had the sibling shape: its dispatch table returned a code the facade
threw away, so `workspace.py status X` reported success for a path that running
`_workspace/status.py X` directly reported as a failure.
"""
import io
import contextlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "cli_tools"))

from _gate import dag, speed  # noqa: E402


def run_gate(module, argv):
    """Return (exit code, stdout). The gate mains answer an int rather than exiting."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = module.main(argv)
    return rc, out.getvalue()


class VerdictSurvivesJsonTestCase(unittest.TestCase):
    """The mode changes the rendering. It must not change the verdict."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.missing = str(Path(self._tmp.name) / "no-such-workspace")

    def tearDown(self):
        self._tmp.cleanup()

    def test_dag_reports_the_same_verdict_in_both_modes(self):
        text_rc, _ = run_gate(dag, [self.missing])
        json_rc, out = run_gate(dag, [self.missing, "--json"])
        self.assertEqual(text_rc, 1)
        self.assertEqual(json_rc, 1, "--json reported success for a workspace text failed on")
        self.assertFalse(json.loads(out)["ok"])

    def test_speed_reports_the_same_verdict_in_both_modes(self):
        text_rc, _ = run_gate(speed, [self.missing])
        json_rc, out = run_gate(speed, [self.missing, "--json"])
        self.assertEqual(text_rc, 1)
        self.assertEqual(json_rc, 1, "--json reported success for a workspace text failed on")
        self.assertFalse(json.loads(out)["ok"])

    def test_json_output_is_still_a_single_parseable_document(self):
        """The suppression the verdict was tangled in is still doing its own job."""
        for module in (dag, speed):
            with self.subTest(gate=module.__name__):
                _, out = run_gate(module, [self.missing, "--json"])
                json.loads(out)  # raises if the epilogue leaked back in


class FacadePropagatesTestCase(unittest.TestCase):
    """Running through the facade and running the module must answer alike."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.empty = Path(self._tmp.name) / "empty"
        self.empty.mkdir()
        self.absent = Path(self._tmp.name) / "absent"

    def tearDown(self):
        self._tmp.cleanup()

    def _both(self, target):
        facade = subprocess.run(
            [sys.executable, str(REPO / "cli_tools/workspace.py"), "status", str(target)],
            capture_output=True, cwd=REPO,
        )
        direct = subprocess.run(
            [sys.executable, str(REPO / "cli_tools/_workspace/status.py"), str(target)],
            capture_output=True, cwd=REPO,
        )
        return facade.returncode, direct.returncode

    def test_a_workspace_without_a_status_file_fails_through_the_facade(self):
        facade, direct = self._both(self.empty)
        self.assertEqual(facade, direct)
        self.assertNotEqual(facade, 0)

    def test_a_path_that_is_not_a_directory_fails_through_the_facade(self):
        facade, direct = self._both(self.absent)
        self.assertEqual(facade, direct)
        self.assertNotEqual(facade, 0)


class ProseMatchesCodeTestCase(unittest.TestCase):
    """Four places said these gates exit 0. A test asserting the code's behaviour is
    what keeps that sentence from being written again."""

    def test_no_file_still_claims_these_gates_always_exit_zero(self):
        stale = "exit 0 and stop nothing"
        for name in ("CLAUDE.md", "AGENTS.md"):
            with self.subTest(file=name):
                self.assertNotIn(stale, (REPO / name).read_text(encoding="utf-8"))

    def test_no_gate_module_still_claims_it_exits_zero_unless_strict(self):
        stale = "exit code stays 0 unless --strict"
        for name in ("dag", "speed"):
            with self.subTest(gate=name):
                text = (REPO / f"cli_tools/_gate/{name}.py").read_text(encoding="utf-8")
                self.assertNotIn(stale, text)


if __name__ == "__main__":
    unittest.main()
