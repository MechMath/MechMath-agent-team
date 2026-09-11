# ADR 0005: Proof Rigor Standards and Verification Criteria

## Status
Accepted

## Context

"Rigorous informal proof" is an oxymoron that requires precise definition. Without clear standards, Generators will produce proofs at varying quality levels, and Verifiers will apply inconsistent criteria. The system needs a shared understanding of what constitutes a correct informal proof.

The Prover project's `informal_prover.py` uses a 3-tier scoring system (0, 0.5, 1) with explicit criteria. Its SOLUTION_PROMPT enforces "atomic steps" and "explicit justification." This demonstrates that rigor standards must be embedded in agent prompts, not left to interpretation.

Competition mathematics (Putnam, IMO, etc.) provides the closest analogue for our rigor standard: solutions are written for expert human reviewers who will catch any logical gap.

## Decision

### Rigor Standard: "Publication-Ready Informal Proof"

A proof is correct if and only if a competent mathematician would accept it for publication in a peer-reviewed journal. This means:

1. **Every logical step is justified** — by a named theorem, definition, or previously proven result
2. **No gaps** — no step requires the reader to fill in non-trivial reasoning
3. **No hand-waving** — forbidden phrases without accompanying justification:
   - "obviously", "clearly", "trivially"
   - "it is easy to see", "by inspection"
   - "the rest follows similarly"
   - "WLOG" (must justify why WLOG is valid)
4. **Correct scope** — the proof proves exactly the stated lemma, not a weaker or different statement
5. **Sound structure** — hypotheses are explicitly stated, conclusion follows from the chain of reasoning

### Generator Output Requirements

Each proof step must follow this format:

```markdown
**Step N**: <claim>

*Justification*: <theorem/definition/lemma used> applied to <specific objects>.
<Detailed reasoning showing why the justification applies.>
```

Example:
```markdown
**Step 3**: Since $f$ is continuous on $[a, b]$ and $[a, b]$ is compact, $f$ attains its maximum.

*Justification*: Extreme Value Theorem. The interval $[a, b]$ is compact in $\mathbb{R}$
(closed and bounded, by Heine-Borel). The function $f: [a, b] \to \mathbb{R}$ is continuous
by hypothesis. Therefore by the Extreme Value Theorem, there exists $c \in [a, b]$ such that
$f(c) \geq f(x)$ for all $x \in [a, b]$.
```

### Verifier Scoring Criteria

The Verifier evaluates each step on a 3-tier scale:

| Rating | Meaning | Action |
|--------|---------|--------|
| **VALID** | Step is logically correct and sufficiently justified | No action needed |
| **QUESTIONABLE** | Step may be correct but justification is insufficient or unclear | Requests clarification — Generator should expand |
| **INVALID** | Step contains a logical error, incorrect theorem application, or unjustified gap | Proof cannot pass — Generator must fix |

### Verdict Rules

- **PASS**: All steps VALID (or QUESTIONABLE steps where Generator's response_to_verifier.md resolves the concern)
- **FAIL**: Any step INVALID, or multiple QUESTIONABLE steps that collectively undermine the proof
- **NEEDS_REVISION**: No INVALID steps, but QUESTIONABLE steps need clarification

### Forbidden Patterns (Automatic FAIL)

1. **Circular reasoning** — using the conclusion (or an equivalent statement) as a premise
2. **Wrong direction** — proving A → B when the lemma requires B → A
3. **Missing cases** — claiming exhaustive case analysis but omitting cases
4. **Incorrect theorem application** — applying a theorem outside its hypotheses (e.g., applying L'Hôpital's rule when the limit isn't indeterminate)
5. **Scope error** — proving a weaker statement than claimed (e.g., proving for n > 1 when the lemma claims for all n ≥ 0)

## Consequences

### Pros
- **Consistent quality** — all proofs are held to the same standard
- **Clear Generator guidance** — the step format is unambiguous
- **Systematic Verifier evaluation** — the 3-tier rating prevents vague "this seems right" responses
- **Automatic FAIL patterns** — common LLM proof mistakes are explicitly flagged

### Cons
- **Verbosity** — requiring explicit justification for every step produces longer proofs
- **Over-rigidity** — some proofs are naturally more concise; forcing the step format on trivial lemmas adds unnecessary boilerplate (mitigated: Orchestrator can instruct Generator to use lighter format for simple lemmas)
- **Standard enforcement** — the Verifier is still an LLM and may not catch all violations (mitigated: optional Gemini cross-verification)
