"""Progress summary gate: one check per half of the complaint it implements.

The complaint was that progress notes are too long, miss the point, are badly
structured, carry too much jargon and self-invented vocabulary, and do not
accurately summarise progress. Each of those is a test class here. The last
class is the one that matters most: a lint that refuses good documents is worse
than no lint, because a run learns to route around it.

2026-08-28: the summary became LaTeX compiled to a PDF, on the grounds that the
document a person reads is the one that has to be typeset. Every fixture here
is a compilable standalone document as a result, and the budgets are measured
on the body -- so is every line number these tests assert on.
"""

from pathlib import Path
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "cli_tools"))
from _gate import summary as summary_gate


PREAMBLE = r"""\documentclass[11pt,a4paper]{article}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath,amssymb,url}
\providecommand{\path}[1]{\texttt{#1}}
\title{Connes embedding for the cloning overgroup family}
\date{}

\begin{document}
\maketitle
"""

GOOD = PREAMBLE + r"""
\section{The statement}

Let $G_k$ be the cloning overgroup of $F_k$ for $k\ge2$. The claim is that
$\Lambda(G_k)$ embeds into an ultrapower of the hyperfinite factor.

\section{Where this stands}

The original statement is open. Two of its three reductions are proved and the
third is blocked on a finite computation nobody has run.

\section{What is blocked}

Whether the vertical Fox derivative detector is well defined on the order-$103$
global list. Every route now passes through it.

\section{What is established}

\begin{itemize}
  \item \textbf{Statement.} For every $k\ge2$ the expansion map factors as
        $\varepsilon_k=\pi_k\circ\iota_k$ with $\iota_k$ injective.
        \textbf{Sketch.} Both maps are built from the fold move, which acts two
        generators at a time; injectivity is the rank computation on the
        resulting blocks.
        \path{lemmas/cloning_fold_restart_2/cf2_expansion_factorization/}
\end{itemize}

\section{What was ruled out}

\begin{itemize}
  \item Deriving the detector from the twisted coset funnel: injectivity fails
        at the edge map, and no weakening of the hypotheses recovers it.
\end{itemize}

\section{What to do next}

\begin{enumerate}
  \item Run the finite check on the order-$103$ list.
\end{enumerate}

\section{Terms coined here}

\begin{itemize}
  \item vertical Fox derivative detector --- the map sending a relator to the
        vector of its Fox derivatives along the vertical subgroup.
\end{itemize}

\end{document}
"""

ESTABLISHED_ITEM = (
    "  \\item \\textbf{Statement.} For every $k\\ge2$ the expansion map factors as\n"
    "        $\\varepsilon_k=\\pi_k\\circ\\iota_k$ with $\\iota_k$ injective.\n"
    "        \\textbf{Sketch.} Both maps are built from the fold move, which acts two\n"
    "        generators at a time; injectivity is the rank computation on the\n"
    "        resulting blocks.\n"
    "        \\path{lemmas/cloning_fold_restart_2/cf2_expansion_factorization/}\n"
)

COINED = (
    "\\begin{itemize}\n"
    "  \\item vertical Fox derivative detector --- the map sending a relator to the\n"
    "        vector of its Fox derivatives along the vertical subgroup.\n"
    "\\end{itemize}\n"
)


def write(text):
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".tex", delete=False, encoding="utf-8"
    )
    handle.write(text)
    handle.close()
    return Path(handle.name)


class BaselineTests(unittest.TestCase):
    def test_a_well_formed_summary_passes(self):
        path = write(GOOD)
        self.addCleanup(path.unlink)
        result = summary_gate.lint_file(path)
        self.assertEqual([], result.errors, result.errors)
        self.assertEqual([], result.warnings)

    def test_a_missing_file_says_where_the_spec_is(self):
        result = summary_gate.lint_file(Path("/nonexistent/progress_summary.tex"))
        self.assertTrue(any("prompts/writer.md" in e for e in result.errors))


