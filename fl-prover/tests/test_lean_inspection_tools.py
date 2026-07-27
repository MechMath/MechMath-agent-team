from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cli_tools"))

from _lean import check as lean_check
from _lean import sourcetools as lst


LEAN_SAMPLE = """import Mathlib

/-- docstring sorry admit -/
theorem docstring_ok : True := by
  trivial

/- outer sorry
  /- nested admit -/
-/
def string_ok : String := "sorry admit"

lemma target_one (n : Nat) : n = n := by
  sorry

theorem target_two : True := by
  admit
"""


class LeanInspectionToolsTest(unittest.TestCase):
    def test_sorry_scan_ignores_comments_docstrings_and_strings(self) -> None:
        hits = lst.find_tokens(LEAN_SAMPLE, ["sorry", "admit"])
        starts = lst.line_starts(LEAN_SAMPLE)
        locations = [(token, lst.offset_to_line_col(starts, offset)) for token, offset in hits]
        self.assertEqual(locations, [("sorry", (13, 3)), ("admit", (16, 3))])

    def test_declarations_and_statement_extraction(self) -> None:
        declarations = lst.find_declarations(LEAN_SAMPLE)
        names = [decl.name for decl in declarations]
        self.assertEqual(names, ["docstring_ok", "string_ok", "target_one", "target_two"])

        target = next(decl for decl in declarations if decl.name == "target_one")
        statement = LEAN_SAMPLE[target.statement_start:target.statement_end].strip()
        self.assertEqual(statement, "lemma target_one (n : Nat) : n = n")

    def test_diagnostic_filtering_by_severity_and_line_range(self) -> None:
        messages = [
            {"severity": "error", "line": 10, "column": 1, "data": "bad"},
            {"severity": "warning", "line": 12, "column": 1, "data": "warn"},
            {"severity": "error", "line": 30, "column": 1, "data": "bad2"},
        ]
        filtered = lean_check.filter_messages(
            messages,
            severities=["error"],
            line_start=1,
            line_end=20,
        )
        self.assertEqual(filtered, [messages[0]])


if __name__ == "__main__":
    unittest.main()
