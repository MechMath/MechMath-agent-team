"""The suite must not be able to hide part of itself.

Nine test modules had `if __name__ == "__main__": unittest.main()` in the middle
of the file, left behind each time a class was appended after it. `unittest
discover` imports the module and finds every class, so nothing failed — but
running one file directly executed only the classes above the guard, and the
gap was ~200 tests. A suite that reports a different number depending on how it
is invoked is a suite that can hide a failure from whoever runs it the other way.
"""

from pathlib import Path
import re
import unittest


HERE = Path(__file__).resolve().parent
GUARD = re.compile(r'^if __name__ == "__main__":', re.MULTILINE)


class SuiteShapeTests(unittest.TestCase):
    def modules(self):
        return sorted(p for p in HERE.glob("test_*.py") if p.name != Path(__file__).name)

    def test_every_module_has_at_most_one_main_guard(self):
        for path in self.modules():
            with self.subTest(module=path.name):
                self.assertLessEqual(len(GUARD.findall(path.read_text())), 1)

    def test_no_test_class_sits_below_the_main_guard(self):
        """The failure was silent and cost about 200 tests on a direct run."""
        for path in self.modules():
            text = path.read_text()
            match = GUARD.search(text)
            if match is None:
                continue
            with self.subTest(module=path.name):
                below = text[match.end():]
                self.assertNotRegex(
                    below, r"^class \w+", f"{path.name} defines a class after its guard"
                )
                self.assertNotRegex(
                    below, r"^    def test_", f"{path.name} defines a test after its guard"
                )

    def test_every_module_is_runnable_on_its_own(self):
        for path in self.modules():
            with self.subTest(module=path.name):
                self.assertIsNotNone(
                    GUARD.search(path.read_text()),
                    f"{path.name} has no main guard, so it cannot be run directly",
                )


if __name__ == "__main__":
    unittest.main()
