# Orchestrator Cookbook

The Orchestrator is a hub-and-spoke dispatcher. It owns `STATUS.md`,
`proof.tex`, route history, branch queues, and final user-facing state. It does
not supply missing mathematical proof, verification, definitions, theorem
preconditions, computations, counterexamples, or reader-facing mathematical
exposition from private reasoning.

## Operating Guide (advisory)

This is the *typical* order for a non-terminal workspace, not a mandatory loop.
The Orchestrator keeps the routing autonomy declared in `orchestration.md`'s Core
Contract and dispatches by the current blocker. The only hard parts are the step-1
preconditions and the invariant-level rules (single-pass verification, `PASS`
before merge, pop the next branch on failure) — not the step ordering:

1. At the start of every non-trivial cycle, load memory and refresh the
   mechanical indexes before dispatching. First (hard precondition) read the
   long-term memory:
   `uv run python cli_tools/memory.py read --tier long-term --view compact <workspace>`.
   Then refresh and read the local tier:
   `uv run python cli_tools/memory.py refresh <workspace> --view compact` and
   `uv run python cli_tools/memory.py read --tier local <workspace>`; also
   refresh `search.py index`, `workspace.py references`, and `workspace.py presentation`
   when their inputs are relevant. This is a required step, not an optional
   alternative to scanning the directory. Then read `problem.md`, `STATUS.md`,
   route history, latest review packets, recovery packets, and relevant
   specialist artifacts — **latest only, and under a budget**: this set is
   re-read at the start of every round, so anything left in it is paid for once
   per round for the rest of the run. Keep it under about 60 KB. Superseded
   versions are never in it; `review_packet_v7.md` replaces `review_packet_v6.md`
   rather than joining it. Check the size with
   `uv run python cli_tools/gate.py speed <workspace>`, which reports the set's
   current bytes and names the largest member.

   When it is over budget the file to look at is almost always `STATUS.md`,
   because it is the only member that grows without bound. Move append-only
   narrative to `STATUS_history.md` and rows that reached `rejected` or `done`
   to `STATUS_closed.md`, leaving `active`, `queued`, `open`, and `blocked` rows
   behind — `blocked` is waiting on a named condition, not finished, so it stays.
   **Archiving is not closing**: a row keeps
   its status and its evidence paths, it just stops being re-read, and a branch
   that is archived by mistake must be recoverable from the archive by id. When
   in doubt leave it in `STATUS.md` — re-opening a settled branch costs far more
   than re-reading a line.
2. Identify the current blockers — **plural — and say what they are in your own
   words.** There is no fixed class vocabulary: no closed list fits the blockers
   that actually occur, and picking the nearest label loses the part that
   mattered. Listing only the single smallest blocker is what turns a set of
   independent lemmas into a queue; ask "what is blocked *right now*", not "what
   is blocked *first*".
3. Choose the smallest specialist that owns each blocker. Use
   `subagent-dispatch-cookbook.md` when unsure.
4. **Dispatch every independent blocker in one batch**, each specialist with its
   own explicit input paths, write target, blocker, and acceptance condition.
   Blockers are independent when their write targets do not overlap — separate
   `lemmas/<id>/` directories are independent by construction, so generator-ready
   lemmas with no dependency edge between them go out together, not one per
   round. **Up to 6 at once.** Serialise only what an actual dependency
   serialises.

   When the frontier is **wider than the cap**, or two blockers want the same
   specialist, a choice is forced and this is the rule for it — the one
   `prompts/sketcher.md` hands over and nothing here used to receive. Rank by the
   two dimensions the Synthesizer ranks routes on: **Feasibility** and
   **Contribution**. The assembly node carries the highest Contribution there is, so
   it goes out early, against stated lemmas rather than proved ones
   (`hardest-first.md`). And the ban travels with the rule: **do not rank by how
   checkable it looks** — that is the reading that spends a cycle on the tractable
   lemmas and meets the assembly last.

   This number was raised to 12 on 2026-08-25 and reverted the same day, on the
   human's decision. The argument for raising it was that 6 was a number in this
   file rather than a limit of anything. That was wrong in two ways. `.codex/
   config.toml` enforces `max_threads = 6`, so on one of the two platforms it is
   exactly a limit of something — and a cookbook read by both platforms saying
   "up to 12" tells Codex to do something its runtime refuses. And ADR 0024 §4.2
   had already decided not to raise it, with a precondition: observe with
   `logs/dispatch.jsonl` first. That measurement does not exist yet — 159 rows
   across 6 workspaces, none written by the hook — so the raise happened on an
   unmet precondition, which is the part worth remembering. See ADR 0024 §0bis.1
   and Q8.
