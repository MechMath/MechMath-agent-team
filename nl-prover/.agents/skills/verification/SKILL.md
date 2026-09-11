---
name: verification
description: "Cross-verification tools for independently scoring proof quality via Gemini and GPT"
---

# Verification Tools

Independent verification tools and checklists for proof quality. External scoring scripts are in `cli_tools/`.

> **Verifier responsibility** — Verifiers use these tools and checklists when
> judging a proof. **Generators must not use verification tools to approve their
> own work**, and no producer's own judgement is a verdict.
>
> Starting a check is not approving one. A Generator or Sketcher may run
> `cli_tools/verify.py`, which assembles a dispatch from paths and hands the
> artifact to a **fresh, cold-start** Verifier that the producer cannot see into
> and whose verdict it cannot edit — the packet lands in the Verifier-owned
> directory, which the producer still may not write. The verdict is the
> Verifier's, exactly as when the Orchestrator dispatches one; what changed is
> who picks up the phone. What remains forbidden is a producer scoring its own
> proof, arguing with the packet in the proof file, or treating its own
> confidence as an outcome.

## Available Tools

| Tool | Purpose | When to use |
|------|---------|-------------|
| **gemini-verify** | Score a proof using Gemini via OpenRouter or direct Gemini API | When `OPENROUTER_API_KEY` or `GEMINI_API_KEY` is set |
| **gpt-verify** | Score a proof using GPT-5.5 Pro via OpenRouter or direct OpenAI API | When `OPENROUTER_API_KEY` or `OPENAI_API_KEY` is set |
| **`cli_tools/verify.py`** | Assemble one verification dispatch from paths and enums, and either print it for a Verifier subagent or run it against a cold-start verifier | Every ordinary per-artifact check in `certification`. Never in `discovery` — discovery output discharges no obligation, so a verdict on it is a category error |

> **No API key?** The Verifier skips external cross-verification and performs the same 0/0.5/1 rubric internally.

### `verify.py dispatch`

```bash
uv run python cli_tools/verify.py dispatch <lemmas/L3/proof_v2.md> \
    --statement <lemmas/L3/statement.md> \
    --problem <problem.md> \
    --output-dir <lemmas/L3/verifier> \
    --mode certification \
    --verification-mode lemma \
    --version 2 \
    --dependency <lemmas/L1/statement.md>:PASS \
    --dependency <lemmas/L2/statement.md>:NEEDS_REVISION \
    --context <queries/source-theorem-package.md> \
    --budget-minutes 30 --stop-when packet-written \
    --workspace <problem_workspace>
```

`--verification-mode` is one of `lemma`, `target_obstruction`, `plan_logic`,
`global_refinement`, and names the single mode file the Verifier reads — reading
all of them costs about 9 KB a dispatch and only one can apply. `--dependency`
takes `PATH[:PASS|NEEDS_REVISION|none]`: the state, never the reasoning behind
it. `--stop-when` is `packet-written`, `blocking-issue-found`, or
`budget-exhausted`.

**Independence here is structural, not a matter of discipline.** Across 87
verification dispatches, 100% told the Verifier it was a fresh, stateless,
independent referee and 84% supplied, in the same prompt, the thing independence
excludes — 57% the Generator's own account of its work, 45% what earlier
verifiers concluded. A contract stated and violated five times in six is not a
wording problem, so every parameter above is a path or an enum: there is no
argument that can carry a prior verdict, a confidence, a defence of the artifact,
or "the Generator reports that". Not forbidden — there is nowhere to put it. A
concern that still matters travels inside the artifact, as a question about the
mathematics ("does Step 14 need n >= 3?"), never as a verdict about a document.

**Both routes are the same text.** `_verify/dispatch.py` renders it once. With
`--run` it executes against the cold-start verifier named in
`NLPROVER_VERIFIER_CMD` (e.g. `claude -p --permission-mode acceptEdits`, or
`codex exec`), fed on stdin; without `--run` it prints exactly what the
Orchestrator hands to a Verifier subagent. Equivalence by construction rather
than by audit. `--run` with no `NLPROVER_VERIFIER_CMD` refuses and says so — a
verification that did not happen must not look like one that passed. Pass
`--workspace` either way so the dispatch is recorded in `logs/dispatch.jsonl`
with the same `prompt_shape` the hook computes, which is what lets
`gate.py speed` put a number on the claim.

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
verdict_v<N>.md
```

**Write the versioned name.** Both forms exist in the corpus — 352 `verdict.md`
against 118 `verdict_v<N>.md` — and `gate dag` reads both, preferring the
versioned one (`_gate/dag.py`, `VERDICT_VERSION`). `cli_tools/verify.py` emits
the versioned name. The unversioned name is not wrong, it is lossy: a
re-verification overwrites the verdict it was re-checking, and invariant 15 —
a PASS applies only to the artifact it checked — is unauditable afterwards. The
version is what lets `dag` tell a re-issue from a first verdict.

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