class CompiledDocumentTests(unittest.TestCase):
    """The artifact a person opens is the PDF, so the source must compile.

    A `.tex` that does not compile leaves the reader with nothing, and leaves
    it looking exactly like a run that stopped without writing anything.
    """

    def test_a_fragment_without_a_preamble_is_refused(self):
        path = write("\\section{Where this stands}\n\nOpen.\n")
        self.addCleanup(path.unlink)
        errors = " ".join(summary_gate.lint_file(path).errors)
        self.assertIn("\\begin{document}", errors)
        self.assertIn("\\documentclass", errors)

    def test_the_preamble_does_not_spend_the_budget(self):
        """Budgets are measured on the body. Otherwise a longer preamble is a
        shorter document, which is the opposite of what the cap is for."""
        result = summary_gate.lint_file(write(GOOD))
        expected = PREAMBLE.splitlines().index("\\begin{document}") + 1
        self.assertEqual(expected, result.metrics["preamble_lines"])
        self.assertLess(result.metrics["lines"], len(GOOD.splitlines()))

    def test_the_body_stops_at_end_document(self):
        """The last required section otherwise carries `\\end{document}`, so
        "this section is empty" is undecidable for whichever section is last --
        and that is `Terms coined here`, every time, by construction."""
        path = write(GOOD.replace(COINED, ""))
        self.addCleanup(path.unlink)
        result = summary_gate.lint_file(path)
        self.assertTrue(
            any("this document coins no terms" in e for e in result.errors),
            result.errors,
        )

    def test_a_missing_pdf_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "writer").mkdir()
            (workspace / summary_gate.SUMMARY_NAME).write_text(GOOD, encoding="utf-8")
            errors = " ".join(summary_gate.lint_workspace(workspace).errors)
            self.assertIn("progress_summary.pdf", errors)

    def test_an_exported_pdf_satisfies_it(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "writer").mkdir()
            (workspace / summary_gate.SUMMARY_NAME).write_text(GOOD, encoding="utf-8")
            (workspace / summary_gate.SUMMARY_PDF).write_bytes(b"%PDF-1.5\n")
            self.assertEqual([], summary_gate.lint_workspace(workspace).errors)


class PageCountTests(unittest.TestCase):
    """The complaint was made in pages, so one check is made in pages."""

    def _workspace(self, directory, log_text):
        workspace = Path(directory)
        (workspace / "writer").mkdir()
        (workspace / summary_gate.SUMMARY_NAME).write_text(GOOD, encoding="utf-8")
        (workspace / summary_gate.SUMMARY_PDF).write_bytes(b"%PDF-1.5\n")
        if log_text is not None:
            (workspace / "writer" / "progress_summary.log").write_text(
                log_text, encoding="utf-8"
            )
        return workspace

    def test_a_long_pdf_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = self._workspace(
                directory, "Output written on progress_summary.pdf (49 pages, 333576 bytes)"
            )
            result = summary_gate.lint_workspace(workspace)
            self.assertEqual(49, result.metrics["pages"])
            self.assertTrue(any("49 pages" in e for e in result.errors))

    def test_a_single_page_log_says_page_not_pages(self):
        """pdflatex writes "1 page," and a `pages` -only pattern misses it."""
        with tempfile.TemporaryDirectory() as directory:
            workspace = self._workspace(
                directory, "Output written on progress_summary.pdf (1 page, 79114 bytes)"
            )
            result = summary_gate.lint_workspace(workspace)
            self.assertEqual(1, result.metrics["pages"])
            self.assertEqual([], result.errors)

    def test_no_log_reports_null_rather_than_a_pass(self):
        """Not checked must never read as checked-and-fine."""
        with tempfile.TemporaryDirectory() as directory:
            workspace = self._workspace(directory, None)
            result = summary_gate.lint_workspace(workspace)
            self.assertIsNone(result.metrics["pages"])
            self.assertEqual([], result.errors)


