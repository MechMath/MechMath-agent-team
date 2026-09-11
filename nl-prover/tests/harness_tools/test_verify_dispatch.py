"""The verification dispatch assembler.

Every test here fixes something the dispatch must or must not be able to carry.
The measured baseline these exist against: over 87 verification dispatches, 100%
claimed the Verifier was a fresh independent referee and 84% supplied, in the
same prompt, the thing independence excludes; 48% named a budget; 1% named a
stopping condition.
"""

import importlib.util
from pathlib import Path
import sys
import unittest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "cli_tools"))
from _verify.dispatch import (  # noqa: E402
    Dependency,
    Dispatch,
    DispatchError,
    anchoring_matches,
)


def make(**overrides):
    fields = dict(
        region="certification",
        verification_mode="lemma",
        artifact="lemmas/branch/leaf/generator/proof_v3.md",
        statement="lemmas/branch/leaf/statement.md",
        problem="problem.md",
        output_dir="lemmas/branch/leaf/verifier",
        version=3,
    )
    fields.update(overrides)
    return Dispatch(**fields)


class DispatchShapeTests(unittest.TestCase):
    def test_it_renders_from_paths_alone(self):
        text = make().render()
        self.assertIn("lemmas/branch/leaf/generator/proof_v3.md", text)
        self.assertIn("mode: certification", text)
        self.assertIn("resume: false", text)

    def test_resume_is_pinned_and_is_not_a_parameter(self):
        """The specialist may not decide resume: given the choice it will always
        prefer more context, and the anti-anchoring cases lose their enforcer."""
        self.assertNotIn("resume", Dispatch.__dataclass_fields__)
        self.assertIn("resume: false", make().render())

    def test_a_dependency_carries_a_state_and_not_a_reason(self):
        text = make(
            dependencies=[Dependency("lemmas/branch/dep/statement.md", "NEEDS_REVISION")]
        ).render()
        self.assertIn("lemmas/branch/dep/statement.md — NEEDS_REVISION", text)

    def test_a_dependency_state_outside_the_enum_is_refused(self):
        with self.assertRaises(DispatchError):
            Dependency.parse("lemmas/d/statement.md:rejected because step 6 is wrong")

    def test_no_field_can_carry_free_text(self):
        """The whole claim: there is nowhere to put a prior verdict."""
        allowed = set(Dispatch.__dataclass_fields__)
        self.assertEqual(
            set(),
            allowed & {"context", "hint", "focus", "note", "summary", "concerns"},
        )

    def test_a_budget_and_a_stopping_condition_are_always_present(self):
        text = make().render()
        self.assertIn("Budget: 30 minutes", text)
        self.assertIn("Stop when:", text)

    def test_a_stopping_condition_outside_the_enum_is_refused(self):
        with self.assertRaises(DispatchError):
            make(stop_when="when you feel it is done").render()

    def test_output_paths_are_versioned(self):
        out = make(version=7).output_paths()
        self.assertTrue(out["review_packet"].endswith("review_packet_v7.md"))
        self.assertTrue(out["verdict"].endswith("verdict_v7.md"))

    def test_the_assembled_text_carries_no_anchoring_content(self):
        for region in ("certification", "discovery"):
            for mode in ("lemma", "plan_logic", "global_refinement", "target_obstruction"):
                text = make(region=region, verification_mode=mode).render()
                self.assertEqual([], anchoring_matches(text), (region, mode))

    def test_the_guard_would_catch_it_if_it_did(self):
        """A guard that cannot fire is not a guard."""
        self.assertTrue(anchoring_matches("Prior verdict: three rounds, all NEEDS_REVISION"))
        self.assertTrue(anchoring_matches("The generator reports that step 6 is fine"))

    def test_a_disclaimer_would_trip_the_classifier_so_there_is_none(self):
        """'A disclaimer does not neutralise anchoring content' — and naming what
        it excludes scores the dispatch anchored however clean it is."""
        text = make().render()
        self.assertNotIn("does not contain", text)
        self.assertNotIn("no prior verdict", text.lower())


class ClassifierAgreementTests(unittest.TestCase):
    """The dispatch is scored by the hook's classifier, not a copy of it."""

    def setUp(self):
        hook = REPO_ROOT / ".claude" / "hooks" / "dispatch_log.py"
        spec = importlib.util.spec_from_file_location("_dispatch_log_under_test", hook)
        self.hook = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.hook)

    def test_the_assembled_dispatch_scores_unanchored_and_budgeted(self):
        shape = self.hook.classify_prompt(make().render())
        self.assertFalse(shape["generator_framing"])
        self.assertFalse(shape["prior_verdict"])
        self.assertTrue(shape["budget"])
        self.assertTrue(shape["stopping_condition"])


if __name__ == "__main__":
    unittest.main()