5. Collect the specialist artifacts as they land. **Do not wait for the batch.**
   If one requests another specialist, treat that request as a handoff artifact
   and dispatch through the Orchestrator while the rest are still running.
6. Run fresh Verifier checks when a plan, proof, refinement, or terminal
   obstruction is being adopted. **A lemma's Verifier starts the moment that
   lemma's Generator artifact lands**, not when the slowest sibling finishes —
   the Verifier is stateless and reads one lemma, so it has nothing to gain by
   waiting and the whole batch pays for the wait.
7. Update `STATUS.md`, route history, and the active branch queue, then record
   the change in workspace memory so the ledger stays current. Run
   `memory.py refresh <workspace>` to pick up updated `STATUS.md`, recovery, and
   review-packet files, and use
   `memory.py append <workspace> --channel <channel> --source <file> --kind <label>`
   for artifacts the refresh globs do not cover.
8. Continue with the next queued branch unless `stop-conditions.md` permits a
   terminal stop. Set the failed branch to `open` — `rejected` needs an exact
   counterexample or a certification-mode Verifier FAIL, and `blocked` needs a
   named external condition (`branch-queue-cookbook.md`). Continuing also
   includes going deeper on the current branch or returning to an `open` one,
   not only popping the next queued branch.
9. At a permitted stop, write memory back before stopping: `memory.py refresh`,
   then `memory.py aggregate-candidates <workspace>` to promote the run's
   candidate lessons into `memory/experience/` and re-render the resident
   `memory.md`, then `gate.py stop <workspace>
   [--verified-proof]`, which must pass. This applies to every stop, not only a
   verified proof — the completion gate covers only the proof path
   (`stop-conditions.md`, ADR 0022).

## The Revision Chain Is The Critical Path

Widening the DAG has a floor, and the floor is the worst lemma's revision chain.
Measured on the 26-hour run: 15 lemmas, 38 generator rounds, and **one lemma took
11 of them over 7.9 hours**. Even with every lemma running in parallel that run
could not have finished faster than 7.9 hours — about 3.3x, and no more. Past
that point the only thing left to shorten is the chain itself.

Two rules do that. Both spend dispatches to buy latency, which is the trade this
harness should be making.

### Split at the third revision

**A lemma that is about to receive its fourth generator dispatch does not need a
fourth revision. It needs to be split.** Send a Sketcher or Refiner to
re-decompose it into sub-lemmas, and dispatch those in parallel.

Three revisions that did not converge is evidence about the lemma, not about the
Generator. On the 11-round lemma every version was larger than the last
(66 KB → 159 KB) — the artifact was accreting, not converging, and rounds 10 and
11 changed no mathematics at all by their own statement. A serial chain of eight
more rounds was bought where a split would have produced width.

The exception is a lemma whose Verifier reports are *shrinking*: fewer blocking
issues each round, each one narrower than the last. That is convergence and it
should be allowed to finish.

### Start the next round before the verdict arrives

For a lemma already at revision 2 or more, dispatch the next Generator **at the
same time** as the Verifier, on the assumption the verdict will be
`NEEDS_REVISION`. Give it the same inputs and the standing instruction to repair
whatever the Verifier is about to name.

- If the verdict is `NEEDS_REVISION`, the repair is already in flight and one
  full turnaround has been removed from the chain.
- If the verdict is `PASS`, the speculative attempt is **discarded unread**, at
  the price of one dispatch.