class TooLongTests(unittest.TestCase):
    def test_over_the_line_cap_fails(self):
        filler = "\nFiller sentence.\n" * 200
        path = write(GOOD.replace("\\section{Terms coined here}", filler + "\\section{Terms coined here}"))
        self.addCleanup(path.unlink)
        result = summary_gate.lint_file(path)
        self.assertTrue(
            any(f"against a cap of {summary_gate.MAX_LINES}" in e for e in result.errors),
            result.errors,
        )

    def test_the_cap_message_forbids_shortening_the_restart_document(self):
        """ADR 0021 bought that length deliberately; this must not trade it back."""
        path = write(GOOD.replace("\\end{document}", "\nx\n" * 320 + "\\end{document}"))
        self.addCleanup(path.unlink)
        result = summary_gate.lint_file(path)
        self.assertTrue(any("progress_notes.tex" in e for e in result.errors))


class MissesThePointTests(unittest.TestCase):
    def test_a_late_blocker_fails(self):
        body = GOOD.replace(
            "\\section{What is blocked}\n\nWhether the vertical Fox derivative detector is well defined on the order-$103$\nglobal list. Every route now passes through it.\n\n",
            "",
        )
        # Padded past BLOCKER_MAX_LINE so the absolute rule cannot rescue it:
        # a short document is allowed any layout, and this test is about a long
        # one that buries the blocker.
        body = body.replace(
            "\\section{Terms coined here}",
            "Filler line.\n" * 40
            + "\n\\section{What is blocked}\n\nThe detector.\n\n\\section{Terms coined here}",
        )
        path = write(body)
        self.addCleanup(path.unlink)
        result = summary_gate.lint_file(path)
        self.assertTrue(
            any("The reader came for this" in e for e in result.errors), result.errors
        )

    def test_a_lead_that_rambles_fails(self):
        path = write(GOOD.replace(
            "The original statement is open. Two of its three reductions are proved and the\nthird is blocked on a finite computation nobody has run.",
            "One. Two. Three. Four. Five. Six. Seven. Eight. Nine.",
        ))
        self.addCleanup(path.unlink)
        result = summary_gate.lint_file(path)
        self.assertTrue(any("9 sentences" in e for e in result.errors), result.errors)

    def test_an_empty_lead_says_what_the_first_sentence_must_answer(self):
        path = write(GOOD.replace(
            "The original statement is open. Two of its three reductions are proved and the\nthird is blocked on a finite computation nobody has run.",
            "",
        ))
        self.addCleanup(path.unlink)
        result = summary_gate.lint_file(path)
        self.assertTrue(any("proved, disproved" in e for e in result.errors))


class BadStructureTests(unittest.TestCase):
    def test_a_missing_section_is_named(self):
        path = write(GOOD.replace("\\section{What was ruled out}", "\\section{Dead ends}"))
        self.addCleanup(path.unlink)
        result = summary_gate.lint_file(path)
        self.assertTrue(any("What was ruled out" in e for e in result.errors))

    def test_sections_out_of_order_fail(self):
        body = GOOD.replace("\\section{What is blocked}", "\\section{ZZ}").replace(
            "\\section{What is established}", "\\section{What is blocked}"
        ).replace("\\section{ZZ}", "\\section{What is established}")
        path = write(body)
        self.addCleanup(path.unlink)
        result = summary_gate.lint_file(path)
        self.assertTrue(any("out of order" in e for e in result.errors))

    def test_an_empty_section_must_carry_its_empty_state_line(self):
        path = write(GOOD.replace(COINED, ""))
        self.addCleanup(path.unlink)
        result = summary_gate.lint_file(path)
        self.assertTrue(any("this document coins no terms" in e for e in result.errors))

    def test_the_empty_state_line_itself_passes(self):
        path = write(GOOD.replace(
            COINED, summary_gate.EMPTY_STATE["Terms coined here"] + "\n"
        ))
        self.addCleanup(path.unlink)
        self.assertEqual([], summary_gate.lint_file(path).errors)


