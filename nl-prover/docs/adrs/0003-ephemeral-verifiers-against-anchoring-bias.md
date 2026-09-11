# ADR 0003: Ephemeral Verifiers to Prevent Anchoring Bias

## Status
Accepted

## Context

When an LLM verifies a proof it has seen before, it develops **anchoring bias** — prior exposure to the proof structure makes it more likely to accept the same logical flow, even if the flaws haven't been fixed.

Until 2026-08-17 that claim was followed here by an appeal to research that does not exist: *"models that have seen a student's work once will rate revisions more favorably regardless of actual improvement."* No such result could be found, and the sentence cited nothing. It was the load-bearing warrant for this entire ADR. What the literature does establish is narrower than the folklore in scope, stronger in mechanism, and points the arrow the other way:

- [**AMEL**, arXiv:2605.22714](https://arxiv.org/abs/2605.22714) — across 84,088 calls to 12 models, prior evaluations in a shared context shift later judgments toward the conversation's prevailing polarity (d = −0.17, p < 10⁻⁵³), and negative histories bias 1.52× harder than positive ones. The bias does **not** grow with context length — 5 prior turns and 50 produce the same shift — so it saturates almost immediately; one prior verdict is close to the whole cost. Its own recommendation is a fresh context per item. What it does *not* establish: it measures generic evaluation items, not proof verification, and it finds polarity-following, **not** leniency. A prior FAIL should drag the next verdict toward FAIL, harder than a prior PASS drags toward PASS. The deleted folklore had the sign backwards.
- [**Contextual Drag**, arXiv:2602.04288](https://arxiv.org/abs/2602.04288) — flawed reasoning present in the context degrades subsequent reasoning across 11 models and 8 tasks (10–20% reductions), and "neither external feedback nor successful self-verification suffices to eliminate this effect." This is the result that kills the mitigation-by-disclaimer we actually shipped: telling the reader to remain skeptical of the contaminating text does not decontaminate it. It does not establish anything about *judgement* specifically; it establishes that presence in context, not endorsement of it, is what does the damage.
- [**Panickssery, Bowman & Feng**, NeurIPS 2024, arXiv:2404.13076](https://arxiv.org/abs/2404.13076) — LLM evaluators recognise their own generations, and self-recognition capability correlates linearly with the strength of self-preference. It says nothing about anchoring; it is here because it names the residue a fresh context cannot remove (see Consequences).

In formal theorem proving (Lean, Coq), this doesn't matter — the type checker is deterministic and stateless. But for informal proofs, verification is inherently subjective and context-dependent. The Verifier IS the type checker, and it must be as unbiased as possible.

The Prover project's proof agent works in tmp files and operates within a single session, accumulating context. This is fine for formal proofs where compilation is the ground truth. For informal proofs, accumulated context is a liability for the Verifier.

## Decision

**Verifiers are ephemeral.** Each verification request spawns a completely new Verifier agent with:
- No memory of prior verification rounds for this lemma
- No access to previous verifier reports (only the current proof version)
- A fresh, skeptical disposition established by the system prompt

### Protocol

1. Generator writes `proof_v<N>.md`
2. Orchestrator **destroys** any existing Verifier context (if applicable)
3. Orchestrator spawns a **new** Verifier with:
   - The problem statement (`problem.md`)
   - The lemma statement (`statement.md`)
   - Verifier risk checklist items embedded in the statement, plus referenced
     analysis preflight Collector outputs when needed
   - The current proof (`generator/proof_v<N>.md`)
   - **NOT** the previous verifier reports
   - **NOT** the Generator's account of its own work (`generator/response_to_verifier.md`,
     `generator/status.md`) — see the 2026-08-17 amendment below
4. Verifier writes `report_v<N>.md` and `verdict.md`
5. Verifier instance is discarded

### What the Verifier Sees

| File | Included? | Reason |
|------|-----------|--------|
| `problem.md` | Yes | Context for what's being proved |
| `statement.md` | Yes | The lemma to be verified |
| `queries/<query_id>/collector.md` named by risk checklists | Yes | Local analysis preflight warnings the Verifier must audit |
| `generator/proof_v<N>.md` | Yes | The proof under review |
| `generator/response_to_verifier.md` | **No** (amended 2026-08-17) | The author's defence of the work under review. "Read but do not be swayed" was measured and does not hold |
| `generator/status.md` | **No** (amended 2026-08-17) | The author's account of its own progress — same channel, less obviously so |
| `verifier/report_v<N-1>.md` | **No** | Would anchor to prior judgments |
| `generator/proof_v<N-1>.md` | **No** | Would create comparison bias |

### What the Verifier Is Told

The Verifier prompt explicitly states:
- "You are an independent referee. This is the FIRST time you are seeing this proof."
- "Do not open the previous round's verifier output, the previous proof, or the Generator's account of its own work." (2026-08-17; this replaced "Read it, but remain independently skeptical", which was measured not to hold)
- "Your standard for PASS: you would stake your professional reputation on the correctness of every step."

## Consequences

### Pros
- **Reduces one anchoring channel** — the measured effect is a *shift*, not a switch, so removing prior verdicts from context removes the shift they cause and nothing else. Two sources of correlation survive a fresh context untouched: **self-preference**, which scales with a model's ability to recognise its own output ([arXiv:2404.13076](https://arxiv.org/abs/2404.13076)), and **shared priors** — the same training data yields the same blind spots. Both bite hardest here, because in this harness the Generator and the Verifier are usually *the same model*. A fresh instance of the author is not an independent referee; it is the author with amnesia about the conversation but none about how it thinks. Ephemerality buys the context channel only, and claiming more than that is how this ADR acquired its folklore in the first place.
- **Consistent verification quality** — the Nth verification is as skeptical as the 1st
- **Simpler Verifier prompt** — no need to manage "what you said last time" context

### Where the benefit is concentrated

The effect is not uniform across lemmas. AMEL measures d = −0.36 on high-entropy items against
d = −0.15 where the model's baseline judgement is already deterministic — the bias lands where
the evaluator is genuinely uncertain. Translated: freshness buys most on **contested lemmas**,
the ones where a competent referee could go either way, and close to nothing on proofs with an
obviously broken step. That is the good case for us, since the contested lemmas are exactly the
ones a bad PASS escapes through.

It is also a measurement instruction. Evaluate this intervention **on contested lemmas only**.
Averaged over a corpus dominated by clear-cut proofs, a real effect of this size disappears
into the clear-cut items and the intervention will read as having done nothing.

### Cons
- **Higher token cost** — re-reading problem, statement, and proof from scratch each time
- **No accumulated Verifier insight** — if the Verifier noticed a subtle issue in v1, it won't automatically check for it in v2. Mitigated by carrying the concern in the *artifact* (obligation ledger, Verifier Risk Checklist) as an open mathematical question; **not** by `response_to_verifier.md`, which the new Verifier no longer reads (amended 2026-08-17)
- **Potential inconsistency** — two fresh Verifiers might disagree on the same proof (acceptable — informal proof verification is inherently probabilistic)

### Mitigation for Lost Insight

When the Orchestrator spawns a new Verifier, it can direct attention — but the concern must
arrive as **a question about the mathematics, carried by the artifact**, not as a report of
what earlier referees concluded:

```
Open obligation on this lemma (in the statement's Verifier Risk Checklist):
- Step 3 applies X. Does X require n >= 3, and is that available here?
```

not

```
ADDITIONAL CONTEXT FROM ORCHESTRATOR:
Prior verification rounds have flagged these concerns (YOU may or may not agree):
- Step 3 was previously questioned for relying on X without justification
- The Generator claims to have addressed this in response_to_verifier.md
```

Both point at Step 3. The first is a thing to check; the second is a verdict to agree or disagree with, and it names who already decided. Only the first survives this ADR.

### Amendment, 2026-08-17 — why the loopholes closed

The original decision was sound and was not being obeyed, because the file the Verifier actually loads never carried it. `prompts/verifier.md` contained **zero** occurrences of the prohibition above; it existed only in this document, which the Verifier never reads. Meanwhile this section's own former mitigation — the block now shown as the counter-example — sanctioned putting prior verdicts back into the prompt.

Measured over **87 verification dispatches** (2026-07-25 → 2026-08-15, 8 sessions):

- **100%** told the Verifier it was fresh, stateless and independent;
- **57%** also supplied the Generator's own claims, status narrative or defence;
- **45%** also supplied prior verdicts or findings;
- **84%** supplied at least one of the two; **16%** handed over the artifact alone.

The ephemerality this ADR bought — a fresh *instance* — was real. The independence it was bought for was not. Three changes follow: the prohibition now lives in `prompts/verifier.md`, where it is read; `response_to_verifier.md` and `status.md` join the excluded list, because the author's defence of the work is the same anchoring channel as the previous referee's verdict; and the packet records `Anchoring inputs received`, so a review that was handed prior context says so instead of being indistinguishable from one that was not.

The transfer channel for a live concern is the artifact — the obligation ledger and the Verifier Risk Checklist — which the Verifier reads anyway and which states concerns as mathematics rather than as judgements.

A disclaimer attached to anchoring content does not remove it. "Read it, but remain independently skeptical" is the construction that was measured at 84%, and it is the construction [arXiv:2602.04288](https://arxiv.org/abs/2602.04288) reports as failing on precisely this axis: an instruction to discount contaminating context does not undo the contamination.

**What the 87 dispatches do not show.** They measure *exposure* — how often the Verifier was
handed anchoring material. They do not measure *effect*: not one of those 87 tells us whether a
verdict would have differed. The ablation that would settle it is small and specific — same
reviewer model, same proof artifact, prior verdict present versus absent, measured on the
verdict-flip rate, stratified by whether the lemma is contested. The harness already holds the
baseline half: every dispatch in the 2026-07-25 → 2026-08-15 window has its artifact, its packet
and its verdict on disk, so the absent-condition arm is a replay rather than new proof work.
Until it runs, the causal claim in this ADR rests on transfer from [arXiv:2605.22714](https://arxiv.org/abs/2605.22714)
and [arXiv:2602.04288](https://arxiv.org/abs/2602.04288), which is a far better warrant than the
sentence it replaced and still not a measurement of this system.
