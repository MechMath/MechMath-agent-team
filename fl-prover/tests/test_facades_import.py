"""Does every facade still start?

On 2026-09-09 a repair commit inserted an import block above `from __future__ import
annotations` in `cli_tools/_control/tasks.py`. That is a SyntaxError, and it killed BOTH
`cli_tools/lean.py` and `cli_tools/control.py` outright — every Lean gate, the whole task
ledger — while `unittest discover -s tests` reported **160 tests passing**, because the
suite imported neither module.

A suite that cannot see the facades is the same defect as a suite that collects 7 of its
172 tests, one layer further out: green means "nothing I looked at is broken", and nobody
had said what it was looking at.

So the facades are now in the suite. Each is imported as a module (which compiles it and
everything it imports) and run with `--help`, which is the cheapest thing that proves the
argument parser is reachable.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "cli_tools"

# Every file directly under cli_tools/ is a facade by this repo's own convention:
# "each the single entry over a cli_tools/_<name>/ package".
FACADES = sorted(p.name for p in CLI.glob("*.py") if not p.name.startswith("_"))


class FacadeImportTest(unittest.TestCase):
    def test_there_are_facades_to_check(self):
        """Guard the guard: an empty list would make every test below vacuous."""
        self.assertGreaterEqual(len(FACADES), 6, f"only found {FACADES}")

    def test_every_facade_compiles(self):
        """Catches the SyntaxError class, including in anything a facade imports."""
        broken = []
        for name in FACADES:
            r = subprocess.run(
                [sys.executable, "-c",
                 f"import sys; sys.path.insert(0, {str(CLI)!r}); "
                 f"import importlib; importlib.import_module({name[:-3]!r})"],
                capture_output=True, text=True, cwd=str(ROOT),
            )
            if r.returncode != 0:
                tail = (r.stderr or "").strip().splitlines()[-1:] or [""]
                broken.append(f"{name}: {tail[0]}")
        self.assertEqual(broken, [], f"facades that will not import: {broken}")

    def test_every_facade_answers_help(self):
        """A parser that cannot be reached is a tool nobody can call."""
        broken = []
        for name in FACADES:
            r = subprocess.run(
                [sys.executable, str(CLI / name), "--help"],
                capture_output=True, text=True, cwd=str(ROOT), timeout=60,
            )
            out = (r.stdout or "") + (r.stderr or "")
            if "Traceback" in out or "SyntaxError" in out:
                broken.append(f"{name}: {out.strip().splitlines()[-1]}")
            elif not out.strip():
                broken.append(f"{name}: --help printed nothing")
        self.assertEqual(broken, [], f"facades whose --help fails: {broken}")

    def test_self_tests_that_exist_still_pass(self):
        """The three modules that carry --self-test must actually pass it."""
        checks = [
            (CLI / "dag.py", ["--self-test"]),
            (CLI / "_lean" / "verdict.py", ["--self-test"]),
            (ROOT / ".claude" / "hooks" / "dispatch_guard.py", ["--self-test"]),
        ]
        broken = []
        for path, args in checks:
            if not path.exists():
                broken.append(f"{path.name}: missing")
                continue
            r = subprocess.run([sys.executable, str(path), *args],
                               capture_output=True, text=True, cwd=str(ROOT), timeout=300)
            if r.returncode != 0:
                broken.append(f"{path.name}: exit {r.returncode} — "
                              f"{((r.stdout or '') + (r.stderr or '')).strip()[-200:]}")
        self.assertEqual(broken, [], f"failing self-tests: {broken}")


if __name__ == "__main__":
    unittest.main()