class ShowTheMathematicsTests(unittest.TestCase):
    """The failure the first real summary actually produced.

    It passed every check in this file at 104 body lines against a cap of 300
    and 2 pages against a cap of 10, and a person still could not see a single
    thing that had been proved: thirteen established results, each a noun
    phrase and a path. The cap was never the constraint — the rule was, and it
    said "one line each, plus the path to the proof".
    """

    def test_the_problem_itself_must_be_stated(self):
        """It also never said what the problem was. The title carried it and
        nothing else did, which is the one thing a document for a person cannot
        assume its reader already knows."""
        path = write(GOOD.replace("\\section{The statement}", "\\section{Background}"))
        self.addCleanup(path.unlink)
        errors = " ".join(summary_gate.lint_file(path).errors)
        self.assertIn("The statement", errors)

    def test_the_statement_section_comes_first(self):
        body = GOOD.replace("\\section{The statement}", "\\section{ZZ}").replace(
            "\\section{Where this stands}", "\\section{The statement}", 1
        ).replace("\\section{ZZ}", "\\section{Where this stands}", 1)
        path = write(body)
        self.addCleanup(path.unlink)
        self.assertTrue(
            any("out of order" in e for e in summary_gate.lint_file(path).errors)
        )

    def test_a_name_and_a_path_is_not_an_established_result(self):
        """Verbatim shape from the real run: thirteen of these, no mathematics."""
        path = write(GOOD.replace(
            ESTABLISHED_ITEM,
            "  \\item The polynomial factorisation for all eight forms:\n"
            "        \\path{lemmas/identity/}\n",
        ))
        self.addCleanup(path.unlink)
        errors = " ".join(summary_gate.lint_file(path).errors)
        self.assertIn("\\textbf{Statement.}", errors)
        self.assertIn("citation, not", errors)

    def test_a_statement_without_a_sketch_is_refused(self):
        path = write(GOOD.replace(
            "        \\textbf{Sketch.} Both maps are built from the fold move, which acts two\n"
            "        generators at a time; injectivity is the rank computation on the\n"
            "        resulting blocks.\n",
            "",
        ))
        self.addCleanup(path.unlink)
        errors = " ".join(summary_gate.lint_file(path).errors)
        self.assertIn("\\textbf{Sketch.}", errors)

    def test_a_result_without_a_path_is_refused(self):
        path = write(GOOD.replace(
            "        \\path{lemmas/cloning_fold_restart_2/cf2_expansion_factorization/}\n",
            "",
        ))
        self.addCleanup(path.unlink)
        errors = " ".join(summary_gate.lint_file(path).errors)
        self.assertIn("full proof", errors)

    def test_every_result_is_checked_not_only_the_first(self):
        path = write(GOOD.replace(
            ESTABLISHED_ITEM,
            ESTABLISHED_ITEM + "  \\item A second thing: \\path{lemmas/second/}\n",
        ))
        self.addCleanup(path.unlink)
        result = summary_gate.lint_file(path)
        self.assertEqual(2, result.metrics["established_results"])
        self.assertTrue(any("Statement." in e for e in result.errors))

    def test_thirteen_broken_results_are_not_thirteen_errors(self):
        """P45's defect, reintroduced by the next gate to be added. The run that
        motivated this check had thirteen malformed results and got thirteen
        identical paragraphs. When every item is wrong the shape is wrong, and
        that is one finding."""
        citation = "  \\item A thing: \\path{lemmas/thing/}\n"
        path = write(GOOD.replace(ESTABLISHED_ITEM, citation * 13))
        self.addCleanup(path.unlink)
        result = summary_gate.lint_file(path)
        self.assertEqual(13, result.metrics["established_malformed"])
        per_item = [e for e in result.errors if "is missing" in e]
        self.assertEqual(summary_gate.CASCADE_LIMIT, len(per_item))
        self.assertTrue(any("10 further results" in e for e in result.errors))

    def test_a_short_sketch_warns_and_does_not_block(self):
        """A finite range checked by machine has a four-word sketch and is
        complete. A length minimum there is a lint the run routes around."""
        path = write(GOOD.replace(
            "\\textbf{Sketch.} Both maps are built from the fold move, which acts two\n"
            "        generators at a time; injectivity is the rank computation on the\n"
            "        resulting blocks.",
            "\\textbf{Sketch.} Exhaustive machine computation.",
        ))
        self.addCleanup(path.unlink)
        result = summary_gate.lint_file(path)
        self.assertEqual([], result.errors, result.errors)
        self.assertTrue(any("under 10 words" in w for w in result.warnings))

    def test_the_empty_state_still_exempts_the_section(self):
        path = write(GOOD.replace(
            "\\begin{itemize}\n" + ESTABLISHED_ITEM + "\\end{itemize}",
            summary_gate.EMPTY_STATE["What is established"],
        ))
        self.addCleanup(path.unlink)
        self.assertEqual([], summary_gate.lint_file(path).errors)

    def test_the_caps_were_never_the_constraint(self):
        """The real summary passed at 104/300 lines and 2/10 pages. Recorded as
        a test so that a later round does not 'fix' this by raising a cap."""
        result = summary_gate.lint_file(write(GOOD))
        self.assertLess(result.metrics["lines"], summary_gate.MAX_LINES / 2)


