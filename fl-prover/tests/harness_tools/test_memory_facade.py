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


memory = load_tool("memory")
from _memory import experience as _experience  # internal card-model module


CARD = """---
type: experience
kind: negative-constraint
id: neg-zero-div
statement: Do not divide by a possibly-zero leading coefficient.
trigger: polynomial division or normalization step
why: division by zero invalidates the step
failure_modes: over-flags when nonzero is already established
provenance: [verifier-block]
scope: general
refs: [[Concept_Polynomials]]
---
Do not divide by a possibly-zero leading coefficient.
"""


class ExperienceCardTests(unittest.TestCase):
    def test_parse_frontmatter_and_load(self):
        fm, body = _experience.parse_frontmatter(CARD)
        self.assertEqual("negative-constraint", fm["kind"])
        self.assertEqual("neg-zero-div", fm["id"])
        self.assertTrue(body.startswith("Do not divide"))

    def test_validate_flags_missing_trigger(self):
        problems = _experience.validate_card({"statement": "x", "kind": "negative-constraint"})
        self.assertTrue(any("trigger" in p for p in problems))

    def test_render_memory_md_two_lines_per_card(self):
        fm, _body = _experience.parse_frontmatter(CARD)
        text = _experience.render_memory_md([{**fm, "id": fm["id"]}])
        self.assertIn("[neg-zero-div]", text)
        self.assertIn("Trigger:", text)


class MemoryFacadeTests(unittest.TestCase):
    def make_cards(self, tmp):
        """A stand-in repo root holding the local long-term tier."""
        root = Path(tmp) / "repo"
        (root / "memory" / "experience").mkdir(parents=True)
        (root / "memory" / "experience" / "Experience_neg-zero-div.md").write_text(CARD, encoding="utf-8")
        return root

    def test_render_longterm_writes_memory_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_cards(tmp)
            mem = Path(tmp) / "memory.md"
            result = memory.render_longterm(memory_file=mem, card_root=root)
            self.assertTrue(result["ok"])
            self.assertEqual(1, result["cards"])
            self.assertIn("neg-zero-div", mem.read_text(encoding="utf-8"))

    def test_render_longterm_refuses_to_blank_nonempty_memory_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty_root = Path(tmp) / "repo"
            (empty_root / "memory" / "experience").mkdir(parents=True)  # no cards
            mem = Path(tmp) / "memory.md"
            mem.write_text("# Long-Term\n\n- [neg-x] a real curated constraint\n", encoding="utf-8")
            result = memory.render_longterm(memory_file=mem, card_root=empty_root)
            self.assertFalse(result["ok"])  # guarded
            self.assertIn("a real curated constraint", mem.read_text(encoding="utf-8"))
            forced = memory.render_longterm(memory_file=mem, card_root=empty_root, force=True)
            self.assertTrue(forced["ok"])  # explicit override allowed

    def test_read_longterm_full_query_filters(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_cards(tmp)
            mem = Path(tmp) / "memory.md"
            hit = memory.read_longterm(view="full", query="division", memory_file=mem, card_root=root)
            self.assertEqual(1, hit["count"])
            miss = memory.read_longterm(view="full", query="topology homotopy", memory_file=mem, card_root=root)
            self.assertEqual(0, miss["count"])

    def test_read_kb_returns_compact_index_and_fetch_note_regardless_of_view(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            (data / "wiki").mkdir(parents=True)
            (data / "wiki" / "index.md").write_text(
                "# KB\n\n## Concepts\n- [[Concept_Foo]] a bound\n", encoding="utf-8"
            )
            for view in ("compact", "summary", "full"):
                payload = memory.read_kb(view=view, query=None, data_dir=data)
                self.assertTrue(payload["ok"])
                self.assertEqual(1, payload["concept_count"])
                self.assertIn("note", payload)  # same for every view

    def test_aggregate_candidates_promotes_into_the_local_long_term_tier(self):
        # The whole point of the tier: a run's lesson must reach memory.md by
        # itself, with no inbox hop and no human promotion step.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            (root / "memory" / "experience").mkdir(parents=True)
            mem = root / "memory.md"
            ws = Path(tmp) / "ws"
            cand = ws / "memory" / "candidates"
            cand.mkdir(parents=True)
            (cand / "verifier-run1.jsonl").write_text(
                '{"kind":"negative-constraint","statement":"Do not divide by zero.","trigger":"div"}\n'
                '{"kind":"negative-constraint","statement":"do not  divide by zero.","trigger":"dup"}\n'
                '{"no_constraint":"nothing generalizable"}\n',
                encoding="utf-8",
            )
            result = memory.aggregate_candidates(ws, memory_file=mem, card_root=root)
            self.assertEqual(3, result["candidates_found"])
            self.assertEqual(1, result["after_dedup"])  # dup collapsed, no_constraint dropped
            self.assertEqual(1, len(result["promoted"]))
            self.assertTrue((ws / "memory" / "candidates_aggregated.jsonl").exists())
            self.assertTrue((ws / "memory" / "candidates_promoted.json").exists())
            self.assertEqual(1, len(list((root / "memory" / "experience").glob("*.md"))))
            self.assertIn("Do not divide by zero.", mem.read_text(encoding="utf-8"))

    def test_aggregate_candidates_does_not_restack_an_existing_constraint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_cards(tmp)  # already holds the zero-division card
            mem = root / "memory.md"
            ws = Path(tmp) / "ws"
            cand = ws / "memory" / "candidates"
            cand.mkdir(parents=True)
            # Same constraint as the fixture card, re-emitted by a later run.
            (cand / "verifier-run1.jsonl").write_text(
                '{"kind":"negative-constraint",'
                '"statement":"Do not divide by a possibly-zero leading coefficient.",'
                '"trigger":"div"}\n',
                encoding="utf-8",
            )
            result = memory.aggregate_candidates(ws, memory_file=mem, card_root=root)
            self.assertEqual([], result["promoted"])
            self.assertEqual(1, len(result["already_present"]))
            self.assertEqual(1, len(list((root / "memory" / "experience").glob("*.md"))))

    def test_aggregate_candidates_rejects_a_card_with_no_trigger(self):
        # No trigger means it can never be recalled, so storing it would grow
        # memory.md without ever firing.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            (root / "memory" / "experience").mkdir(parents=True)
            ws = Path(tmp) / "ws"
            cand = ws / "memory" / "candidates"
            cand.mkdir(parents=True)
            (cand / "verifier-run1.jsonl").write_text(
                '{"kind":"negative-constraint","statement":"Do not divide by zero."}\n', encoding="utf-8"
            )
            result = memory.aggregate_candidates(ws, memory_file=root / "memory.md", card_root=root)
            self.assertEqual([], result["promoted"])
            self.assertEqual(1, len(result["rejected"]))


if __name__ == "__main__":
    unittest.main()
