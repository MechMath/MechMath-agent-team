"""Regression cases for the discovery gate (ADR 0023 §5.1).

Each test is a mechanism from the cross-workspace forensics. The gate is
structural — it never reads mathematics — so what these assert is narrow: that a
route cannot be written off harder than its evidence allows, and that an empty
search cannot be recorded as an absent object.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "cli_tools"))

from _gate import discovery as discovery_gate  # noqa: E402
from _gate import waiver  # noqa: E402


class DiscoveryGateTests(unittest.TestCase):
    def workspace(self, *, status: str = "", artifacts: dict | None = None,
                  proof: str | None = None) -> tuple[tempfile.TemporaryDirectory, Path]:
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        if status:
            (root / "STATUS.md").write_text(status, encoding="utf-8")
        for name, body in (artifacts or {}).items():
            path = root / "discovery" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        if proof is not None:
            (root / "proof.tex").write_text(proof, encoding="utf-8")
        return temp, root

    def errors(self, **kwargs) -> list[str]:
        temp, root = self.workspace(**kwargs)
        with temp:
            return discovery_gate.run(root).errors

    def result(self, **kwargs):
        temp, root = self.workspace(**kwargs)
        with temp:
            return discovery_gate.run(root)

    # --- case A / H: a failed attempt is not a refuted theorem -----------

    def test_rejected_without_evidence_is_an_error(self):
        """2_2_old: a convention error inside a frozen box became rejected,
        was popped, and was never revisited across 93 further ranks."""
        errors = self.errors(status="| 1 | PSLQ in normalized coords | CE | rejected |\n")
        self.assertTrue(any("rejected" in e and "counterexample" in e for e in errors), errors)

    def test_rejected_with_counterexample_passes(self):
        errors = self.errors(
            status="| 1 | rank-3 certificate | Verifier | rejected — counterexample at n=4 |\n"
        )
        self.assertEqual([], errors)

    def test_rejected_with_verifier_fail_passes(self):
        errors = self.errors(status="| 1 | route | Verifier | rejected (Verifier FAIL) |\n")
        self.assertEqual([], errors)

    def test_retired_status_is_an_error(self):
        """inconclusive survived in the cookbook but named no state; every
        reader collapsed it to 'not PASS', which is what made renaming free."""
        errors = self.errors(status="| 1 | sibling transfer | Explorer | inconclusive |\n")
        self.assertTrue(any("retired status" in e for e in errors), errors)

    def test_blocked_needs_a_named_condition(self):
        errors = self.errors(status="| 1 | Bloch group route | Explorer | blocked |\n")
        self.assertTrue(any("blocked" in e and "condition" in e for e in errors), errors)

    def test_blocked_with_condition_passes(self):
        errors = self.errors(
            status="| 1 | Bloch group route | Explorer | blocked until the human supplies log 2 |\n"
        )
        self.assertEqual([], errors)

    def test_open_is_always_fine(self):
        errors = self.errors(status="| 1 | anything | Explorer | open |\n")
        self.assertEqual([], errors)

    # --- case E: an empty search is about the scope ----------------------

    def test_empty_search_must_name_the_next_scope(self):
        """2_5: one frame came up empty and the run treated the question as
        closed. The frame that would have worked cost 0.455 seconds."""
        errors = self.errors(artifacts={
            "triage_1.md": "NO_RESULT_IN_DECLARED_SCOPE\n  searched: basis [w_i, G, 1]\n"
        })
        self.assertTrue(any("next:" in e for e in errors), errors)

    def test_empty_search_with_both_fields_passes(self):
        errors = self.errors(artifacts={
            "triage_1.md": (
                "NO_RESULT_IN_DECLARED_SCOPE\n"
                "  searched: basis [w_i, G, 1], height <= 12\n"
                "  next: raw w_i coordinates, basis [w_i, G, log2, 1]\n"
            )
        })
        self.assertEqual([], errors)

    # --- case B: a gap is a work order ----------------------------------

    def test_gap_specification_needs_consumed_at(self):
        """3_1: brainstorm_26 wrote the specification the eventual solution
        needed, then abandoned because something was absent."""
        errors = self.errors(artifacts={
            "prospect_1.md": "first_missing: a target-independently specified finite-order subgroup\n"
        })
        self.assertTrue(any("consumed_at" in e for e in errors), errors)

    def test_gap_specification_with_consumed_at_passes(self):
        errors = self.errors(artifacts={
            "prospect_1.md": (
                "first_missing: a target-independently specified finite-order subgroup\n"
                "consumed_at: lemma 4, the lattice bridge\n"
            )
        })
        self.assertEqual([], errors)

    # --- case A: a prohibition closes one box, with evidence -------------

    def test_closed_off_line_needs_evidence(self):
        errors = self.errors(artifacts={
            "notes.md": "## Closed Off\n- scope: basis [w_i, G, 1], height <= 12\n"
        })
        self.assertTrue(any("evidence" in e for e in errors), errors)

    # --- region separation ----------------------------------------------

    def test_proof_may_not_cite_discovery(self):
        errors = self.errors(proof="\\input{discovery/prospect_1.md}\n")
        self.assertTrue(any("discovery/" in e for e in errors), errors)

    # --- invented tokens advise, they do not block -----------------------

    def test_invented_status_token_is_a_warning(self):
        """Seven such tokens appeared across the runs and none was defined
        anywhere, so downstream every one of them meant the same thing."""
        temp, root = self.workspace(artifacts={
            "prospect_1.md": "DISPOSITION=INCONCLUSIVE\nRANK3_EXECUTABLE=NO\n"
        })
        with temp:
            result = discovery_gate.run(root)
        self.assertEqual([], result.errors)
        self.assertTrue(any("not a status word" in w for w in result.warnings))


class RealWorkspaceShapeTests(DiscoveryGateTests):
    """What the first real run wrote, which the first version of this gate missed.

    The gate read one file per workspace and parsed zero status rows out of it.
    Every case here is a shape taken from `ESConjecture/0806`.
    """

    def artifacts(self, name: str, body: str) -> list[str]:
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = Path(temp.name)
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
            return discovery_gate.run(root).errors

    def test_status_cell_may_carry_bold_and_trailing_prose(self):
        """Real outcome cells read `**done** - superseded and exceeded by ...`;
        requiring the whole cell to equal a status word saw nothing at all."""
        rows = discovery_gate._status_rows(
            "| B1 | Explicit rate | Generator | **done** — superseded and exceeded |\n"
        )
        self.assertEqual([(1, "done", rows[0][2])], rows)

    def test_a_description_column_is_not_a_status(self):
        errors = self.errors(
            status="| B4 | open question about the covering direction | Explorer | done |\n"
        )
        self.assertEqual([], errors)

    def test_blocked_may_name_its_condition_after_a_colon(self):
        errors = self.errors(
            status="| — | sieve to 10^9 | Code Executor | **blocked**: cannot run on this machine |\n"
        )
        self.assertEqual([], errors)

    def test_artifacts_are_found_outside_a_discovery_directory(self):
        """No run has ever created `discovery/`; they write routes/, logs/, ..."""
        errors = self.artifacts(
            "routes/brainstorm_1.md",
            "# 7. Gap specifications\n\n**G2 — the constant `c`.**\nA closed form.\n",
        )
        self.assertTrue(any("consumed_at" in e for e in errors), errors)

    def test_an_artifact_under_lemmas_is_read(self):
        """The old inclusion list left `lemmas/` out as 'the certification
        region'. One workspace declared `Mode: DISCOVERY` in 23 files there."""
        errors = self.artifacts(
            "lemmas/branch_one/leaf_alpha/statement.md",
            "# 7. Gap specifications\n\n**G2 — the constant `c`.**\nA closed form.\n",
        )
        self.assertTrue(any("consumed_at" in e for e in errors), errors)

    def test_an_artifact_in_a_directory_no_list_anticipated_is_read(self):
        """`computations/`, `queries/`, `references/` all hold them too. A gate
        whose reach is an inclusion list is short by whatever a run invents next."""
        errors = self.artifacts(
            "computations/sweep_3/notes.md",
            "# 7. Gap specifications\n\n**G2 — the constant `c`.**\nA closed form.\n",
        )
        self.assertTrue(any("consumed_at" in e for e in errors), errors)

    def test_the_mechanical_memory_index_is_not_read_back(self):
        """`memory/index.md` quotes other artifacts verbatim. Reading it reports
        their defects a second time, against a path whose owner cannot fix them."""
        errors = self.artifacts(
            "memory/index.md",
            "# 7. Gap specifications\n\n**G2 — the constant `c`.**\nA closed form.\n",
        )
        self.assertEqual([], errors)

    def test_mentioning_the_empty_search_tag_is_not_emitting_it(self):
        errors = self.artifacts(
            "logs/explorer_1.md",
            "No `NO_RESULT_IN_DECLARED_SCOPE` condition arose — every experiment\n"
            "returned data within its declared scope.\n",
        )
        self.assertEqual([], errors)

    def test_closed_off_fields_may_span_the_bullet(self):
        errors = self.artifacts(
            "recovery/regulator_decision_1.md",
            "## Closed Off\n\n"
            "- `scope:` counterexample search by CRT construction.\n"
            "  `evidence:` `routes/counterexample_1.md` §4.1\n",
        )
        self.assertEqual([], errors)

    def test_a_discovery_artifact_outside_discovery_is_still_discovery(self):
        """Runs write discovery output to `code/`, `routes/`, `ce/` -- wherever
        the dispatch names. Region separation therefore reads the artifact's
        declared mode, not its path."""
        temp = tempfile.TemporaryDirectory()
        with temp:
            root = Path(temp.name)
            (root / "code").mkdir()
            (root / "code" / "q1_findings.md").write_text(
                "**Mode: DISCOVERY.** Conjectural evidence.\n", encoding="utf-8"
            )
            (root / "code" / "audit_1.md").write_text(
                "**Mode: CERTIFICATION.** Fresh Verifier.\n", encoding="utf-8"
            )
            (root / "proof.tex").write_text(
                "See code/q1_findings.md for the tables.\n", encoding="utf-8"
            )
            first = discovery_gate.run(root).errors
            (root / "proof.tex").write_text(
                "See code/audit_1.md for the audit.\n", encoding="utf-8"
            )
            second = discovery_gate.run(root).errors
        self.assertTrue(any("declares discovery mode" in e for e in first), first)
        self.assertEqual([], second)

    def test_a_long_searched_block_still_reaches_its_next_field(self):
        body = (
            "```\nNO_RESULT_IN_DECLARED_SCOPE\n  searched: for each i in 9..41,\n"
            + "".join(f"    (S{i}) a further enumerated frame\n" for i in range(12))
            + "  next: raw coordinates, basis [w_i, G, log2, 1]\n```\n"
        )
        self.assertEqual([], self.artifacts("search/source_report.md", body))


