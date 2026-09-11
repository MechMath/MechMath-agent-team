# Stop Conditions

Stopping is allowed only when one of these states is documented.

**This file is the SSOT for the stop conditions and for the pre-stop sequence.**
The permitted states, the forbidden ones, and the exact order of the checks a
stop runs are decided here and nowhere else. Any other file that needs them —
`orchestration.md`, `orchestrator-cookbook.md`, `memory-routing/SKILL.md`, the
two platform files — points here rather than restating the sequence. Three
restatements of it existed at once and no two agreed on which gates run, so a
run's stop depended on which file it happened to read.

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
- **The same stop also writes `writer/progress_summary.tex`** and exports
  `progress_summary.pdf` to the workspace root. The notes above are the restart
  document and their reader is the next run; this is the one a **person** reads,
  which is why it is typeset rather than left as markdown. Seven fixed sections
  opening with the problem statement and with the blocker third, ≤300 body lines
  and ≤10 pages, every established result given as statement + sketch + path, no
  harness vocabulary, every coined term defined. `gate summary` judges it and
  `gate stop` requires both the source and the PDF. Shape:
  `.agents/skills/article-writing/references/progress-summary-example.md`.

This does not weaken the conditions below. The progress notes are what a
permitted stop leaves behind; they never make an unpermitted stop permitted, and
"I could write a good progress note" is not a stop condition.

**Every stop also writes memory back.** The summary is for the human and the
notes are for the next run reading this workspace; this is what a run in a
*different* workspace inherits. The completion gate covers only the
verified-proof path, so the write-back is anchored at its own gate that applies
to all four states above (ADR 0022). Before stopping, run in order:

```
uv run python cli_tools/memory.py refresh <workspace>
uv run python cli_tools/memory.py aggregate-candidates <workspace>
uv run python cli_tools/gate.py discovery <workspace>    # blocks · every stop
uv run python cli_tools/gate.py dag <workspace>          # advisory · every stop
uv run python cli_tools/gate.py speed <workspace>        # advisory · every stop
uv run python cli_tools/gate.py summary <workspace>      # blocks · non-proof stops only
uv run python cli_tools/gate.py stop <workspace> [--verified-proof]   # blocks · every stop
```

The annotations are not decoration; running the sequence correctly depends on
them, and they are read off the implementations in `cli_tools/_gate/`, not off
anyone's prose.

**Three of the five block.** `gate discovery` (`discovery.py`) is a structural
lint over the branch queue and returns 1 on any finding: no branch written off
harder than its evidence allows, every `blocked` row naming what it waits on,
every empty search reporting the scope it covered, every gap specification
naming its hole. It reads no mathematics and it applies to every stop, proof or
not — a verified proof does not excuse a route that was recorded as refuted
without a counterexample. Run it whenever the branch queue changes, not only
here. `gate summary` (`summary.py`) returns 1 on any finding too, and it judges
`progress_summary.tex`, which only a non-proof stop is required to produce —
`gate stop`'s export check demands that file on the non-proof path and
`proof.pdf` on the proof path, so on a verified-proof stop there is nothing for
`summary` to judge. `gate stop` (`stop.py`) is the anchor and must pass.

**Two do not.** `gate dag` and `gate speed` emit every finding as a warning and
exit 0; their only error path is a workspace that does not exist. They are in
the sequence because a report nobody runs is the same as no report, and a stop
is the last moment anyone will read them. `dag` is the only check that follows
an edge of the lemma dependency graph — cycles, a lemma accepted before a
dependency it declares, a dependency's proof rewritten after the dependent's
`PASS` (invariant 15), dependency fields nothing can parse; its two ordering
findings are read from mtimes and it says so, so treat them as a question, not a
verdict. `speed` reports what the round cost: rewrite waste, required-read bytes
against the budget, concurrency from `logs/dispatch.jsonl`, and the shape of
this run's verification dispatches. Read both and say in the stop what they
showed. Neither may be treated as a blocker — halting a permitted stop on an
advisory warning is a worse error than omitting the gate, because it converts a
report into a gate nobody agreed to. `--strict` turns their warnings into a
non-zero exit; the stop sequence does not pass it.

Every subcommand takes `--waive REASON`, which records the violations and lets
the run continue. Use it when a check has misfired, rather than editing the
artifact until the check stops firing — the waiver log is what tells us which
checks to delete.

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

A gap is a work order, not an exit. Being able to say precisely what is missing —
what it must satisfy, and which hole it fills — is the most valuable thing the
discovery side produces, not evidence that the route is finished. Record it as a
specification with `consumed_at` naming the hole, dispatch it, and leave the
route open. One run wrote exactly such a specification and then abandoned on the
grounds that something was absent; the specification it had already written was
what the eventual solution needed.
