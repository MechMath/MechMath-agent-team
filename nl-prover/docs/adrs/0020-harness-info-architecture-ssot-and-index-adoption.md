# ADR 0020: Harness Information-Architecture Governance — Single-Source-of-Truth Deduplication and Index Adoption

## Status

Accepted — **implemented (P1–P5), 2026-07-23.**

> **Count correction (2026-08-25).** Every "**five facades**" in this ADR —
> §Status, the current-state review, the ownership table's "five-facade list",
> and the open-question review — reads **six** today. `cli_tools/verify.py`
> (assembling one verification dispatch from paths and a prior verdict) landed
> as a sixth model-facing facade; `.codex/rules/default.rules` now carries six
> facade `prefix_rule`s and `CLAUDE.md` says "six facades". The **governance
> decision is unchanged** — one facade per purpose, internal packages folded
> underneath, allowlist granted per facade rather than per tool — and the count
> was never the decision. The gate facade has likewise grown: `gate.py` now
> dispatches twelve subcommands (`complete`, `stop`, `proof-attempt`,
> `proof-review`, `review-packet`, `result-contract`, `citation-audit`,
> `discovery`, `speed`, `dag`, `summary`, `contracts`); the subcommand lists in
> the body are records of their date and are not exhaustive today. One of them,
> `gate contracts`, is this ADR's own governance made mechanical: it reads the
> code for facts the repo states about itself — the facade list, and the
> concurrency ceiling asserted in both `_gate/speed.py` and the cookbook — so a
> drifting count is caught by a lint rather than by a reader.

> **Implementation status.** P1–P5 landed; open questions resolved as: **Q1** —
> Codex has no hook, so enforcement is (a) the `gate.py complete` freshness/read
> checks + (b) `required` wording; no dispatch wrapper was added. **Q2** — yes, the
> inv.12/16 clarification is in `AGENTS.md`. **Q3** — the stale baseline is
> `STATUS.md` only (`STALE_BASELINE` in `cli_tools/_memory/local.py`, easy to
> widen). **Q4** — recorded only; the `code-executor` prompt was NOT changed.
> Deliverables:
> - **P1**: `AGENTS.md` inv.2 `Refiner` de-duplicated (and noted why inv.1 ≠ inv.2);
>   `collector.md` unified (deprecated `collector_result.md`); `Code Executor`
>   display name unified in prose (identifiers unchanged).
> - **P2**: owner table merged into `workspace-and-ownership.md` (+ ADR 0018
>   `knowledge/*` and ADR 0019 `references/ledger.jsonl`/`refs.bib` rows),
>   `artifact-ownership.md` → pointer; delegation-triggers SSOT = dispatch cookbook,
>   `AGENTS.md`/`orchestration.md` → pointer; `orchestration.md` converged to a
>   Reference Map with an each-cycle precondition pointer; routing loop reframed as
>   advisory (`AGENTS.md` keeps only hard preconditions; cookbook = advisory guide);
>   `workspace-index-tools.md` completed (frontier/citation-graph/ledger/refs-bib)
>   and `memory-routing` gained `card-lint`; presentation/PDF flow SSOT =
>   `latex-and-blueprint.md`.
> - **P3**: `memory.py refresh --check` staleness probe + `memory/index.md`
>   freshness hint + `.longterm_read.json` read trace.
> - **P4**: `gate.py complete` index-freshness check (hard error when an index
>   exists and is stale) + long-term-read check (warning); inv.12/16 clarification;
>   soft holdouts (`nl-prover/SKILL.md`, `query-workflow.md`, `ADR 0012`) aligned to
>   required.
> - **P5**: the `.codex/agents/*.toml` forbidden-action paragraphs slimmed to a
>   pointer at each prompt + `workspace-and-ownership.md` (Verifier's substantive
>   paragraph left intact).
> - **Tests**: +11 in `tests/harness_tools/test_index_freshness.py`; full suite 153
>   green; all five facades load; `memory.py refresh --check` reachable.
>
> The current-state review below records the **pre-implementation** state; its body
> line numbers reflect that state and have since shifted.

