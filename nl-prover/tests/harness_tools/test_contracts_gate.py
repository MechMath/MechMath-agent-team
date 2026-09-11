"""Contracts gate: prose checked against the code, on a synthetic repo.

Every fixture here builds a miniature repository rather than asserting against
the real one, so these tests keep meaning after the real seams are fixed. A test
that asserts "the repo currently has 12 gate subcommands" is a test that fails
the next time someone adds one, which teaches people to delete tests.
"""

from pathlib import Path
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "cli_tools"))
from _gate import contracts as contracts_gate


class Fixture:
    """A minimal harness repo: three facades, two gates, two skills."""

    def __init__(self, root: Path):
        self.root = root
        (root / "cli_tools" / "_gate").mkdir(parents=True)
        for name in ("memory", "gate", "search"):
            (root / "cli_tools" / f"{name}.py").write_text("", encoding="utf-8")
        (root / "cli_tools" / "_private.py").write_text("", encoding="utf-8")
        (root / "cli_tools" / "gate.py").write_text(
            'DISPATCH = {\n    "complete": a,\n    "stop": b,\n}\n', encoding="utf-8"
        )
        (root / "cli_tools" / "_gate" / "speed.py").write_text(
            "DECLARED_CONCURRENCY = 6\n", encoding="utf-8"
        )
        (root / "cli_tools" / "memory.py").write_text(
            "if args.workspace:\n    _stamp_longterm_read(x)\n", encoding="utf-8"
        )
        for name in ("alpha", "beta"):
            skill = root / ".agents" / "skills" / name
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("# s\n", encoding="utf-8")
        (root / ".codex").mkdir()
        # A well-formed harness enforces invariant 2 on both platforms. The base
        # fixture carries both enforcement points so that a test about facade
        # counts is not also a test about nesting.
        (root / ".codex" / "config.toml").write_text(
            "[agents]\nmax_threads = 6\nmax_depth = 1\n", encoding="utf-8"
        )
        (root / ".claude").mkdir(exist_ok=True)
        (root / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
        (root / ".claude" / "hooks" / "nesting_guard.py").write_text("# guard\n", encoding="utf-8")
        (root / ".claude" / "settings.json").write_text(
            '{"hooks": {"PreToolUse": [{"matcher": "Agent|Task", "hooks": '
            '[{"type": "command", "command": ".claude/hooks/nesting_guard.py"}]}]}}',
            encoding="utf-8",
        )
        cookbook = root / ".agents" / "skills" / "nl-prover" / "references"
        cookbook.mkdir(parents=True)
        (cookbook / "orchestrator-cookbook.md").write_text(
            "Dispatch every independent blocker. Up to **6** at once.\n", encoding="utf-8"
        )
        (root / ".agents" / "skills" / "nl-prover" / "SKILL.md").write_text(
            "# nl-prover\n", encoding="utf-8"
        )
        self.write("AGENTS.md", "# A\n")
        self.write("CLAUDE.md", "# C\n")

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


class ContractsGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.fixture = Fixture(Path(self.temp.name))

    def audit(self):
        return contracts_gate.audit(Path(self.temp.name))

    # --- the clean case ---------------------------------------------------

    def test_a_repo_that_says_nothing_about_itself_has_nothing_to_disagree_with(self):
        result = self.audit()
        self.assertEqual([], result.errors)

    def test_the_ground_truths_are_read_from_the_code(self):
        result = self.audit()
        self.assertEqual(
            ["gate", "memory", "search"], result.contracts["facades"]["truth"]
        )
        self.assertEqual(6, result.contracts["concurrency"]["speed.py DECLARED_CONCURRENCY"])

    def test_a_private_module_is_not_a_facade(self):
        self.assertNotIn("_private", self.audit().contracts["facades"]["truth"])

    # --- counted lists ----------------------------------------------------

    def test_a_wrong_facade_count_is_caught_and_names_both_ends(self):
        self.fixture.write("README.md", "There are **five tool facades**, one per purpose.\n")
        errors = self.audit().errors
        self.assertTrue(any("facades" in e and "README.md" in e for e in errors))
        self.assertTrue(any("has 3" in e for e in errors))

    def test_a_count_that_wraps_across_a_line_is_still_read(self):
        """Prose wraps. A line-at-a-time scan misses the drift it is looking for."""
        self.fixture.write("README.md", "There are **five tool\nfacades**, one each.\n")
        self.assertTrue(any("facades" in e for e in self.audit().errors))

    def test_a_correct_count_is_silent(self):
        self.fixture.write("README.md", "There are **three tool facades**.\n")
        self.assertEqual([], self.audit().errors)

    # --- named catalogues -------------------------------------------------

    def test_a_catalogue_missing_one_member_is_caught(self):
        """A file counts as a catalogue once it names at least half the set, and
        at least three. Below that it is a file that happens to mention a couple
        of gate names, and treating it as an incomplete index is a false
        positive — which is the failure mode that gets a lint deleted."""
        self.fixture.write(
            "cli_tools/gate.py",
            'DISPATCH = {\n    "complete": a,\n    "stop": b,\n    "dag": c,\n'
            '    "speed": d,\n    "discovery": e,\n    "summary": f,\n}\n',
        )
        self.fixture.write(
            "AGENTS.md",
            "Gates: `complete`, `stop`, `speed`, `discovery`, `summary`.\n",
        )
        errors = self.audit().errors
        self.assertTrue(any("omits dag" in e for e in errors), errors)

    def test_naming_only_two_of_six_is_not_treated_as_an_index(self):
        self.fixture.write(
            "cli_tools/gate.py",
            'DISPATCH = {\n    "complete": a,\n    "stop": b,\n    "dag": c,\n'
            '    "speed": d,\n    "discovery": e,\n    "summary": f,\n}\n',
        )
        self.fixture.write("AGENTS.md", "Run `dag` when the queue changes.\n")
        self.assertEqual([], self.audit().errors)

    def test_a_file_that_is_not_a_catalogue_is_left_alone(self):
        """Mentioning one gate in passing is not claiming to list them all."""
        self.fixture.write("cli_tools/gate.py", 'DISPATCH = {\n    "a": x,\n    "b": y,\n    "c": z,\n    "d": w,\n}\n')
        self.fixture.write("AGENTS.md", "Run `a` when the queue changes.\n")
        self.assertEqual([], self.audit().errors)

    # --- concurrency ------------------------------------------------------

    def test_a_ceiling_raised_in_one_file_only_is_caught(self):
        self.fixture.write(
            ".agents/skills/nl-prover/references/orchestrator-cookbook.md",
            "Up to **12** at once. The old ceiling was 6.\n",
        )
        errors = self.audit().errors
        self.assertTrue(any("concurrency ceiling disagrees" in e for e in errors))
        self.assertTrue(any("12" in e and "6" in e for e in errors))

    def test_agreeing_ceilings_are_silent(self):
        self.assertEqual(
            [], [e for e in self.audit().errors if "concurrency" in e]
        )

    # --- the long-term read -----------------------------------------------

    def test_an_invocation_without_a_workspace_is_an_error(self):
        self.fixture.write(
            "AGENTS.md",
            "Read memory with `uv run python cli_tools/memory.py read --tier "
            "long-term --view compact`.\n",
        )
        errors = self.audit().errors
        self.assertTrue(any("cannot pass its own stop gate" in e for e in errors))

    def test_an_invocation_with_a_workspace_is_silent_even_when_it_wraps(self):
        """The one correct site in the real repo wraps right before its argument.

        The first version of this gate reported it as the broken one.
        """
        self.fixture.write(
            "CLAUDE.md",
            "Read memory with `uv run python cli_tools/memory.py read --tier\n"
            "long-term --view compact <workspace>` first.\n",
        )
        self.assertEqual(
            [], [e for e in self.audit().errors if "long-term read" in e]
        )

    def test_the_check_is_skipped_rather_than_guessed_when_memory_py_changes(self):
        self.fixture.write("cli_tools/memory.py", "pass\n")
        result = self.audit()
        self.assertTrue(any("check skipped" in w for w in result.warnings))

    # --- the two platform files -------------------------------------------

    def both(self, section, agents_body, claude_body, *, head=""):
        self.fixture.write("AGENTS.md", f"# A\n{head}\n## {section}\n{agents_body}\n")
        self.fixture.write("CLAUDE.md", f"# C\n{head}\n## {section}\n{claude_body}\n")

    def test_identical_synced_sections_are_silent(self):
        self.both("Core Invariants", "1. Verifiers are fresh.\n", "1. Verifiers are fresh.\n")
        self.assertEqual([], self.audit().errors)

    def test_a_line_that_differs_only_in_dispatch_mechanics_is_not_drift(self):
        """That is what the two files are FOR. Normalise it away or the gate
        reports the design as a defect on every run."""
        self.both(
            "Routing",
            "Spawn the Codex custom agent from `.codex/agents/*.toml`.\n",
            "Spawn the Claude Code subagent from `.claude/agents/*.md`.\n",
        )
        self.assertEqual([], self.audit().errors)

    def test_the_same_line_said_differently_is_an_error(self):
        self.both(
            "Tool Rules",
            "Run at most 6 subagents concurrently.\n",
            "Run at most 12 subagents concurrently.\n",
        )
        errors = self.audit().errors
        self.assertTrue(any("says it differently" in e for e in errors), errors)
        self.assertTrue(any("Tool Rules" in e for e in errors))

    def test_a_line_only_one_side_has_is_a_warning_not_an_error(self):
        """It may be a legitimate platform-only addition — Codex has no
        settings.json, so no allowlist sentence. Erroring on it would build a
        list of exceptions, which is the rot this gate exists to avoid."""
        self.both(
            "Tool Rules",
            "Use the facades.\n",
            "Use the facades.\n\nThese are allowlisted in `.claude/settings.json`.\n",
        )
        result = self.audit()
        self.assertEqual([], result.errors)
        self.assertTrue(any("CLAUDE.md only" in w for w in result.warnings))

    def test_a_synced_section_missing_from_one_side_is_an_error(self):
        self.fixture.write("AGENTS.md", "# A\n\n## Routing\nGo left.\n")
        self.fixture.write("CLAUDE.md", "# C\n")
        self.assertTrue(any("present in" in e for e in self.audit().errors))

    def test_sections_outside_the_four_are_not_compared(self):
        """The dual-harness note names exactly four. A Claude-only Hooks section
        is not drift."""
        self.fixture.write("AGENTS.md", "# A\n\n## Core Invariants\nSame.\n")
        self.fixture.write(
            "CLAUDE.md",
            "# C\n\n## Core Invariants\nSame.\n\n## Hooks\nOnly here.\n",
        )
        self.assertEqual([], self.audit().errors)

    # --- hook claims ------------------------------------------------------

    def test_claiming_no_hook_while_two_are_enabled_is_an_error(self):
        self.fixture.write(
            ".claude/settings.json",
            '{"hooks": {"PreToolUse": [{"matcher": "Task", "hooks": '
            '[{"type": "command", "command": ".claude/hooks/nesting_guard.py"}]}],'
            ' "PostToolUse": [{"matcher": "Task", "hooks": []}]}}',
        )
        self.fixture.write(
            "CLAUDE.md", "# C\n\n## Hooks\nnone is enabled by default so it is safe.\n"
        )
        errors = self.audit().errors
        self.assertTrue(any("no hook is enabled" in e for e in errors), errors)
        self.assertTrue(any("enables 2" in e for e in errors))

    def test_an_accurate_hook_claim_is_silent(self):
        self.fixture.write(
            ".claude/settings.json",
            '{"hooks": {"PreToolUse": [{"matcher": "Task", "hooks": '
            '[{"type": "command", "command": ".claude/hooks/nesting_guard.py"}]}]}}',
        )
        self.fixture.write("CLAUDE.md", "# C\n\n## Hooks\nOne PreToolUse hook runs.\n")
        self.assertEqual([], [e for e in self.audit().errors if "hook" in e])

    def test_documenting_hooks_while_none_is_enabled_warns(self):
        # Settings with no hooks at all also trips the nesting check — a
        # well-formed harness must register the guard. Assert on the warning
        # only; the co-firing error is correct and has its own test.
        self.fixture.write(".claude/settings.json", "{}")
        self.fixture.write("CLAUDE.md", "# C\n\n## Hooks\nHooks can do a lot.\n")
        self.assertTrue(any("enables none" in w for w in self.audit().warnings))

    # --- what it deliberately does not check ------------------------------

    def test_the_pre_stop_sequence_is_not_checked(self):
        """It has no executable ground truth. A lint that guesses is worse than
        a document that rots — the three seams without one stay out of here."""
        self.fixture.write("AGENTS.md", "Before stopping run: refresh, then stop.\n")
        self.fixture.write("CLAUDE.md", "Before stopping run: stop.\n")
        self.assertEqual([], self.audit().errors)

class NestingEnforcementTests(unittest.TestCase):
    """Invariant 2 needs an enforcement point on each platform, not one.

    `max_threads` is the fan-out limit; `max_depth` is the nesting limit. Both
    platform files cited the first for a rule the second enforces, and the gate
    parsed only the first — so deleting `max_depth = 1` fired nothing.
    """

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fixture = Fixture(self.root)
        self.fixture.write(".codex/config.toml", "[agents]\nmax_threads = 6\nmax_depth = 1\n")
        self.fixture.write(".claude/hooks/nesting_guard.py", "# guard\n")
        self.fixture.write(
            ".claude/settings.json",
            '{"hooks": {"PreToolUse": [{"matcher": "Agent|Task", "hooks": '
            '[{"type": "command", "command": "python3 .claude/hooks/nesting_guard.py"}]}]}}',
        )

    def nesting_errors(self):
        return [
            e for e in contracts_gate.audit(self.root).errors
            if "max_depth" in e or "nesting_guard" in e
        ]

    def test_both_enforcement_points_present_is_silent(self):
        self.assertEqual([], self.nesting_errors())

    def test_a_missing_codex_max_depth_is_an_error(self):
        self.fixture.write(".codex/config.toml", "[agents]\nmax_threads = 6\n")
        self.assertTrue(any("unenforced on Codex" in e for e in self.nesting_errors()))

    def test_a_max_depth_that_permits_nesting_is_an_error(self):
        self.fixture.write(".codex/config.toml", "[agents]\nmax_threads = 6\nmax_depth = 2\n")
        self.assertTrue(any("needs 1" in e for e in self.nesting_errors()))

    def test_a_missing_claude_guard_is_an_error(self):
        (self.root / ".claude" / "hooks" / "nesting_guard.py").unlink()
        self.assertTrue(any("prose only on" in e for e in self.nesting_errors()))

    def test_a_guard_nobody_registered_is_an_error(self):
        """The failure mode that looks exactly like a working guard."""
        self.fixture.write(".claude/settings.json", '{"hooks": {}}')
        self.assertTrue(any("a guard nobody runs" in e for e in self.nesting_errors()))


class PreStopSequenceTests(unittest.TestCase):
    """Three mutually inconsistent versions of this sequence existed at once.

    It has a ground truth now — a designated SSOT file rather than executable
    code, which is weaker. "The copies agree with the one that decides" is still
    a fact, and it took a human reading four files by hand to notice it was false.
    """

    SSOT = ".agents/skills/nl-prover/references/stop-conditions.md"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fixture = Fixture(self.root)
        self.sequence(self.SSOT, ["memory.py refresh", "gate.py discovery", "gate.py stop"])

    def sequence(self, name, steps):
        body = "\n".join(f"uv run python cli_tools/{s} <workspace>" for s in steps)
        self.fixture.write(name, f"# s\n\n```\n{body}\n```\n")

    def errors(self):
        return [e for e in contracts_gate.audit(self.root).errors if "pre-stop" in e]

    def test_a_copy_that_matches_is_silent(self):
        self.sequence("AGENTS.md", ["memory.py refresh", "gate.py discovery", "gate.py stop"])
        self.assertEqual([], self.errors())

    def test_a_file_that_does_not_restate_the_sequence_is_ideal_and_silent(self):
        """Pointing at the SSOT instead of copying it is the behaviour to reward."""
        self.fixture.write("AGENTS.md", "# A\n\nSee stop-conditions.md for the sequence.\n")
        self.assertEqual([], self.errors())

    def test_a_copy_that_drops_a_step_is_an_error_naming_the_step(self):
        self.sequence("AGENTS.md", ["gate.py discovery", "gate.py stop"])
        errors = self.errors()
        self.assertTrue(any("omits memory refresh" in e for e in errors), errors)

    def test_a_copy_that_invents_a_step_is_an_error(self):
        self.sequence(
            "AGENTS.md",
            ["memory.py refresh", "gate.py discovery", "gate.py complete", "gate.py stop"],
        )
        self.assertTrue(any("adds gate complete" in e for e in self.errors()))

    def test_the_same_steps_in_another_order_is_a_warning_not_an_error(self):
        self.sequence("AGENTS.md", ["gate.py discovery", "memory.py refresh", "gate.py stop"])
        result = contracts_gate.audit(self.root)
        self.assertEqual([], [e for e in result.errors if "pre-stop" in e])
        self.assertTrue(any("different order" in w for w in result.warnings))

    def test_a_block_that_is_not_a_stop_sequence_is_not_read_as_one(self):
        """Prose and examples name these commands constantly for other reasons."""
        self.fixture.write(
            "AGENTS.md",
            "# A\n\n```\nuv run python cli_tools/memory.py read --tier kb\n```\n",
        )
        self.assertEqual([], self.errors())

    def test_a_missing_ssot_skips_rather_than_accusing_the_copies(self):
        (self.root / self.SSOT).unlink()
        result = contracts_gate.audit(self.root)
        self.assertEqual([], [e for e in result.errors if "pre-stop" in e])
        self.assertTrue(any("check skipped" in w for w in result.warnings))


class LatentDefectTests(unittest.TestCase):
    """Six ways this gate reported PASS while the thing it guards was broken.

    Every one was latent — none fired on the real tree, which is the point: a
    check that cannot fire looks exactly like a check with nothing to report.
    """

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fixture = Fixture(self.root)

    def audit(self):
        return contracts_gate.audit(self.root)

    # --- the direction that was not checked at all -------------------------

    def test_a_subcommand_the_prose_orders_and_the_code_lost_is_an_error(self):
        """`truth - named` only. Deleting a subcommand five files still order is
        the drift that stops a run, and it was invisible."""
        self.fixture.write("AGENTS.md", "Run `uv run python cli_tools/gate.py dag <ws>`.\n")
        errors = [e for e in self.audit().errors if "no such subcommand" in e]
        self.assertTrue(any("gate dag" in e for e in errors), errors)

    def test_an_invocation_that_still_exists_is_silent(self):
        self.fixture.write("AGENTS.md", "Run `uv run python cli_tools/gate.py stop <ws>`.\n")
        self.assertEqual([], [e for e in self.audit().errors if "no such subcommand" in e])

    # --- extractors that returned a wrong answer silently ------------------

    def test_a_brace_inside_DISPATCH_no_longer_truncates_the_list(self):
        self.fixture.write(
            "cli_tools/gate.py",
            'DISPATCH = {\n    "alpha": a,  # dict}\n    "beta": b,\n    "dag": c,\n}\n',
        )
        self.assertEqual(
            ["alpha", "beta", "dag"], contracts_gate.gate_subcommands(self.root)
        )

    def test_an_adr_number_before_a_noun_is_not_read_as_a_count(self):
        """"see ADR 0016 facades" raised a blocking error claiming 16 facades."""
        self.fixture.write("README.md", "See ADR 0016 facades for the rationale.\n")
        self.assertEqual([], [e for e in self.audit().errors if "facades" in e])

    def test_a_count_written_as_two_is_read(self):
        """NUMBER_WORDS started at `three`, so small wrong counts passed."""
        self.fixture.write("README.md", "There are two tool facades.\n")
        self.assertTrue(any("facades" in e for e in self.audit().errors))

    def test_an_unreadable_ceiling_warns_instead_of_going_quiet(self):
        self.fixture.write("cli_tools/_gate/speed.py", "CONCURRENCY = 6\n")
        self.assertTrue(
            any("could not read the ceiling" in w for w in self.audit().warnings)
        )

    # --- normalisation that erased the thing it was comparing --------------

    def test_a_platform_claim_and_its_inverse_are_not_the_same_line(self):
        """Mapping both platform names to one placeholder made "may dispatch on
        Claude Code but not on Codex" and its reverse normalise identically."""
        for name, text in (
            ("AGENTS.md", "## Core Invariants\nA specialist may dispatch on Claude Code but not on Codex.\n"),
            ("CLAUDE.md", "## Core Invariants\nA specialist may dispatch on Codex but not on Claude Code.\n"),
        ):
            self.fixture.write(name, f"# t\n\n{text}")
        self.assertTrue(
            any("says it differently" in e for e in self.audit().errors)
        )

    def test_a_flag_is_not_read_as_a_pre_stop_step(self):
        """`[a-z-]+` swallowed `--help`, turning a troubleshooting block into
        two spurious extra-step errors."""
        block = (
            "```\nuv run python cli_tools/gate.py stop <ws>\n"
            "uv run python cli_tools/gate.py --help\n```\n"
        )
        self.fixture.write(
            ".agents/skills/nl-prover/references/stop-conditions.md", f"# s\n\n{block}"
        )
        self.fixture.write("AGENTS.md", f"# a\n\n{block}")
        self.assertEqual([], [e for e in self.audit().errors if "pre-stop" in e])

    # --- certifying a broken mechanism -------------------------------------

    def test_a_guard_that_fails_its_own_self_test_is_an_error(self):
        """Present and registered is what a working guard also looks like. The
        first version asserted exactly those two things about a hook that could
        not fire on any real payload."""
        guard = self.root / ".claude" / "hooks" / "nesting_guard.py"
        guard.write_text("import sys; sys.exit(1)\n", encoding="utf-8")
        self.assertTrue(
            any("fails its own --self-test" in e for e in self.audit().errors)
        )


if __name__ == "__main__":
    unittest.main()
