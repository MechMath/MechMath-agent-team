import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_TOOLS = REPO_ROOT / "cli_tools"
sys.path.insert(0, str(CLI_TOOLS))


def load_tool(name):
    module_path = CLI_TOOLS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


from _memory import cardlint as lint


GOOD = """---
type: experience
kind: negative-constraint
id: neg-zero-div
statement: Do not divide by a possibly-zero leading coefficient.
trigger: polynomial division step
refs: [[Concept_Polynomials]]
---
Do not divide by a possibly-zero leading coefficient.
"""

INLINE_FACT = """---
type: experience
kind: negative-constraint
id: neg-bad
statement: Use the theorem below
trigger: something
---
Theorem (Banach): every contraction on a complete metric space has a unique fixed point.
"""


class ExperienceCardLintTests(unittest.TestCase):
    def _write(self, tmp, text):
        p = Path(tmp) / "card.md"
        p.write_text(text, encoding="utf-8")
        return p

    def test_good_card_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual([], lint.lint_experience_card(self._write(tmp, GOOD)))

    def test_inline_theorem_without_refs_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors = lint.lint_experience_card(self._write(tmp, INLINE_FACT))
            self.assertTrue(any("inline a theorem" in e for e in errors))

    def test_missing_trigger_is_rejected(self):
        card = GOOD.replace("trigger: polynomial division step\n", "")
        with tempfile.TemporaryDirectory() as tmp:
            errors = lint.lint_experience_card(self._write(tmp, card))
            self.assertTrue(any("trigger" in e for e in errors))

    def test_fact_content_with_constraint_language_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "note.md"
            p.write_text("# Concept_Foo\n\nThe bound holds. Do not apply it when n is odd.\n", encoding="utf-8")
            errors = lint.lint_fact_content(p)
            self.assertTrue(any("behavioral-constraint language" in e for e in errors))

    def test_clean_fact_content_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "note.md"
            p.write_text("# Concept_Foo\n\nThe spectral bound holds for all n.\n", encoding="utf-8")
            self.assertEqual([], lint.lint_fact_content(p))


if __name__ == "__main__":
    unittest.main()
