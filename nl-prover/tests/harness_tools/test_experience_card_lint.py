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
from _memory import experience as cardlib


GOOD = """---
type: experience
kind: negative-constraint
id: neg-zero-div
statement: Do not divide by a possibly-zero leading coefficient.
trigger: polynomial division step
why: the leading coefficient may vanish for special parameter values
failure_modes: over-flags once nonzero has already been established upstream
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
why: because
failure_modes: none known
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

    def test_missing_why_is_rejected(self):
        card = GOOD.replace(
            "why: the leading coefficient may vanish for special parameter values\n", ""
        )
        with tempfile.TemporaryDirectory() as tmp:
            errors = lint.lint_experience_card(self._write(tmp, card))
            self.assertTrue(any("why" in e for e in errors), errors)

    def test_missing_failure_modes_is_rejected(self):
        """A card the reader cannot argue with. One that cannot say when it
        itself misleads is one nobody can ever argue with."""
        card = GOOD.replace(
            "failure_modes: over-flags once nonzero has already been established upstream\n", ""
        )
        with tempfile.TemporaryDirectory() as tmp:
            errors = lint.lint_experience_card(self._write(tmp, card))
            self.assertTrue(any("failure_modes" in e for e in errors), errors)

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

class CardIdPrefixTests(unittest.TestCase):
    """The id must follow the kind.

    It was hardcoded `neg-`, so all 82 cards in the corpus carry a `neg-` id and
    25 of them are `transferable-idea`. A whole round then recorded "82 cards,
    all negative-constraint" in a diagnosis, a commit message, a module
    docstring and an E4 item saying `transferable-idea` had never been used —
    because the id was read instead of the field, and the id agreed with itself.
    """

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, **fields):
        base = {
            "kind": "negative-constraint",
            "statement": "Do not read the identifier instead of the field",
            "scope": "class-level",
            "trigger": "any",
            "why": "because",
            "failure_modes": "when the identifier is right by accident",
        }
        base.update(fields)
        return cardlib.write_card(base, root=self.root)

    def test_a_negative_constraint_gets_a_neg_id(self):
        self.assertTrue(self.write().name.startswith("Experience_neg-"))

    def test_a_transferable_idea_does_not(self):
        path = self.write(kind="transferable-idea")
        self.assertTrue(path.name.startswith("Experience_idea-"), path.name)

    def test_an_explicit_id_is_never_rewritten(self):
        """An id is a reference. Renaming the 25 mislabelled cards would break
        every citation of them; the mislabelling is historical and stays."""
        path = self.write(kind="transferable-idea", id="neg-an-old-card")
        self.assertEqual("Experience_neg-an-old-card.md", path.name)


if __name__ == "__main__":
    unittest.main()
