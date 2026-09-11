"""The ordering rule must be reachable from the files that hand it over.

`prompts/sketcher.md` says scheduling "belongs to the Orchestrator" — and no Orchestrator
file received it. A handoff to nobody is invisible: both ends read as correct, and the
rule simply does not exist. These assert the ends meet.
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REF = REPO / ".agents/skills/nl-prover/references"
HARDEST = REF / "hardest-first.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def flat(path: Path) -> str:
    """Line wrapping is formatting; the sentence is the content."""
    return re.sub(r"\s+", " ", read(path))


class ReachabilityTestCase(unittest.TestCase):
    def test_the_reference_exists(self):
        self.assertTrue(HARDEST.is_file())

    def test_the_skill_index_lists_it(self):
        self.assertIn("hardest-first.md", read(REPO / ".agents/skills/nl-prover/SKILL.md"))

    def test_the_sketcher_hands_scheduling_somewhere_that_exists(self):
        text = read(REPO / "prompts/sketcher.md")
        self.assertIn("belongs to the Orchestrator", text)
        self.assertIn("hardest-first.md", text)

    def test_the_orchestrator_cookbook_receives_it(self):
        text = read(REF / "orchestrator-cookbook.md")
        self.assertIn("hardest-first.md", text)
        self.assertIn("Contribution", text)

    def test_the_synthesizer_carries_its_two_dimensions_across_the_boundary(self):
        text = read(REPO / "prompts/synthesizer.md")
        self.assertIn("sub-parts", text)
        self.assertIn("hardest-first.md", text)

    def test_every_repo_reference_the_new_file_names_exists(self):
        """Only paths. `STATUS.md` and `proof.tex` are workspace artifacts and live
        nowhere in the repository."""
        for rel in re.findall(r"`([^`]+/[^`]+\.md)`", read(HARDEST)):
            with self.subTest(reference=rel):
                self.assertTrue((REPO / rel).is_file(), f"{rel} is named and does not exist")


class InvariantTestCase(unittest.TestCase):
    def invariant(self, path, n):
        text = read(REPO / path)
        m = re.search(rf"^{n}\.\s+(.*?)(?=^\d+\.\s|^## )", text, re.S | re.M)
        return re.sub(r"\s+", " ", m.group(1)).strip() if m else None

    def test_both_platforms_carry_it(self):
        claude, agents = self.invariant("CLAUDE.md", 19), self.invariant("AGENTS.md", 19)
        self.assertIsNotNone(claude, "CLAUDE.md has no invariant 19")
        self.assertEqual(claude, agents)

    def test_it_does_not_ask_for_a_queue(self):
        """The cookbook's batch rule is correct and this must not contradict it."""
        text = self.invariant("CLAUDE.md", 19)
        self.assertIn("does not make a queue", text)
        self.assertIn("one batch", text)

    def test_the_cookbook_still_dispatches_everything_independent(self):
        text = read(REF / "orchestrator-cookbook.md")
        self.assertIn("Dispatch every independent blocker in one batch", text)
        self.assertIn("what is blocked *right now*", text)


class BanTestCase(unittest.TestCase):
    """`how checkable it looks` is the easy-first proxy, and the Synthesizer already
    bans ranking by it. The ban has to travel with the rule."""

    def test_the_ban_is_stated_where_the_rule_is_applied(self):
        for path in (HARDEST, REF / "orchestrator-cookbook.md"):
            with self.subTest(file=path.name):
                self.assertIn("checkable it looks", flat(path))

    def test_the_synthesizer_still_states_it(self):
        self.assertIn("How checkable it looks", flat(REPO / "prompts/synthesizer.md"))


if __name__ == "__main__":
    unittest.main()
