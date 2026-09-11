from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cli_tools"))

from _lean import axioms as lean_axioms
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

ASSUMPTION_SAMPLE = """import Mathlib

namespace Demo

-- a comment naming axiom and opaque is not a declaration
axiom assumed_fact (n : Nat) : n = n

noncomputable opaque sealed : Nat -> Nat

structure Bundle where
  carrier : Nat

end Demo
"""


class DeclaredAssumptionAuditTest(unittest.TestCase):
    """The half of the audit the kernel cannot answer.

    `#print axioms` only speaks about theorems, and only about what they *depend on*.
    These declarations are assumptions nothing has to consume.
    """

    def sample(self) -> Path:
        import tempfile

        path = Path(tempfile.mkdtemp()) / "Sample.lean"
        path.write_text(ASSUMPTION_SAMPLE, encoding="utf-8")
        return path

    def test_axiom_and_opaque_are_reported_with_qualified_names(self) -> None:
        found = lean_axioms.declared_assumptions(self.sample())
        self.assertEqual(
            [(item["kind"], item["declaration"]) for item in found],
            [("axiom", "Demo.assumed_fact"), ("opaque", "Demo.sealed")],
        )

    def test_a_file_of_only_assumptions_does_not_pass(self) -> None:
        # It used to: no theorem to audit meant an unconditional okay.
        result = lean_axioms.audit(self.sample())
        self.assertFalse(result["okay"])
        self.assertEqual(len(result["declared_assumptions"]), 2)

    def test_allow_accepts_an_approved_assumption_by_short_or_full_name(self) -> None:
        for name in ("assumed_fact", "Demo.assumed_fact"):
            result = lean_axioms.audit(self.sample(), allowed=[name, "Demo.sealed"])
            self.assertTrue(result["okay"], name)

    def test_allow_extends_the_classical_base_rather_than_replacing_it(self) -> None:
        result = lean_axioms.audit(self.sample(), allowed=["Demo.assumed_fact", "Demo.sealed"])
        self.assertIn("propext", result["allowed"])
        replaced = lean_axioms.audit(self.sample(), allow_only=["Demo.assumed_fact", "Demo.sealed"])
        self.assertNotIn("propext", replaced["allowed"])


if __name__ == "__main__":
    unittest.main()
