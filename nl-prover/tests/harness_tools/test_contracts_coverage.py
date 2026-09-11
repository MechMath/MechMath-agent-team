#!/usr/bin/env python3
"""The invocation check has to reach every facade, not the ones written one way.

`facade_subcommands` read a single shape — a `DISPATCH` literal spread over several
lines. `external.py` writes its on one line; `memory.py` and `verify.py` use argparse
subparsers. Those three produced no entry, and a facade with no entry was skipped in
silence by the caller, so every prose invocation of `memory.py` — the facade the
prompts name most — went unchecked while the gate reported success.
"""
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "cli_tools"))

from _gate import contracts  # noqa: E402


class ShapeCoverageTestCase(unittest.TestCase):
    """Each declaration shape, read out of a synthetic tree so the assertion is about
    the reader rather than about today's contents of this repo."""

    def build(self, **facade_source):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "cli_tools").mkdir()
        for name, source in facade_source.items():
            (root / "cli_tools" / f"{name}.py").write_text(source, encoding="utf-8")
        return root

    def test_a_multi_line_dispatch_is_read(self):
        root = self.build(alpha='DISPATCH = {\n    "one": x,\n    "two": y,\n}\n')
        self.assertEqual(contracts.facade_subcommands(root), {"alpha": ["one", "two"]})

    def test_a_single_line_dispatch_is_read(self):
        root = self.build(beta='DISPATCH = {"one": x, "two": y}\n')
        self.assertEqual(contracts.facade_subcommands(root), {"beta": ["one", "two"]})

    def test_argparse_subparsers_are_read(self):
        root = self.build(gamma='p = sub.add_parser("one")\nq = sub.add_parser("two")\n')
        self.assertEqual(contracts.facade_subcommands(root), {"gamma": ["one", "two"]})

    def test_a_subcommand_forwarded_before_argparse_is_read(self):
        root = self.build(delta='if sys.argv[1] == "card-lint":\n    pass\n')
        self.assertEqual(contracts.facade_subcommands(root), {"delta": ["card-lint"]})

    def test_a_private_module_is_not_a_facade(self):
        root = self.build(**{"_hidden": 'DISPATCH = {"one": x}\n'})
        self.assertEqual(contracts.facade_subcommands(root), {})


class LiveCoverageTestCase(unittest.TestCase):
    def test_every_facade_in_this_repo_is_readable(self):
        """The check must not be able to go quiet again. A facade written in a shape the
        reader does not know is a hole, and a hole reads exactly like a clean result."""
        read = contracts.facade_subcommands(REPO)
        self.assertEqual(sorted(read), sorted(contracts.facades(REPO)))

    def test_the_facades_the_pattern_matches_are_the_facades_that_exist(self):
        """`_INVOCATION` names the facades literally. If one is added and not named
        there, its invocations are unmatched rather than checked."""
        named = set(contracts._INVOCATION.pattern.split("(")[1].split(")")[0].split("|"))
        self.assertEqual(named, set(contracts.facades(REPO)))


class DeadInvocationTestCase(unittest.TestCase):
    def test_an_invocation_of_a_removed_subcommand_is_reported(self):
        result = contracts.ContractResult()
        prose = "run `cli_tools/memory.py no-such-thing <workspace>` before stopping"
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / ".agents/skills/memory-routing").mkdir(parents=True)
        (root / ".agents/skills/memory-routing/SKILL.md").write_text(prose, encoding="utf-8")
        contracts.check_invocations_exist(
            result, root, subcommands={"memory": ["read", "refresh"]}
        )
        self.assertTrue(
            any("memory no-such-thing" in e for e in result.errors), result.errors
        )

    def test_a_live_invocation_is_not_reported(self):
        result = contracts.ContractResult()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / ".agents/skills/memory-routing").mkdir(parents=True)
        (root / ".agents/skills/memory-routing/SKILL.md").write_text(
            "run `cli_tools/memory.py refresh <workspace>`", encoding="utf-8"
        )
        contracts.check_invocations_exist(
            result, root, subcommands={"memory": ["read", "refresh"]}
        )
        self.assertEqual(result.errors, [])


if __name__ == "__main__":
    unittest.main()