> **Current-state review (as of 2026-07-23; all line numbers re-checked against the
> current repository).** This ADR was drafted before the cli_tools facade reorg and
> before ADRs 0018/0019 landed; many line numbers and phrasings had drifted. This
> block records the review conclusions; body line numbers have been updated in place.
>
> - **All tool names are now the five facades** (`memory / search / external / gate /
>   workspace`). The originally-named `workspace_memory.py`, `query_index.py`,
>   `presentation_index.py`, `reference_extract.py` **no longer exist as model-facing
>   tools**; they are folded into internal packages under the facades. The facades now
>   also carry 4 non-index subcommands: `search.py {frontier, citation-graph}` (ADR
>   0018) and `workspace.py {ledger, refs-bib}` (ADR 0019).
> - **The original "root cause 2: allowlist omits the 4 index tools" is resolved by the
>   facade reorg** (`.codex/rules/default.rules` L24-28 are now five facade rules; all
>   index capabilities live under a facade). This ADR no longer lists it as an open
>   problem, only as historical cause.
> - **Part of Section B already landed in AGENTS.md (important — it reframes B).**
>   `AGENTS.md` Routing Loop step 1 (L102-116) was rewritten: reading the resident
>   long-term memory (`memory.py read --tier long-term --view compact`) is now a
>   **hard precondition — never skip it** (L107-109), and "refresh the mechanical
>   indexes each round" is **required** (L104-106). `orchestrator-cookbook.md` L13-22
>   and `workspace-index-tools.md` L56-58 are aligned to the same hard tone. **But this
>   is still prompt discipline only, with no mechanical gate** (skipping neither fails
>   nor leaves a trace). So B's state is: **B.4 "tone unification" is mostly landed**,
>   leaving only a few soft holdouts and the orchestration.md omission; **B.2/B.3
>   "stale detection + mechanical gate" is untouched** and remains this ADR's core work.
> - **ADR 0018's new artifacts** (`knowledge/{findings,map,leads}.md`,
>   `knowledge/frontier.jsonl`) and new subcommands (`search.py frontier`,
>   `search.py citation-graph`) **are still absent from every ownership table and index
>   scope** (grep finds them only in the `AGENTS.md:157` tool list, not an ownership
>   row). They must be added to the ownership table and index scope.
> - **ADR 0019's new artifacts and tools** (implemented): the provenance ledger
>   `references/ledger.jsonl` (Searcher writes provenance, a fresh Verifier writes
>   trust), `references/refs.bib` (generated by `workspace.py refs-bib`), and the new
>   subcommands `workspace.py {ledger,refs-bib}`, `gate.py {proof-attempt --ledger,
>   citation-audit}`. Ownership table, five-facade list, and index scope all need these
>   added; the ledger sits under `references/`, naturally inside `workspace.py
>   references`' scan scope.
> - **A newly-found SSOT correctness bug in the review**: `AGENTS.md` invariant 2
>   (L38-39) lists roles as "Generator, **Refiner, Refiner**, Explorer…" — `Refiner`
>   duplicated, and the list is not aligned with invariant 1. This is P1 "conflict-level
>   inconsistency" because the invariants are the core SSOT.

This addresses two user-reported problems: **(A) the harness has a large amount of
duplicated content**; **(B) Codex often fails to use the mechanical indexes correctly.**
These share a root cause and are handled in one ADR.

## Background

### Symptom 1: indexes are not adopted (observed, each with a location)

All four index capabilities can only be **run manually** — no scheduler, no hook, no
auto-trigger (names are the post-facade current names; the original name is in parens):

- `memory.py refresh` / `memory.py read --tier local` (former `workspace_memory.py`):
  glob-scans to produce `memory/index.md`/`index.json`, channels `branch_states /
  failed_paths / verification_reports / source_findings / presentation / latest`;
  anything the glob misses must be added manually with `memory.py append`.
- `search.py index` (former `query_index.py`): `summarize/refresh/latest`, writes
  `queries/<id>/index.*` and top-level `queries/index.*`, and appends findings into
  `memory/source_findings.jsonl`.
- `workspace.py presentation` (former `presentation_index.py`):
  `build/show/latest/sync-static`, writes `presentation/index.*`.
- `workspace.py references` (former `reference_extract.py`): `scan/extract/show/search`,
  writes `references/index.*`; it is **the only tool with a `stale` freshness field**
  (`_workspace/references.py`'s `file_record` computes it and writes it into
  `index.json/md`), but that field **is consumed by no one and blocks nothing**.

> **Review: are all current tools correctly "indexed" into prompts/skills (answering an
> annotation).** A full scan of `prompts/`, `prompts/references/`, `.agents/skills/`,
> `AGENTS.md`, `.codex/agents/*.toml`, `.codex/rules/default.rules` finds it **mostly
> clean**: **no** stale old tool name is used as a callable command
> (`workspace_memory.py`/`query_index.py`/`presentation_index.py`/`reference_extract.py`/
> `gemini_verify.py`… are all migrated to the five facades; even a "(former X.py)"
> parenthetical appears only inside this ADR); **no** subcommand is attributed to the
> wrong facade; **no** bare `python`/`python3` (all `uv run python`). **The one real
> gap**: `.agents/skills/nl-prover/references/workspace-index-tools.md` enumerates
> subcommands **stale/incompletely** — `workspace.py` lists only `references`/
> `presentation` (missing `ledger`/`refs-bib`), `search.py` lists only `index` (missing
> `frontier`/`citation-graph`), inconsistent with the fully-updated `AGENTS.md`
> (L150-163) / `orchestration.md` (L205-228). **And per the Section-A table this file is
> exactly the SSOT for "tool-invocation examples (index)" — so it must be completed
> before consolidation**, otherwise the incomplete subcommand set gets frozen as
> authoritative. One soft gap too: `memory-routing/SKILL.md` mentions the memory
> subcommands in prose but never `card-lint`. Both are fixed in P2.

