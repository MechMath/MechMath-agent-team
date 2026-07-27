import importlib.util
from pathlib import Path
import sys
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


if __name__ == "__main__":
    unittest.main()
