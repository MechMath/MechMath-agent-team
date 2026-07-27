---
name: verification
description: "Cross-verification tools for independently scoring proof quality via Gemini and GPT"
---

# Verification Tools

Independent verification tools and checklists for proof quality. External scoring scripts are in `cli_tools/`.

> **Verifier responsibility** — Verifiers use these tools and checklists when judging a proof. Generators must not use verification tools to approve their own work.

## Available Tools

| Tool | Purpose | When to use |
|------|---------|-------------|
| **gemini-verify** | Score a proof using Gemini via OpenRouter or direct Gemini API | When `OPENROUTER_API_KEY` or `GEMINI_API_KEY` is set |
| **gpt-verify** | Score a proof using GPT-5.5 Pro via OpenRouter or direct OpenAI API | When `OPENROUTER_API_KEY` or `OPENAI_API_KEY` is set |

> **No API key?** The Verifier skips external cross-verification and performs the same 0/0.5/1 rubric internally.

## Single-Packet Verification

NL-Prover uses one full Verifier review packet per mathematical check.
There is no structural pre-check. The Verifier checks target preservation,
problem reading, dependency coverage, source-theorem and definition audits,
load-bearing obligations, adversarial risks, and step-by-step mathematical
correctness in the same pass.

A Verifier writes:

```text
report_v<N>.md
review_packet_v<N>.md
verdict.md
```

Run the packet shape lint before using a passing packet for merge,
refined-proof adoption, plan adoption, or obstruction acceptance:

```bash
uv run python cli_tools/gate.py review-packet <review_packet.md> --mode auto
```

The lint is not mathematical verification. It only checks that the packet is
restartable and that accepting next actions are compatible with the verdict.

## Hypotheses and Preconditions Checklist

Every Verifier report should include a dedicated hypotheses/preconditions audit.
If the statement, decomposition, or query outputs include a Verifier risk
checklist from analysis preflight, the report should also include an
`Analysis/Preflight Risk Audit`. For each checklist item, mark
`SATISFIED`, `VIOLATED`, or `NOT APPLICABLE`, and explain the decision. Treat
analysis pages as warning signals, not as proof facts.

1. **Statement preservation**
   - Does the proof prove the exact lemma statement?
   - Did it change quantifiers, domains, types, regularity, finiteness, or assumptions?

2. **Dependency lemma preconditions**
   - For each dependency lemma used, what are its hypotheses?
   - Are those hypotheses satisfied in the current lemma's context?
   - Is the dependency conclusion used exactly as stated, without strengthening?

3. **Theorem preconditions**
   - For each theorem or standard result invoked, what are its required hypotheses?
   - Where are those hypotheses verified before use?
   - Are any theorem assumptions silently imported?

4. **Added or strengthened hypotheses**
   - Did the proof introduce nonzero, finite, Noetherian, smooth, compact, generic, independent, algebraically closed, characteristic zero, bounded, regular, "without loss of generality", or similar assumptions?
   - If yes, are they derived from existing hypotheses or dependency lemmas?

5. **Undischarged assumptions**
   - List every assumption used but not proved, not stated, and not supplied by dependencies.

Verdict guidance:
- Added or strengthened hypotheses that are not derivable from the statement or dependencies force `FAIL`.
- Misusing a dependency lemma by ignoring its hypotheses or strengthening its conclusion forces `FAIL`.
- Missing theorem preconditions that are local and plausibly fixable usually force `NEEDS_REVISION`.
- Missing theorem preconditions that support the core argument force `FAIL`.

## Refinement Verification Modes

The same hypothesis discipline applies to refinement candidates. The Verifier
approves or rejects refinement; the Orchestrator only routes files and follows
the verdict.

### Plan Logic / Refinement

Use this after Sketcher writes `sketch/decomposition.md`, before any Generator
starts. Use it again when checking a candidate `sketch/decomposition_refined.md`.
This is a gate for the current route, not a fixed pipeline requirement: if the
Regulator or Orchestrator selects a different route owner, verify the new
canonical decomposition before generation.

Checklist:
- Does the DAG still target the exact original theorem?
- Do the terminal lemmas logically entail the main theorem once proved?
- Is there a clear final assembly path from terminal lemmas to the final question?
- Is any bridge lemma missing?
- Are all dependencies acyclic and sufficient for the final theorem?
- Are removed, merged, or bypassed lemmas justified by the new route?
- Are dependency lemma hypotheses listed and plausibly supplied by parent nodes?
- Are theorem preconditions listed instead of silently imported?
- Are added or strengthened hypotheses absent?
- For refined candidates, is the proposed DAG meaningfully simpler, clearer, or less risky?

Reject with `FAIL` if the candidate changes the theorem, adds or strengthens
hypotheses, uses a circular DAG, cannot derive the final theorem from terminal
lemmas, lacks necessary bridge lemmas, or relies on missing core preconditions.

### Global Proof Refinement

Use this when checking a candidate `refinement/proof_refined.tex`.

Checklist:
- Does the refined proof prove the exact original theorem?
- If the DAG changed, is the new DAG sufficient and acyclic?
- Are deleted or bypassed lemmas truly unnecessary?
- Are dependency and theorem preconditions verified before use?
- Are no hypotheses added, strengthened, or hidden?
- Is the refined proof a real simplification rather than a shorter but less
  justified argument?

Pass the refined proof only if it is both correct and materially cleaner than
the already accepted proof. Otherwise keep the original proof.

For full parameters and examples, read the corresponding `reference-<tool>.md` file in this directory.