After ADR 0018 landed there is another layer of artifacts no index covers:
`knowledge/{findings,map,leads}.md` (defined at `prompts/searcher.md:116,122,127`) and
`knowledge/frontier.jsonl` (`search.py frontier`, searcher.md:81-85 and the search
skill). The first three are digested material downstream reads by trigger; the last is
deep-search frontier state (`search.py frontier status` has its own budget view).
**Neither is in** the `workspace-and-ownership.md` / `artifact-ownership.md` ownership
tables. Both the ownership table and the index scope must be extended to cover them.

After ADR 0019 landed there are two more artifacts under `references/`: the provenance
ledger `references/ledger.jsonl` and the generated `references/refs.bib`. The ledger is
itself a mechanical index (`workspace.py ledger status`/`validate` have their own view)
and already sits inside `workspace.py references`' scan directory; the ownership table
must record its **dual owner** (provenance fields = Searcher, trust field = fresh
Verifier, `cite_key` = mechanically generated by `refs-bib`) so it is not mistaken for a
single-owner artifact.

Root-cause clues (mechanical, not just "the agent won't listen"):

1. **No pre-dispatch gate.** The only mechanical gate `gate.py complete`
   (`_gate/completion.py`'s `lint_workspace`, L368-418) runs only **at the end**: it
   checks proof markers, STATUS phase/obligation/lemma rows, review-packet lint,
   result-contract, proof-review, candidate aggregation (ADR 0016), but **checks nothing
   about whether any index exists / is refreshed / is stale, and does not check whether
   long-term memory was read** (B.0). There is no gate before dispatch. Invariant 12 even
   actively states "there is no structural pre-check gate" (`AGENTS.md` L64-65), which
   conflicts with the goal "read the index before dispatch".
2. **~~Allowlist omission~~ (historical cause, resolved).** The former
   `.codex/rules/default.rules` allowlisted the query/verify tools but **omitted all 4
   index tools**, so "refresh the index every round" was a more expensive path at the
   execution layer than allowlisted tools (potential approval friction) — the
   implementation contradicted the instruction's intent. That was the most concrete
   mechanical root cause of low adoption.

   **Review: resolved by the facade reorg.** The allowlist is now **five facade rules**
   (`.codex/rules/default.rules` L24-28: `memory.py / search.py / external.py / gate.py /
   workspace.py`), and all index capabilities live under those five facades, so **index
   operations are now all inside the allowlist**, at execution cost on par with other
   tools. This ADR no longer lists it as an open item; B's original "remove friction"
   step is dropped accordingly.

   *Worth keeping on record*: this root cause was not "the agent won't listen" but **an
   instruction-required action being set as the more expensive path at the execution
   layer**. Any future "must do every round" action should first be confirmed inside the
   allowlist.
3. **Inconsistent and scattered instruction tone (partly fixed).** The same requirement:
   at `AGENTS.md` L104-109 ("required" + "hard precondition — never skip it"),
   `orchestrator-cookbook.md` L13-22, `workspace-index-tools.md` L56-58 it is already
   **hard** (these three were unified when part of B landed early); but soft/contextual
   holdouts remain — `SKILL.md` L20 (only "when the workspace is large"),
   `query-workflow.md` L69 ("may run"), `ADR 0012` L186 ("should call"). And the
   Orchestrator's core routing file `prompts/orchestration.md`'s routing sections (Core
   Contract / Hard Routing Principles L26-77, Mandatory Specialist Triggers L79-99)
   **do not mention this step at all**, listing the tool name only in the Tool Index
   (L209-211). An agent following orchestration.md primarily will inevitably miss it.
4. **No staleness feedback loop.** Except for references, the other three index.md write
   only record counts, not "has it been refreshed since the last STATUS.md change". An
   agent reading a stale index has no way to notice.
5. **Reading the index is not a verifiable precondition of dispatch.** Routing step 2
   (dispatch) does not depend on step 1's product; the agent can scan the workspace files
   directly and get the same result, so the index layer is seen as skippable duplicate
   labor. (Step 1 is now declared required, but lacking the mechanical signals of points
   3 and 4, whether it was actually done cannot be verified.)

**The real motivation is token economy, not just "discipline".** The mechanical indexes
(`memory/index.md`, `queries/index.md`, `references/index.md`, etc.) are **compressed
summaries** of workspace state; having the agent read the index first and expand on
demand saves a large amount of tokens versus full-scanning the whole workspace directory
each round. The cost of non-adoption is not "non-compliance" but **paying for an
avoidable full scan every single round**. Section B's gating is worth it precisely
because it locks in that recurring saving — this is the core reason for this ADR's
priority.

### Symptom 2: harness content duplication (observed, with locations)

Investigation found heavy cross-file duplication (some of it conflict-level inconsistency):

- **Delegation-triggers table** duplicated in three places: `AGENTS.md` L89-100 (header
  L85), `orchestration.md` L88-99 (header "Mandatory Specialist Triggers" L79),
  `subagent-dispatch-cookbook.md` L6-19, with wording drift ("Route unclear or repeated
  strategic failure" vs "route unclear, repeated strategy failure, or no generator-ready
  DAG" vs "No generator-ready DAG, route unclear, or repeated strategy failure").
- **Routing loop** in two places: `AGENTS.md` L102-135 (now 10 steps, extended) and
  `orchestrator-cookbook.md` L9-43, with command lines (memory.py read/refresh/append)
  duplicated verbatim. **But the problem here is not just duplication — it is a
  qualitative error**: writing it as a numbered 10-step "loop/pipeline" **contradicts**
  `orchestration.md` L26-37 "Core Contract"'s own declaration that the "Orchestrator is
  not required to follow a fixed proof pipeline … routing autonomy only". The correct
  framing is that it is an **advisory reference/cookbook** ("how it usually goes"),
  **not** a hard loop the Orchestrator must follow each round; the Orchestrator should be
  fairly free to dispatch subagents by current blocker. **The only hard constraints are a
  few "preconditions"** (read long-term memory each round, single-pass verification, PASS
  before merge, pop the next branch on failure), **not the ordering of steps**. The SSOT
  decision adjusts this row accordingly (see the Section-A "routing loop" row and dedup
  action 7).
- **Core invariants** are restated in prose in multiple cookbook/orchestration spots
  (single-pass verification, PASS scope, mechanical ≠ mathematical, specialists are
  irreplaceable, one failure is not exhaustion — 3~4 spots each).
- **Artifact-ownership table** in three places and **mutually inconsistent**:
  `workspace-and-ownership.md` L26-58 (full directory + owner), `artifact-ownership.md`
  L6-40 (a subset, with several owner attributions differing), `AGENTS.md` inv.14
  blacklist L69-73 (lists only Orchestrator forbidden-write paths, not a full table). The
  per-row differences between the first two are in the comparison table under
  "conflict-level inconsistency" item 3 below.
- **Stop conditions** in three-to-four places: `stop-conditions.md` (whole file L1-57),
  `AGENTS.md` L134-135 (routing step 10 stop clause), `orchestration.md` L137-159 (Result
  Contract / When stuck), `branch-queue-cookbook.md` L51-63 (Exhaustion Standard).
- **Tool list / invocation examples** in multiple places: `orchestration.md` L203-237
  (facade bullets L209-228), `workspace-index-tools.md` (whole file), `AGENTS.md`
  L148-184 (facade list L150-163), `verification-gates.md` L9-39, `query-workflow.md`
  L65-76.
- **AGENTS.md and orchestration.md overlap ~50-60% overall** (revised down from the
  original 60-70% estimate): overlapping sections are the delegation-triggers table, the
  five-facade tool list, the prose restatement of invariants (orchestration's "Hard
  Routing Principles"), and stop/Result-Contract language; orchestration.md-only sections
  are the Reference Map, the Active Branch Queue template, Failure Classes, and the
  Presentation layer.

**Conflict-level inconsistencies that must be resolved before any merge:**

1. **`collector.md` vs `collector_result.md`**: `collector.md` is used at `collector.md:12`,
   `sketcher.md:130/151/184/342`, `workspace-and-ownership.md:47`, `query-workflow.md:51/61`,
   `verifier.md:118/282/366`, `knowledge/SKILL.md:20`; `collector_result.md` is used at
   `artifact-ownership.md:30`, `subagent-dispatch-cookbook.md:15`. **The same Collector
   output file is called by two names. Decision: unify to `collector.md`, deprecate
   `collector_result.md`** (only `artifact-ownership.md:30`, `subagent-dispatch-cookbook.md:15`
   need changing).

   > **What Collector does now** (per `prompts/collector.md`): it is a **read-only
   > knowledge-base query** subagent — it reads the local wiki pages under
   > `{data_dir}/wiki/` (and an optional Collector directory), answers one focused query
   > with **a source audit**, and writes to `queries/<id>/collector.md`. It **does not run
   > `claude`/any external LLM, does not modify the wiki, does not write outside the
   > workspace, and makes no mathematical judgment**. That is: "find the relevant local-KB
   > entries and land a citable answer" — a pure retrieval/summary role. (Distinguish it
   > from the `/home/cyc/Collector` **repository**, which only does mechanical
   > dedup/format/human-acknowledged ingest and has no content-audit agent; the Collector
   > here is the NL-Prover subagent that queries the local KB.)
2. **`Code Executor` vs `CodeExecutor`**: spaced `Code Executor` at `AGENTS.md:36/39/96`,
   `SKILL.md:29`, `artifact-ownership.md:25`, `workspace-and-ownership.md:39`,
   `subagent-dispatch-cookbook.md:17`, `code_executor.md:1`, `code-executor.toml:2/4`;
   unspaced `CodeExecutor` at `orchestration.md:95`, `synthesizer.md:58`,
   `code-executor.toml:13` (as `nickname_candidates`). **Decision: unify the prose/display
   name to the spaced `Code Executor`** (only `orchestration.md:95`, `synthesizer.md:58`
   need changing). **Identifiers stay unchanged** — agent id / TOML `name` = `code-executor`
   (hyphen), prompt file = `prompts/code_executor.md` (underscore), `nickname_candidates =
   ["CodeExecutor"]` (unspaced) are all **identifiers**, unaffected by the spaced display
   name, and need not and should not change.
3. **The two owner tables have different entry sets** (differing in both directions).
   Per-row comparison (W&O = `workspace-and-ownership.md`, AO = `artifact-ownership.md`):

   | Artifact | W&O | AO | Difference |
   |----------|-----|----|-----------| 
   | `recovery/route_history.md` | Orchestrator or Regulator | — (absent) | W&O only |
   | `recovery/regulator_decision_*.md` | — (folded into recovery/route_history) | Regulator | AO only |
   | `sketch/target_contract*.md` | Sketcher | Sketcher or target-reading workflow | owner attribution differs |
   | `sketch/revision_*.md` | Sketcher | Sketcher or Refiner | owner attribution differs |
   | `sketch/plan_refinement.md`, `decomposition_refined.md`, `refined_lemmas/*` | Refiner | — (absent) | W&O only |
   | `sketch/*_report.md`, `*_review_packet.md`, `*_verdict.md` | Verifier | — (absent) | W&O only |
   | `lemmas/<id>/statement.md` | Sketcher or selected refined plan | Sketcher | owner attribution differs |
   | `refinement/original_*` | Orchestrator | — (absent) | W&O only |
   | `refinement/proof_refinement.md`, `decomposition_refined.md` | Refiner | — (AO lists only `proof_refined.tex`) | W&O only |
   | `refinement/verdict.md` | Verifier | — (AO lists only `verifier_*`, `review_packet.md`) | W&O only |
   | Collector output | `collector.md` | `collector_result.md` | naming conflict (see item 1) |

   **Merge direction**: base on W&O (most complete directory coverage), but absorb AO's
   **finer owner attributions** — `target_contract*` = "Sketcher or target-reading
   workflow", `revision_*` = "Sketcher or Refiner", `statement.md` = "Sketcher or selected
   refined plan" — and add AO's unique `recovery/regulator_decision_*.md` = Regulator.
   After merging, AO drops its table and becomes a pointer.
4. **The same delegation-trigger row is worded three different ways**: e.g. the
   finite-computation row — `AGENTS.md:96` "Finite enumeration, computation, or exhaustive
   case evidence is load-bearing | Code Executor, then Verifier"; `orchestration.md:95`
   "finite enumeration, exhaustive check, or computation evidence is load-bearing |
   CodeExecutor, then Verifier"; `subagent-dispatch-cookbook.md:17` "Finite enumeration,
   exhaustive check, or computation evidence is load-bearing | Code Executor". Three
   wordings (plus the Code Executor/CodeExecutor split). Unify the display name per item 2
   and the wording per the SSOT (`subagent-dispatch-cookbook.md`).

   > **Verifying "Code Executor is really a Computation Auditor" (answering an
   > annotation).** True: although `prompts/code_executor.md` is titled "Code Executor
   > Agent", its body is a pure **computation audit** — output template `# Computation
   > Audit`, terminal marker `COMPUTATION_AUDITOR_DONE`, verdict `PASS_AUDIT`, and its
   > first line reads "You audit finite cases … You do not use black-box computation as a
   > substitute for proof". It **audits computation evidence produced by others; it does
   > not actually run code**. Name/reality mismatch: it is a Computation Auditor, not a
   > code-running Executor.
   >
   > **Search result in `/home/cyc/RamanujanChallenge`**: across all 6 workspaces (2_2 /
   > 2_4 / 2_6 / 2_7 / 2_8 / 3_2), old dirs, and the tarball, **no self-authored standalone
   > "executor prompt" file was found**; there are only many `routes/computation_audit_*.md`
   > (outputs of the current audit role) and real compute directories (e.g.
   > `2_4/compute/rc24-certificate/`, `2_7/…/solver_ore_algebra…/pyproject.toml`). That is,
   > in practice **the heavy lifting was run by ad-hoc compute environments set up inside a
   > workspace, not via a harness "executor" agent** — which conversely confirms "a real
   > code-execution role is missing". (If you recall that prompt being elsewhere or deleted,
   > tell me the path and I'll look again.)
   >
   > **Recommendation on the subagent set (this ADR does not directly edit the prompt, only
   > assesses)**: keep an open question **Q4** — whether to **split this into two roles**:
   > (a) a **Code Executor** that actually runs code/CAS (producing scripts, tables,
   > reproducible results), and (b) the existing **Computation Auditor** (auditing
   > exhaustiveness and conclusion mapping, `PASS_AUDIT`). These are the distinct
   > "execution" and "audit" responsibilities, now crammed into one misnamed agent; and per
   > inv.2 the executor's product must go to an independent audit/Verifier, not self-certify.
   > See "Risks and open questions Q4".
5. **A bug in the invariant SSOT itself (newly found)**: `AGENTS.md` invariant 2 (L38-39)
   lists roles as "Generator, **Refiner, Refiner**, Explorer, Synthesizer, CE-Hunter,
   Searcher, Auditor, Code Executor, Collector, and Writer" — `Refiner` is duplicated.
   Since the invariants are the core SSOT, this must be fixed in P1. **Fix**: drop the
   duplicate `Refiner`; inv.2's "must never spawn a Verifier / other subagent" list should
   be `Generator, Refiner, Explorer, Synthesizer, CE-Hunter, Searcher, Auditor, Code
   Executor, Collector, Writer`. Note that inv.2 and inv.1 (L33-37, the roles the
   Orchestrator must not act as) **should not be identical**: inv.1 additionally has
   `Sketcher / Verifier / Regulator` (Verifier is fresh/stateless with its own constraint;
   Sketcher/Regulator's spawn rules are covered by the hub-and-spoke general rule). Make
   this explicit in P1 so it is not "aligned to be identical" next time.

### Causal link (why merge into one ADR)

Duplication → no single authority → agents each read a different copy and are lost when
wording drifts → cross-file-but-not-output-critical steps like "refresh and read the
index" are the easiest to skip. **Deduplication (establishing a single source of truth)
is the precondition for stable index adoption**; the two are two faces of the same
governance problem.

## Decision

### Section A: Single Source of Truth (SSOT) and deduplication

**Principle: every file is either the sole authoritative source (SSOT) for a class of
content, or a pointer to that source; there must be no "second full copy worded
differently".**

SSOT placement table:

| Content class | Authoritative source (SSOT) | Everywhere else becomes |
|---------------|-----------------------------|-------------------------|
| Core invariants | `AGENTS.md ## Core Invariants` (numbered hard constraints) | cite the invariant number |
| Delegation-triggers table | `subagent-dispatch-cookbook.md` (5-column, most complete, with output paths) | a one-line pointer |
| Routing loop (**framed as advisory reference, not a hard loop**) | `orchestrator-cookbook.md` (advisory operating guide, with command-line examples) | AGENTS.md keeps only the **hard preconditions** (read long-term memory, single-pass verification, PASS before merge, pop on failure), dropping the "must run 1→10 in order" implication |
| Artifact ownership | `prompts/references/workspace-and-ownership.md` (most complete directory + owner) | artifact-ownership.md drops its table for a pointer; AGENTS inv.14 blacklist stays but notes "full table here" |
| Stop / exhaustion | `stop-conditions.md` + `branch-queue-cookbook.md` (exhaustion standard) | orchestration.md shrinks to a pointer |
| Tool-invocation examples | `workspace-index-tools.md` (index) + `verification-gates.md` (lint/gate) | others drop the commands, keep the tool names |
| Deep-search artifacts & frontier | `prompts/searcher.md` + `search` skill (ADR 0018) | ownership table adds `knowledge/{findings,map,leads}.md`, `knowledge/frontier.jsonl` with owner=Searcher |
| Provenance ledger & citation (ADR 0019) | `prompts/searcher.md` (provenance) + `prompts/verifier.md` (trust) + `article-writing` (citation) | ownership table adds `references/ledger.jsonl` (dual owner: Searcher provenance / Verifier trust), `references/refs.bib` (mechanical = `refs-bib`); five-facade list adds `workspace.py {ledger,refs-bib}`, `gate.py {proof-attempt --ledger, citation-audit}` |
| Pointer master table | `orchestration.md ## Reference Map` | orchestration.md converges to pure pointers |

Dedup actions (by priority):

1. **Fix conflict-level inconsistencies first** (correctness first; must precede any
   merge): unify `collector.md` (deprecate `collector_result.md`, at `artifact-ownership.md:30`,
   `subagent-dispatch-cookbook.md:15`); unify display name `Code Executor` (id
   `code-executor`, nickname `CodeExecutor`; change `orchestration.md:95`,
   `synthesizer.md:58`); unify the two owner tables' entry sets; unify the delegation-trigger
   wording; **fix `AGENTS.md` invariant 2's `Refiner, Refiner` duplication and align with
   invariant 1's list**.
2. **Merge the owner table** → `workspace-and-ownership.md` (adding the ADR 0018/0019 new
   artifact rows); `artifact-ownership.md` drops its table for a pointer; `AGENTS.md` inv.14
   blacklist stays but notes "full owner table in workspace-and-ownership.md".
3. **Merge the delegation-triggers table** → `subagent-dispatch-cookbook.md`; `AGENTS.md`
   and `orchestration.md` shrink to a one-line pointer.
4. **`orchestration.md` converges to a pure Reference Map**: keep `## Reference Map`,
   `## Failure Classes`, the `## Active Branch Queue` template, and the presentation-pdf
   naming details; delete the prose restatement of invariants/triggers/stop/tools, pointing
   to AGENTS.md and the cookbooks instead. **And at the routing pointer add the pointer to
   "read long-term memory + refresh index each round"** (removing the core-file omission and
   aligning B.4). Return it to the "operational index" role it claims at L1-4, rather than a
   second AGENTS.md.
5. **Presentation/pdf export rules** merged from three places into one (suggested:
   `latex-and-blueprint.md`, which already has the pdf export command).
6. **The `.codex/agents/*.toml` developer_instructions' 3rd-paragraph prohibitions** slim
   to "obey the owner/forbidden-action constraints declared in the prompt", keeping the SSOT
   of specific forbidden-write paths in the prompt + workspace-and-ownership.md; if kept as
   safety redundancy, mark clearly in-file "this mirrors the prompt; changes must be synced
   in both places".
7. **Reframe the routing loop as advisory reference** (following the qualitative issue in
   Symptom 2): change `orchestrator-cookbook.md`'s "Operating Loop" wording to an advisory
   operating guide ("typical order, not mandatory"); `AGENTS.md`'s "Routing Loop" keeps only
   the **hard preconditions** (read long-term memory, single-pass verification, PASS before
   merge, pop the next branch on failure), dropping the "must execute 1→10 in order"
   implication and making explicit that the Orchestrator retains the routing autonomy
   declared in `orchestration.md`'s Core Contract.

### Section B: enforce index adoption (mechanical gate + feedback loop)

Turn "refresh and read the index" from a soft suggestion into a **hard precondition with a
feedback loop**. **Note: B's "declared required" half already landed early** (see the
current-state review); the remaining core of this section is **stale detection + mechanical
gate + completion check**.

**B.0 takes over ADR 0016's unclosed precondition (the primary target of this section).**
ADR 0016 made "read the resident long-term memory" (`memory.py read --tier long-term`) a
**hard precondition** of `AGENTS.md` Routing Loop step 1 (L107-109, wording "This is a hard
precondition — never skip it."). But **it currently has only prompt discipline, no
mechanical gate**: skipping it fails no check and leaves no trace. This is isomorphic to
Symptom 2 — an action declared "must" with no verifiable signal at the execution layer. This
ADR's stale/pre-gate design **must cover this too**, or 0016's memory stratification may spin
idle in real runs. (ADR 0016 hangs this closure on this ADR in **§3.3 (L260-272) and §4
"Relationship to existing ADRs" (L491-493)** — not the originally-miswritten §3.5, which is
the deferred distillation lifecycle.)

1. ~~**Remove friction**~~: **done by the facade reorg** (the allowlist is now five facade
   rules; index operations are all inside). The original "add the 4 index tools to the
   allowlist" is no longer needed.
2. **Stale detection (core, untouched)**: add a freshness judgment to `memory.py refresh` —
   compare `memory/index.json`'s `generated_at_utc` against the mtime of `STATUS.md` (and key
   artifacts); when stale, `memory.py refresh --check` exits non-zero and `memory/index.md`
   shows at the top "whether it has been refreshed against the latest STATUS". Make "the index
   is refreshed" a verifiable mechanical signal. The same mechanism can give B.0 a trace of
   "was long-term memory read this round" (e.g. drop a read timestamp at refresh time).
3. **Gate placement (untouched)**:
   - Completion: `gate.py complete` adds an "index not stale" check and a "long-term memory
     read" check.
   - Pre-dispatch: see open question Q1 (Codex has no hook mechanism; enforcement means are
     limited).
4. **Tone unification (partly landed)**: standardize on `AGENTS.md` L104-109's "required /
   hard precondition". **Already aligned**: `orchestrator-cookbook.md` L13-22,
   `workspace-index-tools.md` L56-58. **To align**: the soft holdouts `SKILL.md` L20,
   `query-workflow.md` L69, `ADR 0012` L186; and add to `orchestration.md`'s routing section
   the pointer to "refresh + read the index first each round" (that file currently lists the
   tool name only in the Tool Index, with nothing in the routing section — same action as
   A.4).
5. **Feedback loop (untouched)**: the stale warning prompts the agent to re-run, rather than
   reading a stale index unaware.

**Tension clarification with invariant 12 (important)**: inv.12 "no structural pre-check gate"
(`AGENTS.md` L64-65) targets **mathematical** pre-checks (preventing a mechanical gate from
masquerading as mathematical verification); inv.16 also already states "mechanical checks ≠
mathematical verification". Index freshness is a **mechanical/process** gate, not a
mathematical pre-check. Add a clarification to `AGENTS.md`: **"Mechanical process gating (such
as index freshness) is permitted as a dispatch precondition; it does not constitute, and does
not replace, mathematical pre-checking."**