class JargonTests(unittest.TestCase):
    def test_unambiguous_harness_nouns_are_errors(self):
        path = write(GOOD.replace(
            "Every route now passes through it.",
            "The Sketcher sent NEEDS_REVISION on the review packet.",
        ))
        self.addCleanup(path.unlink)
        result = summary_gate.lint_file(path)
        joined = " ".join(result.errors)
        for token in ("Sketcher", "NEEDS_REVISION", "review packet"):
            self.assertIn(token, joined)

    def test_role_names_that_are_also_mathematics_do_not_block(self):
        """`Verifier` is standard in interactive proofs; `Regulator` is the
        regulator of a number field. Refusing a summary about class numbers for
        saying "Regulator" is the false-positive machine this file warns about,
        and the epilogue tells the run not to waive -- so the only way out would
        be to rename the mathematics."""
        path = write(GOOD.replace(
            "Every route now passes through it.",
            "The Regulator of the field bounds the Verifier's soundness error.",
        ))
        self.addCleanup(path.unlink)
        result = summary_gate.lint_file(path)
        self.assertEqual([], result.errors)

    def test_gate_as_a_mathematical_noun_is_not_a_subcommand(self):
        """"gate set", "gate complexity", "gate teleportation"."""
        path = write(GOOD.replace(
            "Every route now passes through it.",
            "The gate set is universal and the gate complexity is linear.",
        ))
        self.addCleanup(path.unlink)
        self.assertEqual([], summary_gate.lint_file(path).errors)

    def test_a_real_gate_subcommand_is_still_caught(self):
        path = write(GOOD.replace(
            "Every route now passes through it.", "Then run gate summary on it.",
        ))
        self.addCleanup(path.unlink)
        self.assertTrue(
            any("gate summary" in e for e in summary_gate.lint_file(path).errors)
        )

    def test_words_that_are_also_mathematics_warn_and_do_not_block(self):
        """`residual`, `row`, `owner`, `accepted` are ordinary mathematics.

        Blacklisting them builds a false-positive machine. The corpus separates
        on density: the outlier is 0.49/line against a median of 0.04.
        """
        stuffed = "\n".join(
            "The accepted owner row records the slot audit." for _ in range(12)
        )
        path = write(GOOD.replace("Every route now passes through it.", stuffed))
        self.addCleanup(path.unlink)
        result = summary_gate.lint_file(path)
        self.assertEqual([], result.errors)
        self.assertTrue(any("bookkeeping-word density" in w for w in result.warnings))

    def test_one_ordinary_use_of_an_ambiguous_word_is_silent(self):
        path = write(GOOD.replace(
            "Every route now passes through it.",
            "The residual term is bounded on each row of the matrix.",
        ))
        self.addCleanup(path.unlink)
        result = summary_gate.lint_file(path)
        self.assertEqual([], result.errors)
        self.assertEqual([], result.warnings)


