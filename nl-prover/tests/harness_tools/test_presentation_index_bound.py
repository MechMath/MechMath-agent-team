"""The presentation index is a routing view, so retries must replace, not accumulate.

`presentation/index.json` is rebuilt on every `build`, `show`, and `latest` call and
carries a summary plus a head excerpt per file. Without a bound, a lemma that took
eleven Generator attempts contributes eleven review packets to it, and the index a
run re-reads grows with the number of retries rather than the amount of mathematics.
"""

from pathlib import Path
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "cli_tools"))
from _workspace import presentation


class LatestVersionsOnlyTests(unittest.TestCase):
    def paths(self, *names):
        return [Path("/ws/lemmas/lem_a/verifier") / n for n in names]

    def test_keeps_only_the_highest_version(self):
        kept = presentation.latest_versions_only(
            self.paths("review_packet_v1.md", "review_packet_v2.md", "review_packet_v11.md")
        )
        self.assertEqual([p.name for p in kept], ["review_packet_v11.md"])

    def test_version_order_is_numeric_not_lexical(self):
        """v11 must beat v9. Sorting these as strings gets it backwards."""
        kept = presentation.latest_versions_only(
            self.paths("report_v9.md", "report_v11.md")
        )
        self.assertEqual([p.name for p in kept], ["report_v11.md"])

    def test_distinct_families_are_kept_separately(self):
        kept = presentation.latest_versions_only(
            self.paths("report_v2.md", "review_packet_v3.md")
        )
        self.assertEqual(
            sorted(p.name for p in kept), ["report_v2.md", "review_packet_v3.md"]
        )

    def test_same_stem_in_different_lemmas_does_not_collide(self):
        kept = presentation.latest_versions_only(
            [
                Path("/ws/lemmas/lem_a/verifier/review_packet_v1.md"),
                Path("/ws/lemmas/lem_b/verifier/review_packet_v1.md"),
            ]
        )
        self.assertEqual(len(kept), 2)

    def test_unversioned_files_are_always_kept(self):
        kept = presentation.latest_versions_only(
            self.paths("verdict.md", "review_packet_v1.md", "review_packet_v2.md")
        )
        self.assertEqual(
            sorted(p.name for p in kept), ["review_packet_v2.md", "verdict.md"]
        )

    def test_collect_files_is_unbounded_unless_asked(self):
        """The bound is opt-in: sections that are not retry families keep every file."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            directory = root / "lemmas" / "lem_a" / "verifier"
            directory.mkdir(parents=True)
            for i in (1, 2, 3):
                (directory / f"review_packet_v{i}.md").write_text("x\n", encoding="utf-8")
            every = presentation.collect_files(root, "**/review_packet*.md", view="compact")
            latest = presentation.collect_files(
                root, "**/review_packet*.md", view="compact", latest_only=True
            )
            self.assertEqual(len(every), 3)
            self.assertEqual(len(latest), 1)
            self.assertTrue(latest[0]["path"].endswith("review_packet_v3.md"))

    def test_build_payload_bounds_the_verification_section(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "STATUS.md").write_text("# S\n\n## Phase\nprove\n", encoding="utf-8")
            for lemma in ("lem_a", "lem_b"):
                directory = root / "lemmas" / lemma / "verifier"
                directory.mkdir(parents=True)
                for i in range(1, 6):
                    (directory / f"review_packet_v{i}.md").write_text("x\n", encoding="utf-8")
            payload = presentation.build_payload(root, view="compact")
            # 10 packets on disk, one surviving packet per lemma in the index.
            self.assertEqual(len(payload["verification"]), 2)


if __name__ == "__main__":
    unittest.main()
