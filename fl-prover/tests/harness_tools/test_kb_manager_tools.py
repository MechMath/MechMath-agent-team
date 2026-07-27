import importlib.util
import io
import json
from contextlib import redirect_stdout
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


from _memory import inbox as kb_manager_write       # internal inbox-write module
from _memory import kb as kb_manager_summary         # internal KB-tier module


class KBManagerWriteTests(unittest.TestCase):
    def test_write_content_creates_inbox_and_writes_note(self):
        # ADR 0016 P0#1: the "math result -> inbox" chain must actually work.
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            data_dir.mkdir()
            buf = io.StringIO()
            with redirect_stdout(buf):
                kb_manager_write.write("# proven bound", None, "bound.md", str(data_dir))
            result = json.loads(buf.getvalue())
            self.assertTrue(result["ok"])
            inbox = data_dir / "inbox"
            self.assertTrue(inbox.exists())
            written = list(inbox.glob("*bound.md"))
            self.assertEqual(1, len(written))
            self.assertIn("proven bound", written[0].read_text(encoding="utf-8"))

    def test_write_card_type_declares_target_family(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            data_dir.mkdir()
            buf = io.StringIO()
            with redirect_stdout(buf):
                kb_manager_write.write("body", None, "c.md", str(data_dir), "Experience_")
            result = json.loads(buf.getvalue())
            self.assertEqual("Experience_", result["card_type"])
            written = list((data_dir / "inbox").glob("*c.md"))[0].read_text(encoding="utf-8")
            self.assertIn("card-type: Experience_", written)

    def test_write_errors_when_data_dir_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "nope"
            buf = io.StringIO()
            with self.assertRaises(SystemExit):
                with redirect_stdout(buf):
                    kb_manager_write.write("x", None, "n.md", str(missing))
            self.assertIn("Data directory not found", buf.getvalue())


class KBManagerSummaryTests(unittest.TestCase):
    def test_summary_reads_wiki_index_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            wiki = data_dir / "wiki"
            wiki.mkdir(parents=True)
            (wiki / "index.md").write_text(
                "# KB\n\n## Concepts\n- [[Concept_Foo]] a bound\n\n"
                "## Analyses & Comparisons\n- [[Analysis_Bar]] a comparison\n",
                encoding="utf-8",
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                kb_manager_summary.summary(str(data_dir))
            payload = json.loads(buf.getvalue())
            self.assertTrue(payload["ok"])
            self.assertEqual(1, payload["concept_count"])
            self.assertEqual(1, payload["analysis_count"])


if __name__ == "__main__":
    unittest.main()
