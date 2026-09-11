import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "cli_tools"))
from _gate import proof_attempt as proof_attempt_lint


def proof(
    *,
    body="We prove the lemma by direct implication.",
    load_status="resolved",
    remaining="NONE",
    added="NONE",
    theorem_preconditions="NONE",
    definitions="NONE",
    source_theorem_obligations="NONE",
    conclusion="Therefore the statement of the lemma follows.",
):
    return f"""# Proof of lem:test

## Setup
**Statement**: sample lemma.
**Definitions**: all symbols are as in the statement.

## Proof
{body}

## Hypotheses and Preconditions Audit

### Lemma Statement Hypotheses
The hypotheses are copied from the statement.

### Dependency Lemmas Used
NONE

### Theorem Preconditions Used
{theorem_preconditions}

### Definitions and Notation Used
{definitions}

### Problem Reading and Normalization
- Normalized reading used: NONE
- Source of reading: N/A
- Material ambiguity remains: NO
- Boundary conventions audited: N/A

### Proof Obligations
- Construction/existence obligations supplied in this proof: NONE
- Source theorem obligations invoked: {source_theorem_obligations}
- Remaining obligations: {remaining}

### Load-Bearing Obligation Ledger
| Obligation | Type | Where supplied in this proof | Preconditions checked | Status |
|------------|------|------------------------------|-----------------------|--------|
| main implication | final bridge | proof paragraph 1 | YES | {load_status} |

### Added or Strengthened Hypotheses
{added}

**Conclusion**: {conclusion}
"""


def status(*, state="done", obligations="NONE", load_status="resolved", classification="complete proof"):
    return f"""# Generator Status: lem:test

## Status: {state}

## Attempts: 1 / 3
## Current version: proof_v1.md

## Proof Obligations
{obligations}

## Problem Reading and Normalization
- Normalized reading used: NONE
- Material ambiguity remains: NO
- Boundary conventions audited: N/A

## Completion Classification
{classification}

## Load-Bearing Obligation Ledger
| Obligation | Type | Current status | Requested next action |
|------------|------|----------------|-----------------------|
| main implication | final bridge | {load_status} | none |

## Notes
NONE
"""


class ProofAttemptLintTests(unittest.TestCase):
    def test_accepts_complete_done_attempt(self):
        result, signals = proof_attempt_lint.lint_proof_text(proof())
        proof_attempt_lint.lint_status_text(status(), result=result, signals=signals)
        self.assertEqual([], result.errors)

    def test_rejects_gap_only_conclusion(self):
        result, signals = proof_attempt_lint.lint_proof_text(
            proof(conclusion="The definition is missing, so gap found.")
        )
        proof_attempt_lint.lint_status_text(status(), result=result, signals=signals)
        self.assertTrue(
            any("route-failure" in error for error in result.errors),
            result.errors,
        )

    def test_rejects_done_status_with_open_ledger(self):
        result, signals = proof_attempt_lint.lint_proof_text(
            proof(load_status="open")
        )
        proof_attempt_lint.lint_status_text(
            status(load_status="open"), result=result, signals=signals
        )
        self.assertTrue(
            any("done status" in error and "unresolved" in error for error in result.errors),
            result.errors,
        )

    def test_allows_stuck_status_with_restart_detail(self):
        result, signals = proof_attempt_lint.lint_proof_text(
            proof(load_status="open", remaining="source theorem exact statement")
        )
        proof_attempt_lint.lint_status_text(
            status(
                state="stuck",
                obligations="source theorem exact statement is needed",
                load_status="open",
                classification="restartable incomplete",
            ),
            result=result,
            signals=signals,
        )
        self.assertEqual([], result.errors)

    def test_rejects_added_hypothesis_when_done(self):
        result, signals = proof_attempt_lint.lint_proof_text(
            proof(added="Assume compactness; required action: resketch.")
        )
        proof_attempt_lint.lint_status_text(status(), result=result, signals=signals)
        self.assertTrue(
            any("added or strengthened hypotheses" in error for error in result.errors),
            result.errors,
        )

    def test_rejects_missing_audit_subsection(self):
        text = proof().replace("### Theorem Preconditions Used\nNONE\n\n", "")
        result, _ = proof_attempt_lint.lint_proof_text(text)
        self.assertTrue(
            any("Theorem Preconditions Used" in error for error in result.errors),
            result.errors,
        )

    def test_rejects_theorem_like_citation_without_precondition_audit(self):
        result, signals = proof_attempt_lint.lint_proof_text(
            proof(body="By the standard estimate, the required bound follows.")
        )
        proof_attempt_lint.lint_status_text(status(), result=result, signals=signals)
        self.assertTrue(
            any("theorem-like citation" in error for error in result.errors),
            result.errors,
        )

    def test_accepts_theorem_like_citation_with_precondition_audit(self):
        result, signals = proof_attempt_lint.lint_proof_text(
            proof(
                body="By the standard estimate, the required bound follows.",
                theorem_preconditions=(
                    "- Theorem: local estimate\n"
                    "- Exact usable statement: audited statement\n"
                    "- Required hypotheses: copied from the lemma\n"
                    "- Verified at: proof paragraph 1\n"
                    "- Status: SATISFIED"
                ),
            )
        )
        proof_attempt_lint.lint_status_text(status(), result=result, signals=signals)
        self.assertEqual([], result.errors)

    def test_rejects_target_criterion_used_as_definition(self):
        result, signals = proof_attempt_lint.lint_proof_text(
            proof(
                body=(
                    "We define the admissible class as the objects satisfying "
                    "the desired criterion. By definition, the characterization follows."
                )
            )
        )
        proof_attempt_lint.lint_status_text(status(), result=result, signals=signals)
        self.assertTrue(
            any("theorem-as-definition" in error for error in result.errors),
            result.errors,
        )

    def test_accepts_tautological_definition_when_independent_source_is_audited(self):
        result, signals = proof_attempt_lint.lint_proof_text(
            proof(
                body=(
                    "The cited source defines the class as the objects satisfying "
                    "this condition. By definition, the characterization follows."
                ),
                definitions=(
                    "The accepted definition source is dependency lem:def; "
                    "the proof does not introduce this definition."
                ),
            )
        )
        proof_attempt_lint.lint_status_text(status(), result=result, signals=signals)
        self.assertEqual([], result.errors)

    def test_the_no_proof_weight_disclaimer_is_not_a_route_failure(self):
        """Invariant 16 requires discovery artifacts to say their output
        "carries no proof weight". The route-failure regex matched that
        sentence, so the mandated wording tripped a blocking check."""
        patterns = proof_attempt_lint.ROUTE_FAILURE_PATTERNS
        self.assertFalse(
            any(p.search("This computation carries no proof weight.") for p in patterns)
        )
        self.assertTrue(
            any(p.search("There is no proof of the covering direction.") for p in patterns)
        )