class InaccurateProgressTests(unittest.TestCase):
    def test_a_numeric_distance_estimate_fails(self):
        path = write(GOOD.replace(
            "Every route now passes through it.", "We are roughly 80% done."
        ))
        self.addCleanup(path.unlink)
        result = summary_gate.lint_file(path)
        self.assertTrue(any("qualitative" in e for e in result.errors))

    def test_counting_remaining_runs_fails(self):
        path = write(GOOD.replace(
            "Every route now passes through it.", "Two more runs should close it."
        ))
        self.addCleanup(path.unlink)
        result = summary_gate.lint_file(path)
        self.assertTrue(any("qualitative" in e for e in result.errors))

    def test_process_telemetry_fails(self):
        path = write(GOOD.replace(
            "Every route now passes through it.",
            "The run took 22 hours of wall-clock at concurrency 3.",
        ))
        self.addCleanup(path.unlink)
        result = summary_gate.lint_file(path)
        self.assertTrue(any("process telemetry" in e for e in result.errors))

    def test_a_pasted_verbatim_block_fails(self):
        """The actual shape of the failure: an internal artifact pasted whole.

        In a document for a person a verbatim environment is refused outright
        rather than judged on its contents -- the summary's whole job is to
        restate, and the note beside it is where anything unrestatable belongs.
        """
        path = write(GOOD.replace(
            "Every route now passes through it.",
            "\\begin{verbatim}\nSetup\nStatement. ...\n\\end{verbatim}",
        ))
        self.addCleanup(path.unlink)
        result = summary_gate.lint_file(path)
        self.assertTrue(any("summarises nothing" in e for e in result.errors))

    def test_the_other_verbatim_environments_are_caught_too(self):
        """`verbatim` was the only one named, and it is not the only one that
        typesets a paste."""
        for environment in ("lstlisting", "minted", "alltt"):
            with self.subTest(environment=environment):
                path = write(GOOD.replace(
                    "Every route now passes through it.",
                    f"\\begin{{{environment}}}\nSetup\n\\end{{{environment}}}",
                ))
                self.addCleanup(path.unlink)
                result = summary_gate.lint_file(path)
                self.assertTrue(
                    any("summarises nothing" in e for e in result.errors), environment
                )


class NoFalsePositivesTests(unittest.TestCase):
    """A lint that refuses good documents is worse than no lint."""

    def test_a_proof_path_is_not_harness_vocabulary(self):
        """The spec REQUIRES a path per established result. Scanning it for
        `restart_1` made the gate refuse the very thing it asks for -- which is
        what the first draft of this gate did to the first document tested."""
        path = write(GOOD)
        self.addCleanup(path.unlink)
        self.assertEqual([], summary_gate.lint_file(path).errors)

    def test_a_path_named_in_prose_without_markup_is_still_caught(self):
        path = write(GOOD.replace(
            "Every route now passes through it.",
            "See STATUS.md for the rest.",
        ))
        self.addCleanup(path.unlink)
        result = summary_gate.lint_file(path)
        self.assertTrue(any("STATUS.md" in e for e in result.errors))

    def test_generator_in_a_group_theoretic_sense_is_not_a_role_name(self):
        """`generator` is a role here and one of the commonest nouns in the
        subject. The first version of this gate blacklisted it outright, which
        would have refused "each generator of the group" -- the exact shape of
        lint a run learns to route around. It lives on the density list now."""
        path = write(GOOD.replace(
            "Every route now passes through it.",
            "Each generator of the group satisfies the relation.",
        ))
        self.addCleanup(path.unlink)
        result = summary_gate.lint_file(path)
        self.assertEqual([], result.errors)
        self.assertEqual([], result.warnings)

    def test_capitalised_role_names_are_still_errors(self):
        path = write(GOOD.replace(
            "Every route now passes through it.",
            "The Orchestrator asked the Sketcher for a split.",
        ))
        self.addCleanup(path.unlink)
        result = summary_gate.lint_file(path)
        joined = " ".join(result.errors)
        self.assertIn("Orchestrator", joined)
        self.assertIn("Sketcher", joined)

    def test_many_uses_of_generator_as_scheduling_still_warn(self):
        stuffed = "\n".join(
            "The generator produced a record for the accepted row." for _ in range(12)
        )
        path = write(GOOD.replace("Every route now passes through it.", stuffed))
        self.addCleanup(path.unlink)
        result = summary_gate.lint_file(path)
        self.assertEqual([], result.errors)
        self.assertTrue(any("bookkeeping-word density" in w for w in result.warnings))

    def test_mathematics_in_the_preamble_is_not_scanned_as_prose(self):
        """A macro definition is not a sentence, and a `\\usepackage` line is
        not vocabulary. Scanning the preamble made both look like both."""
        noisy = PREAMBLE.replace(
            "\\date{}", "\\date{}\n\\newcommand{\\statusmd}{STATUS.md}"
        )
        path = write(GOOD.replace(PREAMBLE, noisy))
        self.addCleanup(path.unlink)
        self.assertEqual([], summary_gate.lint_file(path).errors)


