"""The four normative sections exist once, or they will diverge again.

`CLAUDE.md` said, in writing: its normative content "is identical to `AGENTS.md` and must
stay in sync with it". Measured 2026-09-09, the two files differed by **465 diff lines**,
and the four sections that sentence names differed by 34, 73, 54 and 8. Nothing checked
it, and no check was possible: a claim of identity between two hand-maintained copies is a
claim about the future.

The divergence was elaboration, not contradiction — the Claude copy had grown detail the
Codex copy never got. That is the worse shape, because both harnesses believed they were
reading the same rules and one of them was reading a summary.

So the four sections now live in `prompts/normative.md` and this test makes that stick.
It is a test rather than a gate on purpose: gates in this repo were invoked 8 times in
174 hours, and the suite runs.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NORMATIVE = ("Core Invariants", "Routing", "Tool Rules", "Rules for All Agents")
ENTRY = ("CLAUDE.md", "AGENTS.md")
SOURCE = "prompts/normative.md"


def headings(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^## (.+)$", text, re.MULTILINE)]


class NormativeSingleSourceTest(unittest.TestCase):
    def test_the_single_source_exists_and_holds_all_four(self):
        p = ROOT / SOURCE
        self.assertTrue(p.exists(), f"{SOURCE} is missing; the four sections have no home")
        hs = headings(p.read_text(encoding="utf-8"))
        for n in NORMATIVE:
            self.assertIn(n, hs, f"{SOURCE} does not define '{n}'")

    def test_neither_entry_document_restates_a_normative_section(self):
        """This is the regression guard. A copy is how it drifted the first time."""
        for name in ENTRY:
            hs = headings((ROOT / name).read_text(encoding="utf-8"))
            clash = [n for n in NORMATIVE if n in hs]
            self.assertEqual(
                clash, [],
                f"{name} has grown back {clash}. Those sections belong only in {SOURCE}; "
                "two hand-maintained copies drifted 465 lines apart last time, while this "
                "file claimed they were identical.",
            )

    def test_both_entry_documents_point_at_the_single_source(self):
        for name in ENTRY:
            t = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn(
                SOURCE, t,
                f"{name} does not point at {SOURCE}, so an agent reading only {name} "
                "never reaches the normative rules.",
            )

    def test_read_first_requires_the_prompts_set_that_contains_it(self):
        """The pointer only works if the agent was already going to read prompts/."""
        for name in ENTRY:
            t = (ROOT / name).read_text(encoding="utf-8")
            self.assertRegex(
                t, r"prompts/(\*\.md|normative\.md)",
                f"{name} must require the prompts/ set (or normative.md by name) in "
                "`## Read First`, or the single source is merely a link nobody follows.",
            )

    def test_the_single_source_carries_no_platform_specific_dispatch(self):
        """Dispatch mechanics belong in the entry documents, or the split is fake."""
        t = (ROOT / SOURCE).read_text(encoding="utf-8")
        for token in ("Task tool", ".codex/agents/", "hookSpecificOutput"):
            self.assertNotIn(
                token, t,
                f"{SOURCE} mentions {token!r}, which is platform-specific dispatch and "
                "belongs in CLAUDE.md / AGENTS.md.",
            )


    def test_no_entry_document_claims_to_mirror_the_other(self):
        """The sentence that made the drift invisible must not come back.

        A change-reviewer found that after the sections were moved, BOTH files still said
        their normative content was "identical to" the other and "must stay in sync" —
        now describing content that no longer existed in either. The claim of identity
        between two hand-maintained copies is the defect; deleting the copies without
        deleting the claim leaves an instruction to synchronise nothing.
        """
        for name in ENTRY:
            for line in (ROOT / name).read_text(encoding="utf-8").splitlines():
                low = line.lower()
                if "identical to" in low and "must stay in sync" in low:
                    self.assertIn(
                        "until 2026-09-09", low,
                        f"{name} claims its normative content is identical to the other "
                        f"file and must be kept in sync: {line.strip()!r}. There is one "
                        "copy now; only the historical note may mention the old claim.",
                    )

    def test_an_entry_document_does_not_restate_normative_rules_under_another_heading(self):
        """Divergence by restatement, which the heading check cannot see.

        The reviewer appended `## Core rules (Claude harness)` with two invariant bullets
        to AGENTS.md and the suite stayed green. Headings drift; the giveaway is the
        normative vocabulary appearing in bulk outside the single source.
        """
        markers = ("must never", "must not", "never spawn", "no `sorry`", "no sorry",
                   "at most", "is mandatory", "is forbidden")
        for name in ENTRY:
            body = (ROOT / name).read_text(encoding="utf-8")
            # Dispatch mechanics legitimately carry a few imperatives; a normative BODY
            # carries many. Eight was the count in the pre-split files; four is headroom.
            hits = sum(body.lower().count(m) for m in markers)
            self.assertLessEqual(
                hits, 6,
                f"{name} carries {hits} normative imperatives. Those rules belong in "
                f"{SOURCE}; this file is for dispatch mechanics. If a rule genuinely is "
                "platform-specific, say so explicitly and raise this bound with a reason.",
            )


if __name__ == "__main__":
    unittest.main()