## Non-goals

- Do not change hub-and-spoke, do not change single-pass mathematical verification, do not
  change the mathematical constraints of the core invariants.
- Do not introduce a scheduler / resident process to auto-refresh indexes (keep CLI + agent
  triggering; only add the stale gate + completion check).
- Do not add a second authoritative document; this ADR's product is "less documentation", not
  more.

## Phased plan (after approval)

- **P1 fix conflicts**: `collector.md` naming, `Code Executor` naming, unify the two owner
  tables' entries, unify delegation-trigger wording, **`AGENTS.md` invariant 2's
  `Refiner, Refiner` duplication**. *(correctness first)*
- **P2 SSOT dedup**: first complete `workspace-index-tools.md`'s `workspace.py`/`search.py`
  subcommand sets (+ `memory-routing/SKILL.md` add `card-lint`) then make it the SSOT; merge
  the owner table (adding the 0018/0019 new artifact rows), merge the delegation-triggers
  table, converge `orchestration.md` to a Reference Map (adding the routing pointer), reframe
  the routing loop as advisory (dedup action 7), merge the presentation rules.
  *(prompts/skills/AGENTS)*
- **P3 stale detection**: `memory.py refresh --check` stale judgment + `memory/index.md`
  freshness annotation + long-term-memory read trace (B.0). *(cli_tools)* (the original "add
  the 4 index tools to the allowlist" is done by the facade reorg, dropped.)
- **P4 gate + tone unification**: `gate.py complete` adds the index-freshness check and the
  "long-term memory read" check; `AGENTS.md` clarifies inv.12/16; align the soft holdouts
  (`SKILL.md` L20, `query-workflow.md` L69, `ADR 0012` L186) and `orchestration.md`'s routing
  omission to required. *(cli_tools/prompts)*
- **P5 toml prohibition slimming**. *(.codex/agents)*

## Risks and open questions

- **R1 over-gating**: too strict a stale gate slows things down. Mitigation: require it only
  on "non-trivial cycles"; stale is warn-only normally, hard-checked only at completion.
- **R2 pointer mismatch during migration**: links may break during the SSOT migration.
  Mitigation: migrate in one pass + run a link-resolution check afterward (like the prompt-path
  resolution check done on previous ADR commits).
- **Q1 (key) who enforces the pre-dispatch gate?** Codex has no hook mechanism
  (`.codex/config.toml` has only `max_threads = 6`/`max_depth = 1`, no hook field). So "must
  have refreshed / read long-term memory before dispatch" is hard to truly mechanically
  enforce; the options are probably only: (a) `gate.py complete` completion check + (b)
  instruction `required` (partly landed) + (c) a light wrapper script around dispatch.
  **Whether it can truly be "enforced" depends on this — please set the direction.** Note this
  now also **decides B.0** (whether ADR 0016's "must read long-term memory" can truly close) —
  they are the same mechanism problem, solved once for both.
- **Q2** Agree to loosen the wording in `AGENTS.md` to explicitly permit "mechanical process
  gating" as a dispatch precondition (coexisting with inv.12)?
- **Q3** Which artifacts' mtime does the stale baseline compare against — only `STATUS.md`, or
  `routes/`, `recovery/`, review packets all? Wider is more accurate but fires stale more often.
- **Q4 (executor / auditor split)** see Symptom 2 conflict item 4: the current `code-executor`
  is a name/reality mismatch (really a Computation Auditor, does not run code), and the real
  heavy lifting is run in ad-hoc environments inside a workspace. Split it into **two
  subagents** — a "Code Executor that actually runs code/CAS" (producing scripts/tables/
  reproducible results) + a "Computation Auditor" (auditing exhaustiveness and conclusion
  mapping)? If split: a code-running agent definition and prompt must be added, and its product
  must go to the Computation Auditor / Verifier for audit (per inv.2, no self-certification).
  **This ADR only records the assessment, it does not directly edit the prompt** (per the
  annotation); whether to include it in implementation, and in which P, is left to you.