class WorkedExampleTests(unittest.TestCase):
    """The documented example must pass the gate that documents it.

    It is a second copy of the spec, and a worked example that its own gate
    would refuse is worse than no example -- a run copies the shape, is refused,
    and learns that the gate is noise.
    """

    EXAMPLE = (
        REPO_ROOT
        / ".agents/skills/article-writing/references/progress-summary-example.md"
    )

    def latex_block(self):
        import re

        match = re.search(r"```latex\n(.*?)\n```", self.EXAMPLE.read_text("utf-8"), re.S)
        self.assertIsNotNone(match, "no ```latex block in the worked example")
        return match.group(1) + "\n"

    def test_the_documented_example_passes(self):
        path = write(self.latex_block())
        self.addCleanup(path.unlink)
        result = summary_gate.lint_file(path)
        self.assertEqual([], result.errors, result.errors)
        self.assertEqual([], result.warnings, result.warnings)

    def test_the_numbers_the_example_quotes_about_itself_are_true(self):
        """It claims 49 body lines and a blocker at body line 9. Those are
        measurements, and a document that misreports its own is the exact
        failure this gate exists to catch."""
        result = summary_gate.lint_file(write(self.latex_block()))
        prose = self.EXAMPLE.read_text("utf-8")
        self.assertIn(f"{result.metrics['lines']} body lines", prose)
        self.assertIn(f"body line {result.metrics['blocker_line']}", prose)

    def test_the_example_uses_every_required_section(self):
        sections = [
            title for title, _, _ in summary_gate._sections(
                summary_gate.document_body(self.latex_block())[0]
            )
        ]
        self.assertEqual(list(summary_gate.REQUIRED_SECTIONS), sections)