Write it to the parallel-attempt path (`proof_v<N>b.md`, see
`workspace-and-ownership.md`) so nothing is clobbered and nothing is spliced.
This is worth doing precisely when the chain is long, and the chain being long
is exactly when the verdict is most likely to be `NEEDS_REVISION` — the bet gets
better the more it matters.

**Do not speculate on round 1.** A first verdict is the most informative one in
the run and often changes the plan rather than the proof; speculating there
buys a repair to a proof that may be about to be abandoned.

## When A Dispatch Stalls: Send A Shadow, Do Not Escalate

**On the first missed checkpoint, dispatch a shadow owner to a _different target
file_. Whichever lands first is adopted; the other is discarded unread.**

**A missed checkpoint is not "a few minutes have passed".** A shadow may not go
out until the primary has been running longer than that role's normal turnaround
— use the median from `logs/dispatch.jsonl`, or roughly 10 minutes if there is no
log yet. Measured failure: a run shadowed **18 of its 19 dispatches**, each about
3 minutes into a primary whose median turnaround was 4.4 minutes. Every one of
the 18 was discarded unread, peak concurrency was 2 and that 2 was always a
primary next to its own shadow. It doubled the dispatch count and saved nothing,
because nothing had stalled.

The test is one question: **has this dispatch stopped behaving normally?** If the
answer is "I do not know yet", it is too early. A shadow on a healthy dispatch is
pure cost — it cannot land sooner than a primary that started before it.

Do not run an escalation ladder. Polling a stalled owner, then asking for a
focused checkpoint, then issuing a completion request, then granting a final
allowance, spends five to seventeen minutes *before* a replacement is even sent —
and the replacement then starts from nothing. One workspace's `STATUS.md` carries
**74 instances** of that ladder's vocabulary. Its worst chain cost 48 minutes for
a single artifact: four consecutive owners missed, the run halted, a human waited
20 minutes, a fifth round produced only a skeleton, and the sixth finally worked.

The shadow costs one extra dispatch. The ladder costs the critical path.

```
recovery/route_recovery_7.md          <- original owner
recovery/route_recovery_7_shadow1.md  <- shadow, dispatched on the missed checkpoint
```

Rules that keep this from becoming a second problem:

- **A shadow is a fresh attempt at the same task, never a continuation.** Give it
  the same inputs and acceptance condition, not the stalled owner's partial work.
- **Never merge the two.** Adopt one file whole and discard the other. Splicing
  two independent attempts is authoring mathematics, which the Orchestrator does
  not do.
- **One shadow per stall.** If the shadow also misses, that is a real blocker —
  stop and say what is blocked, rather than opening shadow 3.
- **Record both in `STATUS.md`**: which was adopted, and that the other was
  discarded. A discarded shadow is not a failure to explain, it is the cost of
  the insurance.

Ownership is unchanged: each file still has exactly one writer. The shadow has
its own file, so nothing is shared and nothing can be clobbered.

## Dispatch Log

**This section is platform-split, and this file is read by both platforms.**
Read the half that applies to you. An earlier revision of this file gave the
Claude answer to everyone, which left the Codex side with no writer for a file
its own gates ask about.

**On Claude Code: you do not write this.** `logs/dispatch.jsonl` is written by
the `PreToolUse`/`PostToolUse` hook `.claude/hooks/dispatch_log.py`, one line per
dispatch, with timings, byte counts, token counts and prompt shape.

This file used to ask you to append each line by hand. Measured on the two runs
that followed: one kept 38 of 39, the next kept 5 of 352 and abandoned it after
fifteen minutes. A rule that must hold on the four-hundredth dispatch belongs in
middleware, not in a prompt — so on the platform that has middleware, the
instruction is gone rather than reworded, because two writers on one file is
worse than either alone.

**On Codex: you write it, because there is no hook mechanism to write it for
you.** `.codex/config.toml` carries `max_threads` and `max_depth` and nothing
else; ADR 0020 Q1 considered a dispatch wrapper and declined it. So append one
line per dispatch:

```json
{"role":"verifier","target":"lemmas/x","started":"2026-08-25T09:00:00Z","ended":"2026-08-25T09:07:00Z","bytes":8400,"batch":"b3","source":"hand"}
```

