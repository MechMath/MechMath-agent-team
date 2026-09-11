# ADR 0006: External LLM Integration — Cross-Verification and Discussion

## Status
Accepted

## Context

Using the same LLM family for both generation and verification creates a systematic blind spot: if Claude has a consistent misunderstanding of a mathematical concept, both the Generator (Claude) and the Verifier (Claude) will share that misunderstanding. The Prover project's `informal_prover.py` already implements a generate-then-verify loop using Gemini and GPT, demonstrating the value of cross-model verification.

Beyond verification, agents sometimes get stuck not because the math is wrong, but because they need a different perspective on proof strategy. The Prover project's `discussion_partner.py` provides free-form strategic discussion with external LLMs — a capability that is equally valuable for informal proofs.

External LLMs should serve two distinct purposes:
1. **Cross-verification** — independent scoring of proof correctness (structured output)
2. **Discussion** — free-form strategic advice when an agent is stuck (unstructured output)

## Decision

### 1. Cross-Verification

After the internal Verifier (Claude) issues a PASS verdict, the Orchestrator can optionally invoke external LLMs for independent scoring.

#### Verification Prompt Template

Adapted from the Numina Lean Agent's verification prompt (`informal_prover.py`):

```
Your task is to evaluate the quality of a proof. The proof should be a rigorous
mathematical argument with every step explicitly justified.

Please evaluate the proof and score it according to the following criteria:

- If the proof is completely correct, with all steps executed properly and clearly
  demonstrated, then the score is 1

- If the proof is generally correct, but with some details omitted or minor errors,
  then the score is 0.5

- If the proof does not actually prove the stated lemma, contains fatal errors, or
  has severe omissions, then the score is 0

- Additionally, referencing anything from any paper or external result does not save
  the need to prove the reference. It's okay IF AND ONLY IF the proof also presents
  a valid justification of the referenced argument(s); otherwise, if the proof omits
  the justification or if the justification is not completely correct, score accordingly

Please carefully reason out and analyze the quality of the proof below, and in your
final response present a detailed evaluation followed by your score.

Your response format:

Here is my evaluation of the proof:

[Present in detail the key steps of the proof or the steps for which you had doubts
regarding their correctness. For each step, explicitly analyze whether it is accurate:
for correct steps, explain why you initially doubted them and why they are indeed correct;
for erroneous steps, explain the reason for the error and its impact on the overall proof.]

Based on my evaluation, the final overall score should be: \boxed{...}

[where ... is 0, 0.5, or 1]

---

## Problem
{problem_statement}

## Lemma
{lemma_statement}

## Proof
{proof_text}
```

#### When to Use Cross-Verification

| Scenario | Cross-verify? | Reason |
|----------|--------------|--------|
| Simple lemma, clean PASS on v1 | Optional | Low risk, save tokens |
| Complex lemma, PASS after multiple revisions | **Recommended** | Higher risk of subtle errors surviving iterations |
| Main theorem (final assembly) | **Recommended** | Highest-stakes verification |
| Lemma that was previously stuck/re-decomposed | **Recommended** | Troubled history suggests difficulty |
| Human requests it | **Required** | Human judgment overrides defaults |

#### Handling Disagreements

| Internal Verifier | External LLM | Action |
|-------------------|-------------|--------|
| PASS | Score 1 | Merge to proof.tex |
| PASS | Score 0.5 | Orchestrator reviews external feedback, may request Generator revision |
| PASS | Score 0 | **Do not merge.** Send external feedback to Generator. Treat as Verifier FAIL. |
| FAIL | (not called) | Standard revision flow |

### 2. Discussion Partner

Any agent (Generator, Sketcher, or even the Orchestrator) can consult an external LLM for free-form strategic advice. This is **not** structured verification — it is an open-ended conversation about proof strategy, mathematical intuition, or alternative approaches.

#### Discussion Prompt Template

Adapted from the Prover project's `discussion_partner.py`:

```
You are a mathematical discussion partner. You are being consulted by another
mathematician who is working on a proof and needs strategic advice.

## Context
{context — problem statement, current proof state, what has been tried}

## Question
{specific question — e.g., "What approach should I try for the induction step?",
"Is this decomposition the right strategy?", "How should I handle the boundary case?"}

Provide thoughtful mathematical advice. Be specific about techniques, theorems,
and strategies. If the approach seems wrong, say so directly and suggest alternatives.
```

#### When to Use Discussion

| Scenario | Who calls it | Purpose |
|----------|-------------|---------|
| Generator stuck on a proof step | Generator | Get alternative proof strategy ideas |
| Sketcher unsure about decomposition | Sketcher | Validate decomposition strategy before committing |
| Verifier finds a subtle issue, wants to confirm | Verifier | Double-check whether a step is truly invalid |
| Orchestrator deciding whether to re-decompose | Orchestrator | Get external opinion on tractability |

#### Discussion vs. Verification — Key Distinction

| | Cross-Verification | Discussion |
|---|---|---|
| **Purpose** | Score proof correctness | Get strategic advice |
| **Output** | Structured: score + analysis | Free-form: advice text |
| **When** | After internal Verifier PASS | Anytime an agent is stuck |
| **Who calls** | Orchestrator only | Any agent |
| **Affects verdict?** | Yes (can block merge) | No (advisory only) |

### Implementation

Skills are CLI tools in `cli_tools/`:

| Tool | Purpose | CLI |
|------|---------|-----|
| `gemini_verify.py` | Cross-verification via Gemini | `uv run python cli_tools/gemini_verify.py <proof_file> --problem <problem_file> --lemma <lemma_file>` |
| `cross_verify.py` | Cross-verification via GPT | `uv run python cli_tools/cross_verify.py <proof_file> --problem <problem_file> --lemma <lemma_file>` |
| `discussion_partner.py` | Free-form discussion with Gemini/GPT | `uv run python cli_tools/discussion_partner.py "question" [--backend gemini\|gpt] [--context <file>]` |

Verification tools return JSON: `{"score": <float>, "analysis": "<text>"}`.

Discussion tool returns plain text advice.

All tools require the corresponding API keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`).

### Generator Solution Prompt Guidance

When a Generator produces a proof, it should follow a structure inspired by the Numina Lean Agent's solution prompt:

- **Purely algebraic/symbolic**: Do NOT use geometric intuition or visual symmetry as proof. All geometric concepts must be translated into precise algebraic or analytic definitions.
- **Atomic steps**: Decompose reasoning into the smallest possible logical units. Do not combine multiple deductive steps into one.
- **No hand-waving**: Forbidden phrases include "obviously", "it is clear that", "by inspection", or "intuitively".
- **Explicit justification**: For EACH step, state the rule of inference, algebraic identity, axiom, or theorem used.
- **Show all calculations**: Show every intermediate stage of simplification or substitution. Do not skip algebraic manipulation steps.

### Generator Refinement Protocol

When a Generator receives verification feedback (either from internal Verifier or external cross-verification), its revision should follow this protocol (adapted from `informal_prover.py`'s refinement prompt):

1. Carefully read the feedback and determine which points are **valid** and which may be due to **misunderstanding or evaluator error**
2. If you **agree** with a feedback item: revise the proof to fix the issue
3. If you **disagree** with a feedback item: keep the original reasoning, but add **explicit explanations or clarifications** to prevent future misunderstandings
4. The revised proof must be self-contained, logically coherent, and mathematically rigorous

## Consequences

### Pros
- **Catches systematic blind spots** — different models have different failure modes
- **Unblocks stuck agents** — discussion provides fresh perspectives when agents are stuck
- **Separates concerns** — verification (structured, pass/fail) vs. discussion (free-form, advisory) serve different needs
- **Higher confidence** — a proof verified by multiple independent LLMs is more likely correct

### Cons
- **API cost** — each external call costs tokens on external APIs
- **Latency** — external API calls add time to the proof pipeline
- **Discussion quality variance** — external LLMs may give bad advice; agents must remain critically independent
- **API dependency** — requires `GEMINI_API_KEY` and `OPENAI_API_KEY` to be configured