class AdversarialTests(unittest.TestCase):
    """Two documents an adversarial review built to break this gate.

    Both worked. They are fixtures now, because the next change to the
    vocabulary or the depth rule will be tempted by exactly the same shortcuts.
    """

    BAD = PREAMBLE + r"""
\section{The statement}

Whether the cloning overgroup embeds. See the note.

\section{Where this stands}

\texttt{The Orchestrator dispatched the ce-hunter and the kb-manager against workspace/foo; the review packet came back NEEDS_REVISION and the obligation ledger in STATUS.md is still open.}

\section{What is blocked}

\texttt{the ce-hunter is blocked on the obligation ledger in workspace/x/STATUS.md, which the Orchestrator never dispatched a Verifier against}

\section{What is established}

\begin{itemize}
  \item \textbf{Statement.} Nothing.
        \textbf{Sketch.} Nothing.
        \path{nothing/at-all}
\end{itemize}

\section{What was ruled out}

\emph{(no route has been ruled out; absence here does not mean the route set is small)}

\section{What to do next}

\emph{(no next step is identified --- that is itself the finding)}

\section{Terms coined here}

\emph{(this document coins no terms)}

\end{document}
"""

    GOOD_AND_SHORT = r"""\documentclass{article}
\begin{document}
\section{The statement}
Every Besicovitch set in $\mathbb{R}^3$ has Hausdorff dimension $3$.
\section{Where this stands}

The original statement is partially proved. The maximal-operator bound now
holds for every Besicovitch set of Minkowski dimension at least $5/2$. The
remaining gap is the range between $5/2$ and $3$. The argument used is Wolff's
hairbrush, not the polynomial method. Nothing here has been checked against
the published literature yet.

\section{What is blocked}
The uniform constant in Lemma 3.
\section{What is established}
\begin{itemize}
  \item \textbf{Statement.} The maximal operator is bounded on $L^3$ for every
        Besicovitch set of Minkowski dimension at least $5/2$.
        \textbf{Sketch.} Wolff's hairbrush argument, with the bush replaced by
        a hairbrush at each scale.
        \path{lemmas/kakeya_hairbrush/bound/}
\end{itemize}
\section{What was ruled out}
The interpolation route.
\section{What to do next}
Try the bilinear estimate.
\section{Terms coined here}
\emph{(this document coins no terms)}
\end{document}
"""

    def lint(self, text):
        path = write(text)
        self.addCleanup(path.unlink)
        return summary_gate.lint_file(path)

    def test_texttt_does_not_hide_harness_vocabulary(self):
        """`PATH_SPAN` erased any marked-up run containing a slash, so wrapping
        a paragraph in `\\texttt{}` and putting one `/` in it hid every term in
        it -- a bypass costing one character."""
        result = self.lint(self.BAD)
        joined = " ".join(result.errors)
        for token in ("Orchestrator", "ce-hunter", "review packet", "NEEDS_REVISION"):
            self.assertIn(token, joined)

    def test_a_real_path_is_still_exempt(self):
        """The rule the bypass was hiding behind is real: an established result
        must cite the path its proof lives at."""
        result = self.lint(GOOD)
        self.assertEqual([], result.errors)

    def test_a_short_correct_summary_is_not_refused_for_its_shape(self):
        """A percentage-based depth rule pulled against the line cap: the only
        way to lower the ratio was to pad AFTER the blocker. This document is
        20 lines, has a full-length lead, and was refused at 55%."""
        result = self.lint(self.GOOD_AND_SHORT)
        self.assertEqual([], result.errors, result.errors)

    def test_a_verbatim_block_cannot_supply_the_required_structure(self):
        """Otherwise the paste check and the structure check read the same lines
        for opposite purposes and certify each other."""
        text = (
            PREAMBLE
            + "\\begin{verbatim}\n"
            + "\n".join(f"\\section{{{name}}}" for name in summary_gate.REQUIRED_SECTIONS)
            + "\n\\end{verbatim}\n\\end{document}\n"
        )
        result = self.lint(text)
        self.assertTrue(
            any("missing required section" in e for e in result.errors), result.errors
        )

    def test_lowercase_role_names_are_caught(self):
        result = self.lint(GOOD.replace(
            "Every route now passes through it.",
            "the orchestrator asked the sketcher for a split.",
        ))
        joined = " ".join(result.errors)
        self.assertIn("orchestrator", joined)
        self.assertIn("sketcher", joined)

    def test_mathematical_abbreviations_do_not_inflate_the_sentence_count(self):
        lead = (
            "The statement is open. We reduced it to Lemma 3.1. The remaining "
            "obstruction is the constant in Prop. 2, i.e. the scale dependence. "
            "Wolff's hairbrush applies for dim > 5/2, e.g. the Besicovitch case. "
            "Nothing was checked against Ref. [4]."
        )
        self.assertLessEqual(len(summary_gate._sentences(lead)), 5)


if __name__ == "__main__":
    unittest.main()