`role`, `started`, `ended` are what every later number is computed from;
`batch` is what separates a batch that ran together from one that ran one at a
time. Mark `"source":"hand"` so the gates can tell a hand-kept log from a
recorded one — they read the same file and must not read it the same way.

Two honest limits on the hand-kept half, so nobody is surprised by them.
**It will be incomplete**; the 5-of-352 measurement above is what a busy run
does to this instruction, and `gate speed` reports the shortfall against the
artifact count rather than pretending the log is the truth. And **three metrics
are not available to you at all** — `platform_mix`, `prompt_shape` and
`token_cost` need fields only the hook can produce. The gate reports those as
`unmeasured`, never as zero. Everything else, concurrency included, is computed
from `started`/`ended` and works from a hand-kept log.

The one thing still yours: **name the batch.** When you dispatch several
specialists together, say so in the dispatch text; `batch` is what separates a
batch that ran together from a batch that ran one at a time.

This is the only timing record the natural-language side has. The formal side has
millisecond `lean_check` logs; here, every timing had to be reconstructed from
file mtimes, which cannot separate a stalled harness from an operator who stepped
away, and cannot see a dispatch that produced no artifact at all — the expensive
failures are exactly the invisible ones.

**The log is checked rather than trusted**: `gate.py speed <workspace>` compares
the line count against the artifacts on disk and says so when they disagree. An
incomplete log is worse than none, because it makes a floor look like a
measurement — so the gate reports the gap rather than the log's own claim. If it
reports a gap it means different things by platform: on Claude the hook is not
firing, which is a harness fault to report; on Codex your own appends fell
behind, which is expected under load and is a shortfall to state at the stop.
Neither is a reason to backfill the file after the fact: a line written from
memory is a guess with a timestamp on it.

## Handoff Format

When an agent needs another agent, require a short handoff:

```markdown
## Handoff Request
- Requested owner:
- File target:
- Context paths:
- Atomic blocker:
- Acceptance condition:
- Queued alternatives affected:
```

The Orchestrator reads the handoff and dispatches the next owner. Subagents do
not message, spawn, or command each other directly.

## Orchestrator Self-Check

Before writing or editing any artifact, ask:

- Is this `STATUS.md`, route history, query routing, branch queue, or verified
  merge assembly? If yes, Orchestrator may own it.
- Does this change mathematical content, a target contract, a lemma statement,
  a proof attempt, a proof repair, theorem support, definition reading,
  computation evidence, or a verification packet? If yes, dispatch a
  specialist instead.
- Am I writing reader-facing article prose, a local rewrite, or a progress note?
  If yes, dispatch Writer instead.
- Am I using a mechanical check as a substitute for mathematical verification?
  If yes, route to Verifier.
- Am I stopping because no proof exists yet? If yes, update the branch queue
  and continue unless stop conditions permit stopping.

## Refiner Trigger

After a complete proof passes fresh verification, retain that proof as the
fallback and dispatch Refiner once for shortening or cleanup unless the
human explicitly disables shortening. The refined proof replaces the fallback
only after fresh verification accepts it.

## Presentation And Reporting Trigger

Presentation is a reader-facing layer, not a mathematical stop condition. After a
verified proof (and after Refiner is accepted, rejected, or skipped) dispatch
Writer in `FULL_ARTICLE`/`COMPLETE_PROOF` mode.

**Before any stop that is not a verified proof, dispatch Writer in
`PROGRESS_NOTES` mode first.** This covers a verified obstruction, a
human-needed ambiguity, an exhausted branch budget, and a human-requested pause.
This is not a licence to stop early: the stop must already be permitted by
`stop-conditions.md`. The progress notes are what you leave behind when it is.

The full flow — Writer dispatch, `refs-bib`, the `citation-audit` gate, KLMM
compilation, and the exported `proof.pdf` / `progress_notes.pdf` — is the SSOT in
`prompts/references/latex-and-blueprint.md`. A presentation failure keeps the
proof's mathematical status unchanged (record it as pending).
