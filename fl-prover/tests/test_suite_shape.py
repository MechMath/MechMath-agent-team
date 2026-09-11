"""Does the suite still contain the tests it contains?

On 2026-09-09 `python3 -m unittest discover -s tests` ran **7 tests**. The suite has
**172**. The other 165 lived in `tests/harness_tools/`, which had no `__init__.py`, so
unittest discovery could not import it as a package and walked straight past sixteen files
and 2,500 lines. Every one of them passed once made visible — they were not broken, they
were simply never asked.

That is worse than a failing test. A red test stops someone. A test that is not collected
reports the same "OK" as a test that ran, so the suite was green for as long as anyone
had been looking, and the deletion decisions in this cycle were about to be justified by
"the tests still pass".

NL-Prover-v1 already carries this exact scar: `tests/harness_tools/test_suite_shape.py`
there records that its suite had silently lost ~200 tests to misplaced `__main__` guards.
The lesson existed, in the sibling repo, written down. It was not transferable as prose,
so it is a test here.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Set from the measured count on 2026-09-09, when discovery was repaired. Raise it when
# tests are added; if it must be LOWERED, that is a deletion and it belongs in a commit
# message, not in a quiet edit here.
#
# History, so the floor is never moved without a reason attached:
#   2026-09-09  170  discovery repaired: 7 collected -> 172 present
#   2026-09-09  153  gate proof-attempt (10 tests) and citation-audit (10) deleted with
#                    their modules; 155 collected. The guard caught the drop and refused,
#                    which is the whole point of it — this line is the declaration.
MIN_TESTS = 153


class SuiteShapeTest(unittest.TestCase):
    def test_every_test_directory_is_an_importable_package(self):
        """A directory of tests without __init__.py is invisible, not empty."""
        missing = [
            str(d.relative_to(ROOT))
            for d in ROOT.rglob("*")
            if d.is_dir()
            and d.name != "__pycache__"
            and any(d.glob("test_*.py"))
            and not (d / "__init__.py").exists()
        ]
        self.assertEqual(
            missing, [],
            "these directories hold test_*.py but are not packages, so unittest "
            f"discovery will skip them silently: {missing}",
        )

    def test_discovery_collects_the_whole_suite(self):
        """Count what discovery actually collects, not what the tree contains."""
        loader = unittest.TestLoader()
        suite = loader.discover(str(ROOT), top_level_dir=str(ROOT))

        def count(s) -> int:
            return sum(count(x) if isinstance(x, unittest.TestSuite) else 1 for x in s)

        n = count(suite)
        self.assertGreaterEqual(
            n, MIN_TESTS,
            f"discovery collected {n} tests, expected at least {MIN_TESTS}. Either tests "
            "were deleted (say so in the commit) or a directory stopped being importable "
            "and the suite is quietly reporting OK for tests it never ran.",
        )
        self.assertEqual(
            loader.errors, [],
            f"discovery raised import errors, which it reports as skipped tests: "
            f"{loader.errors}",
        )

    def test_no_test_file_is_import_only_reachable(self):
        """Each test_*.py must define at least one test, or it is decoration."""
        empty = [
            str(p.relative_to(ROOT))
            for p in ROOT.rglob("test_*.py")
            if "def test" not in p.read_text(encoding="utf-8", errors="replace")
        ]
        self.assertEqual(empty, [], f"test files with no test in them: {empty}")

    def test_every_file_contributes_the_tests_it_declares(self):
        """PER FILE, not just in total — the total hid the failure it cites.

        A change-reviewer wrapped one file's test class in `if __name__ == "__main__":`
        (the exact misplaced-guard shape NL-Prover recorded losing ~200 tests to).
        Collection fell from 160 to 156 and `test_discovery_collects_the_whole_suite`
        still passed, because the floor had 7 tests of headroom. A floor on a total can
        always absorb a small silent loss, so compare each file's declared `def test_`
        count against what discovery actually collects from it.
        """
        loader = unittest.TestLoader()
        short = []
        for path in sorted(ROOT.rglob("test_*.py")):
            declared = len(re.findall(r"^\s*def (test_\w+)", path.read_text(
                encoding="utf-8", errors="replace"), re.MULTILINE))
            if not declared:
                continue
            mod = ".".join(path.relative_to(ROOT).with_suffix("").parts)
            try:
                suite = loader.loadTestsFromName(mod)
            except Exception as exc:                                # noqa: BLE001
                short.append(f"{mod}: will not load ({exc!r})")
                continue

            def count(s) -> int:
                return sum(count(x) if isinstance(x, unittest.TestSuite) else 1 for x in s)

            got = count(suite)
            if got < declared:
                short.append(
                    f"{mod}: declares {declared} test methods, discovery collects {got}"
                    " — the usual cause is the class or the defs sitting inside an"
                    ' `if __name__ == "__main__":` block'
                )
        self.assertEqual(short, [], f"files losing tests silently: {short}")


if __name__ == "__main__":
    unittest.main()
