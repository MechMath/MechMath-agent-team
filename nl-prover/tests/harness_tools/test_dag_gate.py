"""DAG gate: the lemma dependency graph, traversed.

Every test here fixes a *shape* of the graph and asserts the finding that shape
must produce. Nothing asserts a wall-clock or a verdict's mathematics — the two
mtime-based findings are exercised by setting mtimes explicitly, which is also
the honest admission that on a real workspace those two are circumstantial.
"""

import os
from pathlib import Path
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "cli_tools"))
from _gate import dag as dag_gate


BASE = 1_700_000_000.0
MINUTE = 60.0


class DagGateTests(unittest.TestCase):
    def make_workspace(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return Path(temp.name)

    # --- fixture helpers ---------------------------------------------------

    def lemma(self, root, name, *, dependencies=None, verdict=None, at=BASE):
        """A lemma directory: statement, optional verdict, optional proof."""
        directory = root / "lemmas" / name
        directory.mkdir(parents=True, exist_ok=True)
        if dependencies is not None:
            (directory / "statement.md").write_text(
                f"# {name}\n\n## Statement\n\nSomething true.\n\n"
                f"## Dependencies\n\n{dependencies}\n",
                encoding="utf-8",
            )
        if verdict is not None:
            self.verdict(root, name, verdict, at=at)
        return directory

    def verdict(self, root, name, value, *, at=BASE, filename="verdict.md"):
        path = root / "lemmas" / name / "verifier" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# Verdict: {value}\n\nBecause.\n", encoding="utf-8")
        os.utime(path, (at, at))
        return path

    def proof(self, root, name, *, at=BASE, version=1, body="Proof.\n"):
        path = root / "lemmas" / name / "generator" / f"proof_v{version}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        os.utime(path, (at, at))
        return path

    def findings(self, root):
        result = dag_gate.analyse(root)
        return result.metrics["findings"]

    # --- the empty and the clean cases -------------------------------------

    def test_no_lemmas_directory_stops_cleanly(self):
        """Statements live in sketch/refined_lemmas/ in some runs. Do not guess."""
        root = self.make_workspace()
        (root / "sketch" / "refined_lemmas").mkdir(parents=True)
        result = dag_gate.analyse(root)
        self.assertEqual(result.metrics["lemmas_dir"], "absent")
        self.assertEqual(result.metrics["nodes"], 0)
        self.assertEqual(result.warnings, [])

    def test_closed_graph_reports_nothing(self):
        """Two proved leaves and a proved assembly above them: no finding at all."""
        root = self.make_workspace()
        self.lemma(root, "leaf_alpha", dependencies="NONE.", verdict="PASS", at=BASE)
        self.lemma(root, "leaf_beta", dependencies="NONE.", verdict="PASS", at=BASE)
        self.lemma(
            root,
            "main_assembly",
            dependencies="`leaf_alpha`, `leaf_beta`.",
            verdict="PASS",
            at=BASE + 10 * MINUTE,
        )
        result = dag_gate.analyse(root)
        self.assertEqual(result.metrics["edges"], 2)
        for name, items in result.metrics["findings"].items():
            self.assertEqual(items, [], f"{name} fired on a clean graph")
        self.assertEqual(result.warnings, [])

    # --- reachability ------------------------------------------------------

    def test_statement_only_dependency_is_unproved_reachable(self):
        root = self.make_workspace()
        self.lemma(root, "leaf_alpha", dependencies="NONE.")  # no verdict at all
        self.lemma(
            root, "main_assembly", dependencies="`leaf_alpha`.", verdict="PASS"
        )
        findings = self.findings(root)
        self.assertEqual(len(findings["unproved_reachable"]), 1)
        self.assertIn("leaf_alpha", findings["unproved_reachable"][0])
        self.assertIn("statement-only", findings["unproved_reachable"][0])

    def test_unaccepted_top_node_is_reported(self):
        """The 2_8 shape: an assembly and its leaves, none of them accepted.

        `unproved_reachable` traverses from accepted tops only, so on its own it
        goes silent exactly here — the workspace where nothing at all is proved.
        The unaccepted top is its own finding so the gate cannot come back
        clean on a graph with no accepting verdict anywhere in it.
        """
        root = self.make_workspace()
        for leaf in ("data_semantics", "product_columns", "asymptotic_mode"):
            self.lemma(root, leaf, dependencies="NONE.")
        self.lemma(
            root,
            "main_assembly",
            dependencies="`product_columns`, `asymptotic_mode`, `data_semantics`.",
        )
        result = dag_gate.analyse(root)
        findings = result.metrics["findings"]
        self.assertEqual(len(findings["unaccepted_top_node"]), 1)
        self.assertIn("main_assembly", findings["unaccepted_top_node"][0])
        self.assertIn("statement-only", findings["unaccepted_top_node"][0])
        # Reachability still means what it meant: there is no accepted assembly
        # to traverse from, so it stays empty rather than double-reporting.
        self.assertEqual(findings["unproved_reachable"], [])
        self.assertEqual(result.metrics["status_counts"], {"statement-only": 4})
        self.assertTrue(result.warnings)

    def test_accepted_top_node_is_not_an_unaccepted_top_node(self):
        root = self.make_workspace()
        self.lemma(root, "leaf_alpha", dependencies="NONE.", verdict="PASS")
        self.lemma(
            root, "main_assembly", dependencies="`leaf_alpha`.", verdict="PASS",
            at=BASE + MINUTE,
        )
        self.assertEqual(self.findings(root)["unaccepted_top_node"], [])

    def test_a_directory_with_no_statement_is_not_an_unaccepted_top_node(self):
        """Q5's abandoned duplicates make no claim, and are already reported once."""
        root = self.make_workspace()
        (root / "lemmas" / "abandoned_duplicate").mkdir(parents=True)
        self.lemma(root, "lem_real", dependencies="NONE.", verdict="PASS")
        result = dag_gate.analyse(root)
        self.assertIn("abandoned_duplicate", result.metrics["top_nodes"])
        self.assertEqual(result.metrics["statement_missing"], ["abandoned_duplicate"])
        self.assertEqual(result.metrics["findings"]["unaccepted_top_node"], [])

    # --- warning list and its cap ------------------------------------------

    def test_warning_list_states_its_own_elision(self):
        """The count in the summary and the number of WARNING lines must agree.

        Q6 reported `unproved_reachable 15` and printed eight warnings with
        nothing saying the other seven existed.
        """
        root = self.make_workspace()
        leaves = [f"leaf_{index:02d}" for index in range(15)]
        for leaf in leaves:
            self.lemma(root, leaf, dependencies="NONE.")
        self.lemma(
            root,
            "main_assembly",
            dependencies="\n".join(f"- `{leaf}`" for leaf in leaves),
            verdict="PASS",
        )
        result = dag_gate.analyse(root)
        self.assertEqual(len(result.metrics["findings"]["unproved_reachable"]), 15)
        listed = [w for w in result.warnings if "reachable from an accepted assembly" in w]
        elision = [w for w in result.warnings if w.startswith("… ")]
        self.assertEqual(len(listed), dag_gate.DEFAULT_TOP_N)
        self.assertEqual(len(elision), 1)
        self.assertIn(str(15 - dag_gate.DEFAULT_TOP_N), elision[0])
        self.assertIn("unproved_reachable", elision[0])

    def test_no_elision_line_when_nothing_is_elided(self):
        root = self.make_workspace()
        self.lemma(root, "leaf_alpha", dependencies="NONE.")
        self.lemma(root, "main_assembly", dependencies="`leaf_alpha`.", verdict="PASS")
        result = dag_gate.analyse(root)
        self.assertEqual([w for w in result.warnings if w.startswith("… ")], [])

    # --- edge extraction ---------------------------------------------------

    def test_negation_yields_no_edge(self):
        """"No dependency on `lem_s9_rate`" is the opposite of an edge."""
        root = self.make_workspace()
        self.lemma(root, "lem_s9_rate", dependencies="NONE.")
        self.lemma(
            root,
            "lem_fragment_ceiling",
            dependencies="No dependency on `lem_s9_rate`, or on any covering statement.",
            verdict="PASS",
        )
        result = dag_gate.analyse(root)
        self.assertEqual(result.metrics["edges"], 0)
        self.assertEqual(result.metrics["findings"]["unproved_reachable"], [])
        self.assertEqual(result.metrics["findings"]["unreadable_dependency_field"], [])

    def test_does_not_depend_yields_no_edge(self):
        root = self.make_workspace()
        self.lemma(root, "lem_rejected_force", dependencies="NONE.")
        self.lemma(
            root,
            "thm_original_claim",
            dependencies="It does not depend on `lem_rejected_force`.",
            verdict="PASS",
        )
        self.assertEqual(dag_gate.analyse(root).metrics["edges"], 0)

    def test_disjunction_is_satisfied_by_one_member(self):
        """"exactly one of `A` or `B`" is one obligation, not two."""
        root = self.make_workspace()
        self.lemma(root, "route_alpha", dependencies="NONE.", verdict="PASS")
        self.lemma(root, "route_beta", dependencies="NONE.")  # never proved
        self.lemma(
            root,
            "main_assembly",
            dependencies="- exactly one of `route_alpha` or `route_beta`.",
            verdict="PASS",
            at=BASE + 10 * MINUTE,
        )
        result = dag_gate.analyse(root)
        self.assertEqual(result.metrics["disjunctive_groups"], 1)
        # route_beta is reachable, but the group is discharged by route_alpha,
        # so the unproved branch is not a finding.
        self.assertEqual(result.metrics["findings"]["accepted_before_dependency"], [])
        self.assertEqual(
            [f for f in result.metrics["findings"]["unproved_reachable"] if "route_alpha" in f],
            [],
        )

    def test_machine_readable_depends_on_is_preferred(self):
        root = self.make_workspace()
        self.lemma(root, "leaf_alpha", dependencies="NONE.", verdict="PASS")
        self.lemma(
            root,
            "main_assembly",
            dependencies="Depends-on: leaf_alpha\n\nProse that names `route_beta` in passing.",
            verdict="PASS",
            at=BASE + MINUTE,
        )
        result = dag_gate.analyse(root)
        self.assertEqual(result.metrics["dependency_readings"]["main_assembly"], "depends-on")
        self.assertEqual(result.metrics["edges"], 1)

    def test_depends_on_pipe_is_a_disjunctive_group(self):
        """`a | b` inside the field means the same as "exactly one of" in prose.

        Without this the field cannot express a disjunction, so a disjunctive
        lemma is pushed back into prose — and the field exists precisely to stop
        the graph depending on prose.
        """
        root = self.make_workspace()
        self.lemma(root, "leaf_alpha", dependencies="Depends-on: NONE", verdict="PASS")
        self.lemma(root, "leaf_beta", dependencies="Depends-on: NONE")
        self.lemma(
            root,
            "main_assembly",
            dependencies="Depends-on: leaf_alpha | leaf_beta",
            verdict="PASS",
            at=BASE + MINUTE,
        )
        result = dag_gate.analyse(root)
        self.assertEqual(result.metrics["dependency_readings"]["main_assembly"], "depends-on")
        self.assertEqual(result.metrics["disjunctive_groups"], 1)
        # leaf_beta never reached a verdict, but leaf_alpha discharges the group.
        self.assertEqual(result.metrics["findings"]["unproved_reachable"], [])

    def test_depends_on_comma_and_pipe_do_not_collide(self):
        root = self.make_workspace()
        self.lemma(root, "leaf_alpha", dependencies="Depends-on: NONE", verdict="PASS")
        self.lemma(root, "leaf_beta", dependencies="Depends-on: NONE", verdict="PASS")
        self.lemma(root, "leaf_gamma", dependencies="Depends-on: NONE", verdict="PASS")
        self.lemma(
            root,
            "main_assembly",
            dependencies="Depends-on: leaf_alpha, leaf_beta | leaf_gamma",
            verdict="PASS",
            at=BASE + MINUTE,
        )
        result = dag_gate.analyse(root)
        self.assertEqual(result.metrics["edges"], 3)
        self.assertEqual(result.metrics["disjunctive_groups"], 1)

    def test_depends_on_none_is_not_unreadable(self):
        root = self.make_workspace()
        self.lemma(root, "leaf_alpha", dependencies="Depends-on: NONE", verdict="PASS")
        result = dag_gate.analyse(root)
        self.assertEqual(result.metrics["edges"], 0)
        self.assertEqual(result.metrics["findings"]["unreadable_dependency_field"], [])

    def test_unreadable_dependency_field_is_counted(self):
        """A section that declares neither NONE nor any identifier."""
        root = self.make_workspace()
        self.lemma(
            root,
            "lem_vague",
            dependencies="Whatever the sketch decides once the plan settles.",
            verdict="PASS",
        )
        findings = self.findings(root)
        self.assertEqual(len(findings["unreadable_dependency_field"]), 1)
        self.assertIn("lem_vague", findings["unreadable_dependency_field"][0])

    def test_dependency_without_directory_is_separate_from_unproved(self):
        root = self.make_workspace()
        self.lemma(
            root,
            "main_assembly",
            dependencies="- `def:target_contract_scope`\n- `lem_never_written`",
            verdict="PASS",
        )
        findings = self.findings(root)
        declared = {item["declares"]: item for item in findings["dependency_without_directory"]}
        self.assertEqual(set(declared), {"def:target_contract_scope", "lem_never_written"})
        self.assertTrue(declared["def:target_contract_scope"]["off_graph_prefix"])
        self.assertFalse(declared["lem_never_written"]["off_graph_prefix"])
        self.assertEqual(findings["unproved_reachable"], [])

    # --- status resolution -------------------------------------------------

    def test_versioned_verdict_supersedes_a_stale_verdict_file(self):
        """44 verdict_v<N>.md files in the corpus sit beside a stale verdict.md.

        Reading the stale one mis-reports the lemma as FAIL. Version sort, not
        name sort: verdict_v10.md must beat verdict_v9.md.
        """
        root = self.make_workspace()
        self.lemma(root, "lem_revised", dependencies="NONE.")
        self.verdict(root, "lem_revised", "FAIL", filename="verdict.md")
        self.verdict(root, "lem_revised", "NEEDS_REVISION", filename="verdict_v1.md")
        self.verdict(root, "lem_revised", "PASS", filename="verdict_v2.md")
        result = dag_gate.analyse(root)
        self.assertEqual(result.metrics["status_counts"], {"PASS": 1})
        self.assertEqual(result.metrics["status_rules"]["lem_revised"], "verdict_v<N>")

    def test_version_sort_is_numeric_not_lexicographic(self):
        root = self.make_workspace()
        self.lemma(root, "lem_long_chain", dependencies="NONE.")
        self.verdict(root, "lem_long_chain", "PASS", filename="verdict_v9.md")
        self.verdict(root, "lem_long_chain", "FAIL", filename="verdict_v10.md")
        result = dag_gate.analyse(root)
        self.assertEqual(result.metrics["status_counts"], {"FAIL": 1})

    def test_review_packet_is_the_third_fallback(self):
        root = self.make_workspace()
        directory = self.lemma(root, "lem_packet_only", dependencies="NONE.")
        packet = directory / "verifier" / "review_packet_v3.md"
        packet.parent.mkdir(parents=True, exist_ok=True)
        packet.write_text(
            "# Review Packet: lem_packet_only (v3)\n\n## Verdict Snapshot\n- Verdict: PASS\n",
            encoding="utf-8",
        )
        result = dag_gate.analyse(root)
        self.assertEqual(result.metrics["status_rules"]["lem_packet_only"], "review_packet_v<N>")
        self.assertEqual(result.metrics["status_counts"], {"PASS": 1})

    # --- the two mtime-based findings --------------------------------------

    def test_accepted_before_dependency(self):
        """The dependent's PASS predates the dependency's own accepting verdict."""
        root = self.make_workspace()
        self.lemma(root, "lem_base", dependencies="NONE.", verdict="PASS", at=BASE + 109 * MINUTE)
        self.lemma(
            root,
            "lem_dependent",
            dependencies="- `lem_base` (D), (E).",
            verdict="PASS",
            at=BASE,
        )
        findings = self.findings(root)
        self.assertEqual(len(findings["accepted_before_dependency"]), 1)
        self.assertIn("lem_dependent", findings["accepted_before_dependency"][0])
        self.assertIn("lem_base", findings["accepted_before_dependency"][0])

    def test_dependency_accepted_first_is_not_a_finding(self):
        root = self.make_workspace()
        self.lemma(root, "lem_base", dependencies="NONE.", verdict="PASS", at=BASE)
        self.lemma(
            root,
            "lem_dependent",
            dependencies="- `lem_base`.",
            verdict="PASS",
            at=BASE + 30 * MINUTE,
        )
        self.assertEqual(self.findings(root)["accepted_before_dependency"], [])

    def test_stale_pass_when_a_dependency_is_rewritten_afterwards(self):
        """CLAUDE.md invariant 15: a PASS applies only to the artifact it checked."""
        root = self.make_workspace()
        self.lemma(root, "lem_base", dependencies="NONE.", verdict="PASS", at=BASE)
        self.proof(root, "lem_base", version=1, at=BASE - MINUTE)
        self.lemma(
            root,
            "lem_dependent",
            dependencies="- `lem_base`.",
            verdict="PASS",
            at=BASE + 10 * MINUTE,
        )
        self.assertEqual(self.findings(root)["stale_pass"], [])

        self.proof(root, "lem_base", version=2, at=BASE + 90 * MINUTE)
        findings = self.findings(root)
        self.assertEqual(len(findings["stale_pass"]), 1)
        self.assertIn("proof_v2.md", findings["stale_pass"][0])

    # --- obligation ledger -------------------------------------------------

    LEDGER = """### Load-Bearing Obligation Ledger

| Obligation | Type | Where supplied | Preconditions checked | Status |
|------------|------|----------------|-----------------------|--------|
| OB-1 the main bridge | direct | Step 4 | YES | resolved |
| OB-2 the set is {rel} | direct | Step 5 | YES | {second} |
| OB-3 the quoted bound | source | Step 6 | YES | {third} |
"""

    def ledger_proof(self, root, name, *, second, third, rel="relatively open"):
        self.lemma(root, name, dependencies="NONE.", verdict="PASS", at=BASE + MINUTE)
        self.proof(
            root,
            name,
            version=1,
            at=BASE,
            body=self.LEDGER.format(second=second, third=third, rel=rel),
        )

    def test_open_ledger_row_in_an_accepted_proof_is_a_finding(self):
        root = self.make_workspace()
        self.ledger_proof(root, "lem_accepted", second="**open**", third="resolved")
        findings = self.findings(root)
        self.assertEqual(len(findings["open_ledger_rows_in_accepted"]), 1)
        self.assertIn("OB-2", findings["open_ledger_rows_in_accepted"][0])

    def test_open_with_an_explanation_still_fires(self):
        root = self.make_workspace()
        self.ledger_proof(
            root, "lem_accepted", second="**open — Orchestrator; not a precondition**", third="open (Sketcher)"
        )
        self.assertEqual(len(self.findings(root)["open_ledger_rows_in_accepted"]), 2)

    def test_ledger_noise_phrases_do_not_fire(self):
        """The three phrases a substring match got wrong on the real corpus."""
        root = self.make_workspace()
        self.ledger_proof(
            root,
            "lem_accepted",
            second="quoted not assumed",
            third="**resolved** — no open obligation is reported",
            rel="relatively open",
        )
        self.assertEqual(self.findings(root)["open_ledger_rows_in_accepted"], [])

    def test_open_ledger_row_in_an_unaccepted_proof_is_not_a_finding(self):
        """An open obligation in a lemma that is still being worked is the point."""
        root = self.make_workspace()
        self.lemma(root, "lem_in_flight", dependencies="NONE.")
        self.proof(
            root,
            "lem_in_flight",
            body=self.LEDGER.format(second="**open**", third="resolved", rel="x"),
        )
        self.assertEqual(self.findings(root)["open_ledger_rows_in_accepted"], [])

    # --- cycles ------------------------------------------------------------

    def test_cycle_is_reported(self):
        """Nothing in this harness has ever checked this."""
        root = self.make_workspace()
        self.lemma(root, "thm_certificate", dependencies="- `lem_classes`.", verdict="PASS")
        self.lemma(root, "lem_classes", dependencies="- `thm_certificate` (A).", verdict="PASS")
        findings = self.findings(root)
        self.assertEqual(len(findings["cycles"]), 1)
        self.assertIn("thm_certificate", findings["cycles"][0])
        self.assertIn("lem_classes", findings["cycles"][0])

    def test_a_diamond_is_not_a_cycle(self):
        root = self.make_workspace()
        self.lemma(root, "leaf", dependencies="NONE.", verdict="PASS")
        self.lemma(root, "left_branch", dependencies="- `leaf`.", verdict="PASS")
        self.lemma(root, "right_branch", dependencies="- `leaf`.", verdict="PASS")
        self.lemma(
            root,
            "main_assembly",
            dependencies="- `left_branch`\n- `right_branch`",
            verdict="PASS",
        )
        self.assertEqual(self.findings(root)["cycles"], [])

    # --- exit codes --------------------------------------------------------

    def test_advisory_by_default_and_blocking_under_strict(self):
        root = self.make_workspace()
        self.lemma(root, "leaf_alpha", dependencies="NONE.")
        self.lemma(root, "main_assembly", dependencies="`leaf_alpha`.", verdict="PASS")
        self.assertEqual(dag_gate.main([str(root)]), 0)
        self.assertEqual(dag_gate.main([str(root), "--strict"]), 1)

    def test_clean_workspace_passes_strict(self):
        root = self.make_workspace()
        self.lemma(root, "leaf_alpha", dependencies="NONE.", verdict="PASS")
        self.assertEqual(dag_gate.main([str(root), "--strict"]), 0)

    def test_missing_workspace_is_an_error(self):
        root = self.make_workspace()
        result = dag_gate.analyse(root / "nowhere")
        self.assertFalse(result.ok)
        self.assertEqual(dag_gate.main([str(root / "nowhere")]), 1)


LEDGER_HEADED = """## Load-Bearing Obligation Ledger
| Obligation | Type | Status | Notes |
|---|---|---|---|
| LWE hardness | assumption | open | quoted from the contract file |
"""

LEDGER_STATUS_NOT_LAST = """## Load-Bearing Obligation Ledger
| Obligation | Type | Current status | Requested next action |
|---|---|---|---|
| bridge lemma | dependency | open | assign to lem_b |
"""

LEDGER_STATUS_LAST = """## Load-Bearing Obligation Ledger
| Obligation | Type | Notes | Status |
|---|---|---|---|
| LWE hardness | assumption | quoted from the contract file | open |
"""

LEDGER_HEADERLESS = """## Load-Bearing Obligation Ledger
| LWE hardness | assumption | open |
"""


class LedgerStatusColumnTests(unittest.TestCase):
    """The Status column is found by header name, not by position.

    Reading `cells[-1]` made `open_rows` return nothing the moment anything
    followed Status — including `| Current status | Requested next action |`,
    which is already in prompts/generator.md. That hid the open obligations the
    gate exists to surface.
    """

    def test_status_before_a_trailing_marker_column_is_still_read(self):
        self.assertEqual([("LWE hardness", "open")], dag_gate.ledger_rows(LEDGER_HEADED))
        self.assertEqual(1, len(dag_gate.open_rows(LEDGER_HEADED)))

    def test_status_before_a_trailing_action_column_is_still_read(self):
        self.assertEqual(
            [("bridge lemma", "open")], dag_gate.ledger_rows(LEDGER_STATUS_NOT_LAST)
        )
        self.assertEqual(1, len(dag_gate.open_rows(LEDGER_STATUS_NOT_LAST)))

    def test_status_last_keeps_working(self):
        self.assertEqual([("LWE hardness", "open")], dag_gate.ledger_rows(LEDGER_STATUS_LAST))
        self.assertEqual(1, len(dag_gate.open_rows(LEDGER_STATUS_LAST)))

    def test_a_ledger_with_no_header_line_falls_back_to_the_last_cell(self):
        # The existing corpus has these; a fix that only understood headers
        # would stop reading every one of them.
        self.assertEqual([("LWE hardness", "open")], dag_gate.ledger_rows(LEDGER_HEADERLESS))
        self.assertEqual(1, len(dag_gate.open_rows(LEDGER_HEADERLESS)))

    def test_two_ledgers_in_one_document_do_not_share_a_column_index(self):
        rows = dag_gate.ledger_rows(LEDGER_STATUS_NOT_LAST + "\n" + LEDGER_HEADERLESS)
        self.assertEqual([("bridge lemma", "open"), ("LWE hardness", "open")], rows)


class GroupedLemmaLayoutTests(unittest.TestCase):
    """`lemmas/<branch>/<lemma>/`, which every fixture above happens not to use.

    A real run grouped 39 statements under 11 branch folders. The gate walked one
    level, saw 11 directories with no statement.md, and printed 11 nodes, 0 edges
    and 0 findings -- a clean bill of health for a graph it could not see. The
    tests below are the fixture that was missing, not a new feature: a passing
    suite over flat fixtures is not evidence the walk is right.
    """

    def make_workspace(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return Path(temp.name)

    def lemma(self, root, name, *, dependencies=None, verdict=None, at=BASE):
        directory = root / "lemmas" / name
        directory.mkdir(parents=True, exist_ok=True)
        if dependencies is not None:
            (directory / "statement.md").write_text(
                f"# {name}\n\n## Statement\n\nSomething true.\n\n"
                f"## Dependencies\n\n{dependencies}\n",
                encoding="utf-8",
            )
        if verdict is not None:
            path = directory / "verifier" / "verdict.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# Verdict: {verdict}\n\nBecause.\n", encoding="utf-8")
            os.utime(path, (at, at))
        return directory

    def test_a_grouped_run_is_seen_at_all(self):
        root = self.make_workspace()
        self.lemma(root, "branch_one/leaf_alpha", dependencies="NONE.", verdict="PASS")
        self.lemma(root, "branch_one/leaf_beta", dependencies="NONE.", verdict="PASS")
        self.lemma(
            root,
            "branch_one/assembly",
            dependencies="Depends-on: leaf_alpha, leaf_beta",
            verdict="PASS",
            at=BASE + 10 * MINUTE,
        )
        result = dag_gate.analyse(root)
        self.assertEqual(3, result.metrics["nodes"])
        self.assertEqual(2, result.metrics["edges"])
        self.assertEqual([], result.metrics["statement_missing"])

    def test_a_branch_folder_is_not_itself_a_node(self):
        root = self.make_workspace()
        self.lemma(root, "branch_one/leaf_alpha", dependencies="NONE.", verdict="PASS")
        self.lemma(root, "branch_one/leaf_beta", dependencies="NONE.", verdict="PASS")
        self.assertEqual(
            ["branch_one/leaf_alpha", "branch_one/leaf_beta"], _node_names(root)
        )

    def test_a_verifier_directory_is_never_mistaken_for_a_lemma(self):
        root = self.make_workspace()
        self.lemma(root, "branch_one/leaf_alpha", dependencies="NONE.", verdict="PASS")
        self.assertEqual(["branch_one/leaf_alpha"], _node_names(root))

    def test_a_dependency_may_name_the_leaf_alone(self):
        """Nothing in the corpus writes `<branch>/<lemma>` in a Depends-on line."""
        root = self.make_workspace()
        self.lemma(root, "branch_one/leaf_alpha", dependencies="NONE.", verdict="PASS")
        self.lemma(
            root,
            "branch_two/assembly",
            dependencies="Depends-on: leaf_alpha",
            verdict="PASS",
            at=BASE + 10 * MINUTE,
        )
        result = dag_gate.analyse(root)
        self.assertEqual(1, result.metrics["edges"])
        self.assertEqual([], result.metrics["findings"]["dependency_without_directory"])

    def test_a_cycle_across_two_branches_is_still_found(self):
        root = self.make_workspace()
        self.lemma(root, "branch_one/alpha", dependencies="Depends-on: beta", verdict="PASS")
        self.lemma(root, "branch_two/beta", dependencies="Depends-on: alpha", verdict="PASS")
        result = dag_gate.analyse(root)
        self.assertTrue(result.metrics["findings"]["cycles"])

    def test_an_empty_directory_is_still_reported_as_a_node(self):
        """A lemma directory holding nothing is a finding, not a folder to skip."""
        root = self.make_workspace()
        (root / "lemmas" / "abandoned").mkdir(parents=True)
        self.lemma(root, "branch_one/leaf_alpha", dependencies="NONE.", verdict="PASS")
        result = dag_gate.analyse(root)
        self.assertIn("abandoned", result.metrics["statement_missing"])

    def test_a_flat_run_is_unchanged(self):
        """The regression that matters most: bare names stay bare."""
        root = self.make_workspace()
        self.lemma(root, "leaf_alpha", dependencies="NONE.", verdict="PASS")
        self.lemma(
            root,
            "main_assembly",
            dependencies="Depends-on: leaf_alpha",
            verdict="PASS",
            at=BASE + 10 * MINUTE,
        )
        result = dag_gate.analyse(root)
        self.assertEqual(2, result.metrics["nodes"])
        self.assertEqual(1, result.metrics["edges"])
        self.assertEqual([], result.metrics["findings"]["dependency_without_directory"])


class InheritedObligationTests(unittest.TestCase):
    """An obligation left open in a dependency does not stop at that dependency."""

    def make_workspace(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return Path(temp.name)

    LEDGER = (
        "## Load-Bearing Obligation Ledger\n\n"
        "| Obligation | Type | Where | Status |\n"
        "|---|---|---|---|\n"
        "| the bridge bound | estimate | step 4 | {status} |\n"
    )

    def lemma(self, root, name, *, dependencies, verdict, ledger_status=None):
        directory = root / "lemmas" / name
        (directory / "generator").mkdir(parents=True, exist_ok=True)
        (directory / "statement.md").write_text(
            f"# {name}\n\n## Dependencies\n\n{dependencies}\n", encoding="utf-8"
        )
        body = "Proof.\n"
        if ledger_status:
            body += "\n" + self.LEDGER.format(status=ledger_status)
        proof = directory / "generator" / "proof_v1.md"
        proof.write_text(body, encoding="utf-8")
        os.utime(proof, (BASE, BASE))
        verdict_path = directory / "verifier" / "verdict.md"
        verdict_path.parent.mkdir(parents=True, exist_ok=True)
        verdict_path.write_text(f"# Verdict: {verdict}\n", encoding="utf-8")
        os.utime(verdict_path, (BASE + 10 * MINUTE, BASE + 10 * MINUTE))

    def test_an_open_row_in_a_dependency_reaches_the_lemma_above(self):
        root = self.make_workspace()
        self.lemma(root, "dep", dependencies="NONE.", verdict="PASS", ledger_status="open")
        self.lemma(root, "above", dependencies="Depends-on: dep", verdict="PASS")
        findings = dag_gate.analyse(root).metrics["findings"]
        # dep's own ledger row is the per-node finding; that `above` is standing
        # on it is the one the graph is traversed for.
        self.assertTrue(
            any(item.startswith("dep/") for item in findings["open_ledger_rows_in_accepted"])
        )
        self.assertTrue(findings["inherited_open_obligations"])
        self.assertIn("above stands on dep", findings["inherited_open_obligations"][0])

    def test_it_follows_the_edge_transitively(self):
        root = self.make_workspace()
        self.lemma(root, "bottom", dependencies="NONE.", verdict="PASS", ledger_status="blocker")
        self.lemma(root, "middle", dependencies="Depends-on: bottom", verdict="PASS")
        self.lemma(root, "top", dependencies="Depends-on: middle", verdict="PASS")
        findings = dag_gate.analyse(root).metrics["findings"]
        self.assertTrue(
            any(item.startswith("top stands on bottom")
                for item in findings["inherited_open_obligations"])
        )

    def test_a_resolved_dependency_is_not_reported(self):
        root = self.make_workspace()
        self.lemma(root, "dep", dependencies="NONE.", verdict="PASS", ledger_status="resolved")
        self.lemma(root, "above", dependencies="Depends-on: dep", verdict="PASS")
        findings = dag_gate.analyse(root).metrics["findings"]
        self.assertEqual([], findings["inherited_open_obligations"])

    def test_an_unaccepted_lemma_inherits_nothing_it_has_not_claimed(self):
        """It is not standing on anything yet; unproved_reachable is that job."""
        root = self.make_workspace()
        self.lemma(root, "dep", dependencies="NONE.", verdict="PASS", ledger_status="open")
        self.lemma(root, "above", dependencies="Depends-on: dep", verdict="FAIL")
        findings = dag_gate.analyse(root).metrics["findings"]
        self.assertEqual([], findings["inherited_open_obligations"])

    def test_a_cycle_does_not_hang_the_walk(self):
        root = self.make_workspace()
        self.lemma(root, "a", dependencies="Depends-on: b", verdict="PASS", ledger_status="open")
        self.lemma(root, "b", dependencies="Depends-on: a", verdict="PASS")
        findings = dag_gate.analyse(root).metrics["findings"]
        self.assertTrue(findings["cycles"])


def _node_names(root):
    sys.path.insert(0, str(REPO_ROOT / "cli_tools"))
    from _gate.completion import lemma_directories

    return lemma_directories(root)

class StatusDialectTests(unittest.TestCase):
    """19 of 54 run roots track lemmas in no table the completion gate reads.

    The gate said so, once per directory, at the moment a run claimed
    completion. These fix that it is said once, and said during the run.
    """

    def make_workspace(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return Path(temp.name)

    def lemmas(self, root, *names):
        for name in names:
            directory = root / "lemmas" / name
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "statement.md").write_text(
                f"# {name}\n\n## Statement\n\nX.\n\n## Dependencies\n\nDepends-on: NONE\n",
                encoding="utf-8",
            )
        return root

    def status(self, root, text):
        (root / "STATUS.md").write_text(text, encoding="utf-8")

    def analyse(self, root):
        return dag_gate.analyse(root)

    def test_branch_queue_dialect_reports_every_lemma_as_untracked(self):
        root = self.lemmas(self.make_workspace(), "a", "b")
        self.status(root, "# s\n\n## Active Branch Queue\n\n| Rank | Branch |\n|---|---|\n| 1 | r |\n")
        result = self.analyse(root)
        self.assertEqual("branch-queue", result.metrics["status_dialect"])
        self.assertEqual(
            ["a", "b"], result.metrics["findings"]["lemmas_untracked_in_status"]
        )
        self.assertTrue(any("tracked nowhere" in w for w in result.warnings))

    def test_lemma_status_dialect_defers_to_the_completion_gate(self):
        """Reconciling rows against directories is that gate's job, not this one."""
        root = self.lemmas(self.make_workspace(), "a")
        self.status(root, "# s\n\n## Lemma Status\n\n| Lemma | Status |\n|---|---|\n| a | PASS |\n")
        result = self.analyse(root)
        self.assertEqual("lemma-status", result.metrics["status_dialect"])
        self.assertEqual([], result.metrics["findings"]["lemmas_untracked_in_status"])
        self.assertFalse(any("tracked nowhere" in w for w in result.warnings))

    def test_both_dialects_present_also_defers(self):
        root = self.lemmas(self.make_workspace(), "a")
        self.status(root, "# s\n\n## Lemma Status\n\n| a |\n\n## Active Branch Queue\n\n| r |\n")
        self.assertEqual("both", self.analyse(root).metrics["status_dialect"])

    def test_neither_dialect_is_named_as_such(self):
        root = self.lemmas(self.make_workspace(), "a")
        self.status(root, "# s\n\n## Target\n\nProve X.\n")
        result = self.analyse(root)
        self.assertEqual("neither", result.metrics["status_dialect"])
        self.assertEqual(["a"], result.metrics["findings"]["lemmas_untracked_in_status"])

    def test_a_missing_status_file_is_not_reported_as_untracked_lemmas(self):
        """Absence of the file is a different fact and must not be dressed as this one."""
        root = self.lemmas(self.make_workspace(), "a")
        result = self.analyse(root)
        self.assertEqual("no STATUS.md", result.metrics["status_dialect"])
        self.assertEqual([], result.metrics["findings"]["lemmas_untracked_in_status"])


if __name__ == "__main__":
    unittest.main()
