# Stop Conditions

Stopping is allowed only when one of these states is documented.

## Required Before Every Stop

Whichever state below applies, the run does not end silently.

- **Verified Proof** — dispatch Writer (`FULL_ARTICLE`/`COMPLETE_PROOF`) and
  export `proof.pdf`.
- **Every other permitted stop** — Verified Obstruction, Human Needed, or Branch
  Budget Exhausted — **dispatch Writer in `PROGRESS_NOTES` mode and export
  `progress_notes.pdf` before stopping.** The notes must carry all five required
  sections: routes explored; verified results with their complete proofs written
  out; failed explorations with the reason each failed; possible next paths
  including the current atomic blocker; and a short literature summary. Format
  SSOT: `.agents/skills/article-writing/references/progress-note.md`.

This does not weaken the conditions below. The progress notes are what a
permitted stop leaves behind; they never make an unpermitted stop permitted, and
"I could write a good progress note" is not a stop condition.

**Every stop also writes memory back.** The reader-facing document is for a
human; this is what the *next run* inherits. The completion gate covers only the
verified-proof path, so the write-back is anchored at its own gate that applies
to all four states above (ADR 0022). Before stopping, run in order:

```
uv run python cli_tools/memory.py refresh <workspace>
uv run python cli_tools/memory.py aggregate-candidates <workspace>
uv run python cli_tools/gate.py stop <workspace> [--verified-proof]
```

`aggregate-candidates` dedups `memory/candidates/*.jsonl`, writes the survivors
into `memory/experience/`, and re-renders the resident `memory.md`, so a lesson
learned here is loaded at the start of the next run. `gate stop` must pass: it
checks a fresh local index, a long-term read trace, a captured lesson when the
run recorded failures, the promotion, and the stop's export. A run that recorded
only dead ends still owes the next run those dead ends — if a failure genuinely
carries no transferable lesson, say so with a `no_constraint` marker rather than
leaving the channel empty (see the `memory-routing` skill).

## Verified Proof

The original statement is proved by `proof.tex` or the accepted proof artifact.
Required evidence:

- detailed Verifier `PASS`;
- review-packet lint accepted;
- open obligation ledger empty;
- exact statement preservation confirmed;
- completion gate passed or explicitly scheduled by the harness.

## Verified Obstruction

A concrete counterexample, contradiction, or impossible precondition audit is
accepted under the original hypotheses and accepted readings. Required evidence:

- CE-Hunter or equivalent obstruction artifact;
- proof-review workflow context comparing best proof route with obstruction
  route, classified by Regulator;
- fresh Verifier acceptance;
- target-reading and definition assumptions recorded.

## Human Needed

Human is allowed only when the harness cannot proceed because:

- the original statement has no unique accepted reading after definition lookup;
- required problem input is missing;
- external permission or credentials are required;
- the human explicitly requested review or choice.

Do not route to Human simply because an agent is stuck, a source theorem was
not found, or one route failed.

## Branch Budget Exhausted

Exhaustion is allowed only when `branch-queue-cookbook.md` exhaustion standard
is met and the evidence files are named in `STATUS.md` or recovery state.

## Forbidden Terminal States

These are restart states, not final answers:

- source theorem unavailable;
- definition not found;
- search failed;
- Generator exhausted local attempts;
- Verifier rejected current route;
- no generator-ready DAG;
- `future Sketcher/Human after a new idea`;
- missing intermediate construction;
- open final assembly bridge.