class WaiverTests(unittest.TestCase):
    def test_waiver_clears_errors_and_records_them(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            errors, waived = waiver.apply_waiver(
                ["boom"], "regex misfired on an honest progress note",
                gate="discovery", workspace=root,
            )
            self.assertEqual([], errors)
            self.assertEqual(["boom"], waived)
            entries = waiver.read_waivers(root)
            self.assertEqual(1, len(entries))
            self.assertEqual("discovery", entries[0]["gate"])

    def test_no_reason_means_no_waiver(self):
        errors, waived = waiver.apply_waiver(["boom"], None, gate="discovery")
        self.assertEqual(["boom"], errors)
        self.assertEqual([], waived)

    def test_requirement_text_has_three_sections(self):
        text = waiver.requirement_text(checks="a", legal="b", fix="c")
        for heading in ("Checks:", "Legal values:", "If it fails:"):
            self.assertIn(heading, text)

class RejectionScopeTests(DiscoveryGateTests):
    """How far a rejection reaches, which the vocabulary has no field for.

    Runs write it by hand -- `rejected: exact NW9 rule only`, paired with a
    `Non-goals: ... remain open` clause -- and the parser read the first word of
    the cell and discarded the rest. The harness's own long-term memory already
    carries the lesson: a counterexample certifies that a statement is false; it
    does not delimit how it is false.
    """

    SCOPED = (
        "| 1 | NW9 rule | CE | counterexample in routes/ce_1.md | "
        "rejected: exact NW9 rule only |\n"
    )
    BARE = "| 1 | NW9 rule | CE | counterexample in routes/ce_1.md | rejected |\n"

    def test_a_scoped_rejection_is_recorded_as_data(self):
        result = self.result(status=self.SCOPED)
        self.assertEqual(1, len(result.rejections))
        self.assertEqual("exact NW9 rule only", result.rejections[0]["scope"])

    def test_a_scoped_rejection_does_not_warn(self):
        result = self.result(status=self.SCOPED)
        self.assertFalse(any("without saying how far" in w for w in result.warnings))

    def test_an_unqualified_rejection_warns(self):
        result = self.result(status=self.BARE)
        self.assertTrue(any("without saying how far" in w for w in result.warnings))

    def test_an_unqualified_rejection_is_not_an_error(self):
        """The evidence requirement is the hard one. Rows written before this
        existed must still pass."""
        result = self.result(status=self.BARE)
        self.assertEqual([], result.errors)
        self.assertTrue(result.ok)

    def test_evidence_in_another_column_does_not_count_as_scope(self):
        """Reading the whole row picked up 'exact counterexample' from the
        evidence column and called a bare rejection scoped."""
        result = self.result(
            status="| 1 | NW9 | CE | an exact counterexample only, routes/ce_1.md | rejected |\n"
        )
        self.assertTrue(any("without saying how far" in w for w in result.warnings))
        self.assertEqual("", result.rejections[0]["scope"])

    def test_a_non_goals_clause_counts(self):
        result = self.result(
            status="| 1 | NW9 | CE | counterexample in routes/ce_1.md | "
            "rejected — other sections remain open |\n"
        )
        self.assertFalse(any("without saying how far" in w for w in result.warnings))


if __name__ == "__main__":
    unittest.main()