class VerifiedBeforeHandoffTests(unittest.TestCase):
    """In certification an artifact arrives with a verdict or it does not arrive.

    The check itself is unchanged and there is still exactly one per round; what
    moves is who starts it.
    """

    def make_lemma(self, tmp, *, body, packet=True, version=3):
        root = Path(tmp) / "lemmas" / "branch" / "leaf"
        (root / "generator").mkdir(parents=True)
        proof = root / "generator" / f"proof_v{version}.md"
        proof.write_text(body, encoding="utf-8")
        if packet:
            (root / "verifier").mkdir(parents=True)
            (root / "verifier" / f"review_packet_v{version}.md").write_text(
                "# Review Packet\n", encoding="utf-8"
            )
        return proof

    def test_certification_attempt_without_a_packet_is_turned_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            proof = self.make_lemma(tmp, body="# Proof\n\nSomething.\n", packet=False)
            result = proof_attempt_lint.lint_files(proof)
            self.assertTrue(any("no verifier packet" in e for e in result.errors))

    def test_the_message_names_both_routes(self):
        with tempfile.TemporaryDirectory() as tmp:
            proof = self.make_lemma(tmp, body="# Proof\n", packet=False)
            errors = " ".join(proof_attempt_lint.lint_files(proof).errors)
            self.assertIn("verify.py", errors)
            self.assertIn("Verifier subagent", errors)

    def test_a_packet_for_this_round_satisfies_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            proof = self.make_lemma(tmp, body="# Proof\n", packet=True)
            result = proof_attempt_lint.lint_files(proof)
            self.assertFalse(any("no verifier packet" in e for e in result.errors))

    def test_a_packet_from_an_earlier_round_does_not(self):
        """A prior PASS applies only to the exact artifact it checked."""
        with tempfile.TemporaryDirectory() as tmp:
            proof = self.make_lemma(tmp, body="# Proof\n", packet=False, version=4)
            (proof.parent.parent / "verifier").mkdir(parents=True)
            (proof.parent.parent / "verifier" / "review_packet_v3.md").write_text(
                "# Review Packet\n", encoding="utf-8"
            )
            result = proof_attempt_lint.lint_files(proof)
            self.assertTrue(any("review_packet_v4.md" in e for e in result.errors))

    def test_a_discovery_artifact_is_exempt(self):
        """Discovery output discharges no obligation; a verdict on it would be a
        category error, not a favour."""
        with tempfile.TemporaryDirectory() as tmp:
            proof = self.make_lemma(
                tmp,
                body="**Mode: DISCOVERY.** Conjectural evidence.\n\n# Sketch\n",
                packet=False,
            )
            result = proof_attempt_lint.lint_files(proof)
            self.assertFalse(any("no verifier packet" in e for e in result.errors))

    def test_a_file_that_is_not_a_generator_attempt_is_left_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            other = Path(tmp) / "routes" / "brainstorm_1.md"
            other.parent.mkdir(parents=True)
            other.write_text("# Ideas\n", encoding="utf-8")
            result = proof_attempt_lint.lint_files(other)
            self.assertFalse(any("no verifier packet" in e for e in result.errors))

    def test_it_can_be_switched_off_for_a_mid_write_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            proof = self.make_lemma(tmp, body="# Proof\n", packet=False)
            result = proof_attempt_lint.lint_files(proof, require_verdict=False)
            self.assertFalse(any("no verifier packet" in e for e in result.errors))


if __name__ == "__main__":
    unittest.main()
