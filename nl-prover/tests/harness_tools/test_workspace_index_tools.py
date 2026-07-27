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


from _memory import local as workspace_memory      # internal local-tier module
from _workspace import references as reference_extract
from _search import query_index
from _workspace import presentation as presentation_index


class WorkspaceIndexToolTests(unittest.TestCase):
    def make_workspace(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "STATUS.md").write_text(
            "# Proof Status: sample\n\n## Phase\nprove\n\n## History\n- Started.\n",
            encoding="utf-8",
        )
        (root / "proof.tex").write_text("\\begin{proof}Draft.\\end{proof}\n", encoding="utf-8")
        return temp, root

    def test_reference_scan_handles_missing_references(self):
        temp, root = self.make_workspace()
        with temp:
            payload = reference_extract.build_index(root)
            self.assertEqual(0, payload["count"])
            self.assertTrue((root / "references/index.json").exists())
            self.assertTrue((root / "references/index.md").exists())

    def test_reference_extract_indexes_and_searches_text_references(self):
        temp, root = self.make_workspace()
        with temp:
            refs = root / "references"
            refs.mkdir()
            (refs / "note.md").write_text(
                "# Local Note\n\nA spectral gap estimate follows from compactness.\n",
                encoding="utf-8",
            )
            payload = reference_extract.extract(root, backend="pdftotext", force=False)
            self.assertTrue(payload["ok"])
            search = reference_extract.search(root, query="spectral gap", limit=3, view="compact")
            self.assertEqual(1, search["count"])
            self.assertEqual("references/note.md", search["results"][0]["path"])

    def test_workspace_memory_append_show_and_search(self):
        temp, root = self.make_workspace()
        with temp:
            (root / "recovery").mkdir()
            (root / "recovery/route_recovery_1.md").write_text(
                "# Recovery\n\nMissing source theorem blocks route.\n",
                encoding="utf-8",
            )
            entry = workspace_memory.append_from_source(
                root,
                channel="failed_paths",
                source="recovery/route_recovery_1.md",
                kind="recovery",
                view="compact",
            )
            self.assertEqual("failed_paths", entry["channel"])
            shown = workspace_memory.show(root, channel="failed_paths", view="compact", latest=1, limit=10)
            self.assertEqual(1, shown["count"])
            found = workspace_memory.search(
                root,
                query="source theorem",
                channels=["failed_paths"],
                limit=5,
                view="compact",
            )
            self.assertEqual(1, found["count"])

    def test_refresh_index_md_renders_latest_content_not_only_counts(self):
        # ADR 0016 §3.2 P0#2: index.md must render each channel's latest content,
        # not just record counts, so a model reading only index.md sees the memory.
        temp, root = self.make_workspace()
        with temp:
            (root / "recovery").mkdir()
            (root / "recovery/route_recovery_1.md").write_text(
                "# Recovery\n\nMissing source theorem blocks route Alpha.\n",
                encoding="utf-8",
            )
            workspace_memory.refresh(root, view="compact")
            index_md = (root / "memory/index.md").read_text(encoding="utf-8")
            # Content from the artifact, not just the count line, must be present.
            self.assertIn("Missing source theorem", index_md)
            self.assertIn("route_recovery_1.md", index_md)
            self.assertIn("## failed_paths", index_md)

    def test_query_index_summarizes_existing_query_outputs(self):
        temp, root = self.make_workspace()
        with temp:
            qdir = root / "queries/q_source"
            qdir.mkdir(parents=True)
            (qdir / "request.md").write_text("# Query\n\nFind a fixed point theorem.\n", encoding="utf-8")
            (qdir / "status.md").write_text("# Status\n\ncomplete\n", encoding="utf-8")
            (qdir / "matlas.md").write_text("# Matlas\n\nBanach fixed point theorem statement.\n", encoding="utf-8")
            payload = query_index.summarize_query(root, "q_source", view="compact")
            self.assertIn("matlas", payload["sources"])
            refreshed = query_index.refresh(root, sources=["matlas"], view="compact")
            self.assertEqual(1, refreshed["count"])
            self.assertTrue((root / "memory/source_findings.jsonl").exists())

    def test_presentation_index_build_and_latest(self):
        temp, root = self.make_workspace()
        with temp:
            writer = root / "writer"
            writer.mkdir()
            (writer / "progress_notes.tex").write_text("Progress notes text.\n", encoding="utf-8")
            (root / "proof.pdf").write_text("exported proof pdf\n", encoding="utf-8")
            (root / "progress_notes.pdf").write_text("exported progress pdf\n", encoding="utf-8")
            payload = presentation_index.build(root, view="compact")
            self.assertEqual("prove", payload["phase"])
            self.assertTrue((root / "presentation/index.json").exists())
            exported = {item["path"] for item in payload["export_pdfs"]}
            self.assertEqual({"proof.pdf", "progress_notes.pdf"}, exported)
            latest = presentation_index.latest(root, section="presentation", limit=5, view="compact")
            self.assertEqual(1, latest["count"])


if __name__ == "__main__":
    unittest.main()
