# ADR 0016: Stratified Continual Memory System (paper §2.3.2)

## Status

Accepted — **implemented** (see §6 for the phase-by-phase status). This ADR
specifies the target memory architecture for NL-Prover and how it maps to the
MechMath Agent Team paper's Augmentation Plane (§2.3.2 stratified continual
memory), Control Plane state (§2.1), and Knowledge Base Manager (§3.3).

> **Implementation status.** P0, Phase 1 (positioning + `index.md` renders all
> channels), Phase 1.5 (`memory-routing` skill), Phase 2 (`memory.py
> render-longterm` + the hard-precondition cycle-start read wired into
> `AGENTS.md`), Phase 3 (unified `cli_tools/memory.py` over the internal
> `cli_tools/_memory/` package, allowlist + prompts),
> Phase 3.5 (candidate-card aggregation gate in `completion_gate.py`), and Phase
> 5 (`experience_card_lint.py`) are implemented and tested. **Deferred as the ADR
> intends:** Phase 4 distillation (§3.5), and the optional `notation`/`readings`
> local channel (Phase 1). **Pending human action:** running the one-time
> `memory.md → Experience_*` migration on the live KB (`migrate_memory_md.py
> --apply`); the tool is delivered and tested but not applied, to avoid mutating
> the external KB and reformatting the curated `memory.md` without a human go.

> **Naming (throughout):** the paper's "external knowledge base" = this repo's
> **KB-Manager** (formerly *Collector*; the code tools are still named
> `collector_write.py` / `collector_summary.py`, wiki lives at `DATA_DIR/wiki/`).
>
> **Relationship to ADR 0017 (settled):** the final division of labor is
> **"full content lives in the KB, the recall index lives in `memory.md`"**:
> each long-term card's full body is stored once in the KB (read on demand),
> while recall of long-term negative constraints goes through a local resident
> `memory.md` index (a read-only projection of KB content) loaded as a hard
> precondition — **recall never goes through a KB pull** (rationale in §3.3).
> ADR 0017 has been narrowed to own only the KB card-family/schema question; the
> two ADRs are consistent with no residual conflict.

## 1. What the paper actually specifies

Paper §2.3.2 defines memory as a **tripartite, stratified** structure, split by
*scope* and *cognitive density*, so the active context is never clogged by
"transient noise or heavy data load":

| Tier | Scope | Content (paper examples + repo additions) | Lifecycle | Repo mapping |
|------|-------|-------------------------------------------|-----------|--------------|
| **Local memory** | within a session | temporary notation conventions; **plus "what each step of this workspace did, which routes were explored, which died"** | paper: dies with the session | existing **short-term memory** `workspace_memory.py` (lifecycle adjusted in §3.2) |
| **Long-term memory** | across sessions | abstract, highly distilled **strategic boundaries / heuristic thresholds**, as **negative constraints** ("don't make this mistake") | persistent, compact, **loaded at startup** | **resident compact list** (upgraded `memory.md`); **not folded into KB pull**, see §3.3 |
| **Knowledge base (external)** | across sessions | **dense domain facts**; **plus: audited literature results, self-produced verify results** | persistent, heavy, off-context | **KB-Manager** (`DATA_DIR/wiki/`) |

Two load-bearing principles from the same section:

- **P1 — memory distills *errors*, not success trajectories.** Long-term memory
  is biased toward **negative constraints** ("behavioral boundaries the system
  should not cross").
- **P2 — keep active memory lean; externalize heavy facts.** Dense facts live in
  the KB-Manager and are pulled on demand, never filling the context.

**Task ledger / execution graph vs workspace memory — are they duplicates?** No;
they have distinct jobs:

- The §2.1 **task ledger / execution graph** is **live runtime state**
  (ID/Task/Owner/Status, the DAG): it answers "where are we **now**, who owns it,
  what's next"; volatile, authoritative, updated every step.
- **Workspace memory** is a **read-only mechanical index/sediment of produced
  artifacts**: it answers "what has been **done / hit** so far"; non-authoritative
  (the original artifacts are authoritative).
- They do touch: the `branch_states` channel is scanned from `STATUS.md` (the
  ledger's carrier) — but that is a **read-only historical snapshot** of the
  ledger, not a second authority. The ledger owns "now", memory owns "history".
- §2.3.1 **human-in-the-loop reasoning** is a *source* of high-value negative
  constraints: what a human corrected/vetoed is first-class material for the
  long-term tier.

## 2. NL-Prover today (what exists)

| Paper tier | Existing mechanism | Gap |
|------------|--------------------|-----|
| Local (short-term memory) | `workspace_memory.py`: `refresh` mechanically globs existing artifacts into 5 channels (`branch_states`←`STATUS.md`; `failed_paths`←`recovery/*`, `routes/proof_review*`[^1]; `verification_reports`←review packets/verdicts; `source_findings`←`queries/*/*`; `presentation`←`writer/*`, `well-written-*.pdf`), writing `memory/index.md` + `index.json` | **① `index.md` renders only counts** (`build_index` puts each channel's `latest[-5:]` into `index.json`, but writes only `count` into `index.md`) ⇒ a model reading only `index.md` sees no content, i.e. "the json is built but unused"; **② not enforced** (see ADR 0020); ③ notation/definition readings have no first-class channel |
| Long-term | `memory.md` (flat, ≤100-line error *Rules* with `Why`/`Trigger`) | crude today: no `Failure modes`, no dedup, no heuristic-threshold entries; **and not designed as a "loaded-at-startup" resident tier** (§3.3) |
| KB (external, KB-Manager) | KB-Manager wiki + `collector_write.py` (writes inbox) / `collector_summary.py`; card types include `*ErrorKnowledge`, `*CounterexampleKnowledge`, `Analysis_*`, verified lemmas | no explicit boundary rule separating KB facts from long-term negative constraints (ADR 0015 "risk A"); **and `collector_write.py`'s CLI entry is currently broken** (see "Pre-implementation verification") |
| Index/injection | ADR 0012 granularity `compact → summary → full` | each tier has its own read path, not presented uniformly as "three-tier memory" (§3.7) |
| Distillation | ADR 0015: Scholar + Reflector, seed→edit→promote | Proposed only, unimplemented; **deferred by this ADR, ownership leaning to KB-Manager** (§3.5) |

[^1]: `recovery/*` = **recovery packets** written after a route stalls (restartable
    branch portfolio, next owner); `routes/proof_review*` = the **two-sided
    proof/refutation review** produced by the proof-review skill (done before
    accepting any terminal non-proof conclusion). Both fold into `failed_paths`,
    but one is "how to continue" and the other is "does this route actually hold".
    Separately, the `proof-review` skill was updated (already implemented, not just
    planned) so that a **human (professor / advisor / referee) voicing a
    mathematical opinion/doubt/objection/claim about the current proof or route is
    itself a proof-review trigger** — the opinion must be **routed, not obeyed**
    (carried into the review's refutation or proof side, recorded in provenance,
    adjudicated by a fresh Verifier / Regulator; paper §2.3.1 human-in-the-loop).
    **The opinion is a routing signal only and never enters the final artifact:**
    `proof.tex` must **never** contain "the professor said…" / "a referee thinks…"
    narration; it carries clean mathematics, with the opinion and its adjudication
    living in `review/proof_review.md` and provenance. (This is also written into
    the skill's Hard Stops.)

**Diagnosis.** The three tiers exist *piecemeal*; what's missing is a unified
model that (a) names the tiers and tells the model "this is three-tier memory",
(b) specifies the **dispatch rule** for which tier new knowledge enters, and
(c) defines promotion/decay (distillation deferred). The core contribution is
(a) + (b).

**Do we need a dedicated memory-management subagent?** A background, always-on
companion that monitors memory was considered. **Decision: no dedicated
subagent.** This harness is hub-and-spoke, `max_depth=1`; subagents are spawned
per task by the Orchestrator and return when done — there is no "resident
process that polls in the background" agent shape, and forcing one would break
the single-hop discipline and idle-occupy a concurrency slot. Therefore:

- **Mechanical maintenance (glob artifacts → fold into channels) is a
  deterministic script**, `workspace_memory.py refresh` (§3.2) — pure sediment,
  no judgment.
- **Aggregation/dedup ownership is the Orchestrator's.** Aggregating candidate
  cards at run-end, deduping, and folding into the inbox is **judgmental
  collation** — part of the Orchestrator's routing/collation role, not
  outsourced to a "memory script" that decides which card to keep or merge. The
  Orchestrator **may call a deterministic normalization helper** (mechanical
  pre-dedup by `(kind, normalized statement)`) **as a tool**, but the keep/merge/
  drop **decision stays with the Orchestrator**. This satisfies "owned by the
  Orchestrator" while preserving the invariant that the Orchestrator only
  routes/collates and does not judge mathematical content (deduping experience
  cards is collation, not a math judgment). No 13th agent is created (the paper's
  12 roles are unchanged).

## 3. Target design

### 3.1 Tiered dispatch rule (the single decision everything rests on)

> **Landing form: this rule is a skill.** The dispatch rule is not a paragraph
> scattered across prompts; it is a new
> `.agents/skills/memory-routing/SKILL.md` whose `description` triggers on "I
> need to record a new piece of knowledge / decide which memory tier a
> conclusion enters / write to inbox vs local vs long-term". The skill body is
> the "delete-the-object test + decision tree + notes" below, plus **the exact
> command for each exit** (`memory read/refresh`, `collector_write.py`, the
> candidate-card drop path). Any agent facing "where does this go" thus follows
> one skill and gives a consistent dispatch. **Concrete implementation plan is in
> §6.**

Classify before writing. **The "delete-the-object test" clarifies the P1/P2
boundary:** delete the problem-specific concrete objects from the candidate and
see what remains —

- What remains is essentially **a statement/object/number/theorem** (delete the
  objects and nothing is left) → **fact** (P2 → KB).
- What remains is a reusable **"how to do / how not to do / threshold
  distinction"** (still holds after deleting the objects) → **negative
  constraint / experience** (P1 → resident long-term tier).

```
Is it a concrete math fact, theorem statement, verified lemma, counterexample
instance, or dense computation result (P2)?
        └─ yes → do NOT write the KB wiki directly; write the KB-Manager inbox
                 via collector_write.py; enters wiki after human check or formal
                 (Lean) check, through ingest.
Is it valid only within the current problem (notation binding, local convention,
this workspace's exploration history)?
        └─ yes → local memory (workspace channel, §3.2). Bound to the workspace.
Is it a transferable behavioral boundary or heuristic threshold ("don't do X",
"interval A ≠ interval B"; still holds after deleting the objects) (P1)?
        └─ yes → long-term memory (resident negative-constraint list, loaded at
                 startup, §3.3). Not stuffed into KB pull.
otherwise → don't memorize (transient noise).
```

Key points:
- **Math results are never written to the wiki directly by an agent.** Always
  `inbox → human/formal check → wiki`, delegating "trust" to an explicit check.
- **Negative constraints are not stuffed into KB pull.** Rationale in §3.3
  (KB-stored constraints "aren't loaded at the start ⇒ ineffective").

### 3.2 Tier 1 — Local memory (the existing short-term memory)

**Who writes, who reads:**

- **Writing = a deterministic script, not agents writing memory directly.**
  Specialist agents only write products in **their own artifact directory**
  (review packets, `recovery/*`, `queries/*`, etc. — already their job). What
  **sediments those artifacts into memory channels** is the script
  `workspace_memory.py refresh`, which mechanically globs existing artifacts into
  the 5 jsonl channels. **No agent "writes a memory entry directly":** memory is
  always a **read-only derived index** of artifacts, so there are no phantom
  entries "in memory but with no authoritative artifact behind them". (The one
  exception is the *candidate negative-constraint card* of §3.6, an explicitly
  agent-produced artifact class — but it too lands as an artifact first, then is
  aggregated by the script/Orchestrator, never entering the long-term store
  directly.)
- **Reading = every agent (even those without write rights).** Any agent may read
  `memory/index.md` (compact) / `index.json`, or via §3.7's
  `memory read --tier local`. Reading is navigation aid; **the original artifacts
  are authoritative.**
- **Refresh trigger = the Orchestrator.** Per Routing Loop step 1, before each
  non-trivial cycle the Orchestrator runs `refresh` (and `append` for artifacts
  the glob misses). I.e. "script writes, Orchestrator triggers on schedule,
  everyone reads".

- **It is the existing `workspace_memory.py`** (jsonl channels + `index.json`/
  `index.md`); this ADR positions it explicitly as the paper's "local tier" and
  makes the tier semantics explicit to the model.
- **Content scope.** Not just notation/readings, but also **"what each step of
  this workspace did, which routes were explored, which failed and why"** — the
  existing `branch_states` / `failed_paths` channels already carry this.
- **Must be "fully used", no dead json.** Currently `index.md` writes only counts;
  the `latest` content only reaches `index.json`. Requirement: **`index.md` is
  upgraded to render each channel's `latest` summary** (the data is already in
  `index.json`, just unrendered), and **every channel is injected/reachable** —
  there must be no "jsonl generated but no read path puts it in front of the
  model". This ties to ADR 0020's "index enforcement": make the model **actually**
  use this memory rather than let the json spin idle.
- **Read/write permissions.** Write: each agent only writes its own artifact
  directory. **Read: unrestricted** — any agent may read the local memory index
  (navigation aid; original artifacts authoritative).
- **Lifecycle.** **Bound to the workspace, not cleared when a single session
  exits** — a workspace is often reused across many sessions; the memory boundary
  is the workspace, not the session. This is a deliberate adaptation of the
  paper's "local dies with the session".
- **Read path.** `workspace_memory.py refresh` → `memory/index.md` (compact),
  expandable to `summary`/`full` per ADR 0012.

### 3.3 Tier 2 — Long-term (cross-session) memory: placement analysis + resident load

**Problem:** where do long-term negative constraints live? Their value is to
**stop the model from erring from the very start** — they must "take effect
immediately, load at startup".

**Candidate analysis:**

| Option | Load timing | Problem |
|--------|-------------|---------|
| (a) stuff into KB-Manager, query on demand | pull-based — the model may not query at the start | **not loaded at the start ⇒ constraint ineffective**; a query also costs a hop |
| (b) resident compact list, injected into the initial context at startup | in-context every startup | consumes fixed context budget ⇒ must be **compact** (keep ≤100 lines + merge-first) |
| (c) hybrid: compact negative-constraint list resident + optional full card in KB as source | resident part loads at startup, full on demand | must maintain "list ↔ source" in two places, but recall does not depend on KB |

**Decision: option (c), with (b) as the backbone, in the "index/full-card split"
form:**

- **The resident index lives locally and auto-loads at startup.** The
  authoritative recall layer for long-term negative constraints = **a local
  resident compact index** (the upgraded `memory.md`, two lines per card:
  `trigger` + `statement`), loaded into context at process startup (mechanism
  below). **Recall depends on no pull.**
- **Full cards live in the KB, read on demand.** Each long-term card's `full`
  body (`why` / `failure_modes` / `provenance` / `evidence_refs`, etc.) is
  **stored in the KB-Manager**; only when a `trigger` in the index matches the
  current structure do we follow the pointer into the KB to read that full card.
- **Key distinction: the KB here carries only "on-demand read of the full card",
  never "recall".** Recall is always done by the local resident index — because
  once "should I recall this constraint" is delegated to a KB pull, we get "not
  loaded at the start ⇒ constraint ineffective". This both keeps full cards off
  the resident budget (in the KB) and keeps negative constraints effective
  immediately (index resident).

**How "load at startup" actually lands (no hooks in Codex):** Codex has **no hook
mechanism**, so we cannot rely on a process hook to auto-`cat` a file into
context. We do **not** inline the list into `AGENTS.md` (that would bloat it);
instead we **keep the existing structure — the resident negative constraints live
in `memory.md`, and agents read it**. The mechanism converges to **one hard
precondition read**:

- **Carrier = the existing `memory.md`** (its content upgraded to the compact
  `trigger + statement` list rendered from experience cards, but **file location/
  structure unchanged**; `AGENTS.md` untouched).
- **"Load at startup" = making "read `memory.md`" a hard-precondition action.**
  Tied to ADR 0020: "**at cycle start, run
  `memory read --tier long-term --view compact`** (i.e. read the `memory.md`
  compact list)" is a **hard precondition** (0020's index enforcement +
  `completion_gate` check), not a soft suggestion. This turns "read or not" into
  a **gateable mechanical fact** — the closest executable form of "auto-load"
  under hook-less Codex: not physical context injection, but a forced read at the
  start of every cycle, verified by the gate.
- **No `AGENTS.md` budget.** The resident list lives only in `memory.md`, seen via
  the mandatory-read gate; `AGENTS.md` keeps only one line: "you have long-term
  negative-constraint memory, see `memory.md`, mandatory read at the start of
  every cycle".

> **Trade-off (stated honestly):** vs "physical injection into the system
> prompt", the hard-precondition read is **not in-context at token 0**; it forces
> "read first" via the gate. The cost is one extra read action and dependence on
> the 0020 gate actually working; the benefit is `AGENTS.md` doesn't bloat,
> `memory.md`'s structure is unchanged, and the maintenance surface is small.

- Full cards live in the KB, expanded on demand (§3.6: trigger hit → follow
  pointer to the KB full card).

**Card schema (one card per file; the resident list rendered from it takes only
the two lines `trigger` + `statement`).** This is a sketch; **the authoritative
schema for the full card body stored in the KB is ADR 0017 §2** (0017 has merged
this sketch with its `Experience_*` family to avoid two formats):

```yaml
id: neg-<slug>
kind: negative-constraint | heuristic-threshold
statement: <the boundary, one line>       # "don't do X" / "interval A ≠ interval B"
why: <the failure it prevents>
trigger: <structural cue that should recall this card>   # load-bearing (recall)
failure_modes: <when this card itself misleads>          # load-bearing (honesty)
provenance: [verifier-block | human-correction | ce-hunter | regulator]
scope: <applicable domain, or "general">
evidence_refs: [<KB card ids / run ids>]   # pointers only, no heavy payload (see §3.4)
```

- `kind` covers `negative-constraint` (error boundary) and `heuristic-threshold`
  (`O(T)` vs soft-`O(T)`, a boundary not a fact).
- Compactness invariant: keep the whole store small, compress/merge near-duplicate
  cards.

**Should long-term memory be written into the KB-Manager directly?** In two
layers: **the recall layer (local resident index) is never written to the KB** —
it must be a resident file to load at startup; once "should I recall this"
depends on a KB query it becomes pull-based and violates "immediate effect".
**The full card body is written to the KB**, but the KB offers it only as an
on-demand read after a trigger hit, **not recall**. I.e. **the index owns recall
locally, the full card owns detail in the KB**, connected by pointers.

### 3.4 Tier 3 — External KB (KB-Manager)

- Dense facts, theorem packages, verified lemmas, counterexample instances,
  **audited literature results, self-produced verify results**: written to the
  **inbox** via `collector_write.py`, entering the wiki through ingest after
  **human/formal check**. **Agents do not write the wiki directly.**
- **"Long-term cards hold pointers only, never inline statements" — detailed:**
  - **Rule**: when an experience card refers to a theorem/fact, it **writes only a
    pointer** (`evidence_refs: [[Concept_FooBound]]` or `2401.12345 Thm 3.2`),
    **not the theorem statement text**.
  - **Why**: copying the statement into the card makes the same theorem **exist in
    two places** — one in the KB wiki, one in the experience card. Later the KB
    copy is revised (changed hypothesis, fixed typo) while the card's stale copy
    doesn't follow, so **the same theorem has two versions** (statement drift) and
    downstream may cite the outdated/wrong one. This is exactly ADR 0015's "risk A".
  - **How to use**: when the model finds an experience card's `trigger` relevant,
    it **follows the pointer to read the authoritative statement in the KB**; the
    card itself carries only the procedural experience of "when to recall it / when
    it misleads".
  - **In one line**: declarative facts are **authoritative only in the KB**;
    experience cards reference, never copy. This is also the precondition for the
    long-term tier to coexist safely with the KB.

### 3.5 Lifecycle: seed → edit → promote → compact → decay (**deferred, ownership leaning to KB-Manager**)

> **Status: this part is deferred by this ADR.** ADR 0015 is unimplemented;
> "distilling run experience into long-term cards" is essentially a one-shot
> run-end action whose ownership is pending (leaning to KB-Manager / or the
> `regulator`'s run-end duty). The mechanism is spelled out here for reference,
> not advanced this round.

Intended to be driven by a deterministic CLI so unchanged bytes never pass through
the model (guarding against lazy rewrites):

1. **Seed.** The tool snapshots the current long-term store into the workspace;
   the agent edits in place (only changed cards, the rest verbatim).
2. **Distill (run-end).** The distiller scans local memory + task ledger + human
   corrections, proposing candidate cards **only** for negative-constraint
   entries passing §3.1; facts go to the inbox instead.
3. **Promote.** Only files whose content actually changed are promoted; a
   pre-promote snapshot is rollback-able; **a non-empty seed returning an empty
   file is rejected** (guards against silently blanking the whole store — the
   guard that prevents a model from lazily rewriting the entire store into one
   empty/truncated file).
4. **Human gate.** Cross-session promotion of a new negative constraint requires
   explicit human confirmation (one wrong global constraint poisons every future
   run).
5. **Compact.** Periodically merge overlapping cards.
6. **Decay.** Cards overturned by human correction / repeatedly irrelevant are
   demoted and retired (recorded, not hard-deleted).

### 3.6 Injection routing loop

Without changing the Core Invariants, add to Routing Loop step 1 ("refresh index
and read"):

- At Orchestrator startup / branch start, **resident-inject** the compact list of
  long-term negative constraints (`trigger` lines); pull the full card only when a
  `trigger` matches the current structure (ADR 0012 granularity).
- On any `verifier` FAIL / `regulator` classification / `ce-hunter` obstruction /
  human correction, the responsible specialist emits a *candidate* card to **local
  memory**. **Candidate-card aggregation:** no mid-branch promotion; at run-end the
  **Orchestrator aggregates all candidate cards, dedup-filters, and folds them into
  the inbox**, leaving the human/distillation gate (§3.5) to decide promotion to a
  long-term negative constraint. (The Orchestrator only aggregates/routes; it does
  not judge mathematical content.)

**How to ensure both steps actually happen (enforcement, not good intentions):**
neither may be a soft convention; each gets a mechanical gate:

- **Production side (the specialist actually emitted a candidate card):** candidate
  cards are a **managed artifact** at `memory/candidates/<agent>-<runid>.jsonl`. Add
  a check to the lints for the `verifier` FAIL packet, `regulator` classification
  packet, and `ce-hunter` obstruction packet (e.g. `proof_attempt_lint.py --status`
  / `proof_review_lint.py`): **a FAIL/obstruction/human-correction conclusion must
  carry ≥1 candidate card (or an explicit `no-constraint: <reason>` marker)**.
  Missing ⇒ lint failure, the packet is incomplete — turning "emit a candidate
  card" from good intentions into a pass condition.
- **Aggregation side (the Orchestrator actually filtered):** the run-end
  `completion_gate` (tied to 0020) gains a precondition: **if `memory/candidates/`
  is non-empty, a corresponding `memory/candidates_aggregated.jsonl` (the
  Orchestrator's aggregation/dedup product) must exist and have been written to the
  inbox via `collector_write.py`**; otherwise the gate does not pass. Aggregation is
  thus a gateable mechanical fact, not the Orchestrator's good intention.
- **Aggregation is the Orchestrator's, the script is only a tool:** the keep/merge/
  drop **decision belongs to the Orchestrator** (judgmental collation, part of its
  routing role); it calls a deterministic normalization helper to **mechanically
  pre-dedup** by `(kind, normalized statement)`, merging obvious duplicates first,
  then finalizes on top of that. I.e. "Orchestrator-led, script-assisted", not
  "script decides on its own". This satisfies "aggregation is the Orchestrator's"
  without making the Orchestrator judge mathematical content (deduping experience
  cards is collation, not a math judgment).

### 3.7 Unified access facade for three-tier memory — implementation

Problem: each tier has its own read path; the model has to remember three tool
sets and easily misses one.

**Unified entry — consolidation, not a wrapper.** If `memory.py` merely
dispatched to `workspace_memory.py` / `collector_summary.py`, that is **one more
script, not one fewer**, violating "stop making so many scripts" and ADR 0020's
SSOT. So we **absorb**:

- **Move `workspace_memory.py`, `collector_summary.py`, and the `Experience_*`
  card model into an internal package `cli_tools/_memory/`** (`_memory/local.py`,
  `_memory/kb.py`, `_memory/experience.py`). The files physically live in one
  package so it is visually obvious that only the outer `memory.py` is the
  interface and everything in `_memory/` is a called script. `query_index.py` and
  `presentation_index.py` import the local tier from `_memory.local`. The
  **single external entry is `memory.py`**:

  ```
  memory read    --tier local|long-term|kb --view compact|summary|full [--query ...]
  memory refresh [--tier local]                 # absorbs workspace_memory refresh
  memory render-longterm                         # render the resident negative-constraint list from experience cards → memory.md (§3.3)
  memory aggregate-candidates                     # Orchestrator run-end candidate-card dedup → inbox (§3.6)
  ```

- Three-tier semantics in one place: `local` → local channel index; `long-term` →
  read the `memory.md` resident negative-constraint list (`compact` emits
  `trigger`, `full` follows pointers to the KB full card); `kb` → KB query. Output
  is a single JSON/Markdown envelope with a `tier` and `view` header.
- **Net effect: fewer scripts** (several memory scripts collapse into one external
  `memory.py` entry), aligned with ADR 0020's "single source / dedup"; the model
  only has to remember one memory tool.

**The only memory tool exposed to the model is `memory.py` (no two conflicting
tools for the LLM).** The point is not only "fewer scripts" but **one entry, one
format for the model**:

- The local/KB/experience logic lives in `cli_tools/_memory/` and is **not in any
  agent's prompt and not in 0020's tool allowlist** — i.e. **the model never sees
  it**, avoiding "use `workspace_memory show` or `memory read`?" ambiguity. Only
  `memory.py` is exposed.
- Three-tier memory is presented through **one `memory.py` output format** (same
  JSON/Markdown envelope + `tier`/`view` header). Facing memory, the model has
  **exactly one** `memory read/refresh` mental model.
- Shims may be deleted after the migration window (tied to 0020's dedup cleanup).

Supporting: prompts say only "**you have three-tier memory, select a tier with
`memory read --tier`**" (mentioning no old command); (tied to 0020) "read
long-term at startup, refresh local before a non-trivial cycle" is a hard
precondition. **Whether to physically merge the three underlying indexes into one
store** can be deferred (§7 Q1) — but the **external entry and format are
consolidated in this version**, no longer optional.

## Pre-implementation verification (P0, found by read-only diagnosis)

Before touching any code per this ADR, fix/verify these two existing defects
(they invalidate the premise that "memory actually takes effect"):

1. **`collector_write.py`'s CLI entry is broken.** `main()` ends with
   `write(args.content, args.path, args.filename, args.collector_dir)`, but the
   parser only defines `--data-dir` (`args.data_dir`); `args.collector_dir` does
   not exist ⇒ **running from the CLI necessarily raises `AttributeError` and
   nothing is written to the inbox**. So the "math result → inbox" chain is
   currently broken. **Also verify whether past workspaces ever wrote to the inbox
   successfully** (probably not). (ADR 0017 records this bug too.)
2. **`workspace_memory`'s `index.md` writes only counts, not content** (`latest`
   only reaches `index.json`) ⇒ a model reading only `index.md` sees no local
   memory content ("json spinning idle"). Render the `latest` summary into
   `index.md`.

## 4. Relationship to existing ADRs

- **ADR 0012** provides the base (writable files, AI-readable indexes,
  `compact→summary→full`). This ADR consumes it.
- **ADR 0015** provides the card format; distillation (Scholar/Reflector) is
  **deferred** (§3.5).
- **ADR 0017**: once decided "fold the long-term tier into the KB-Manager".
  **Settled as: "full content in the KB, index in `memory.md`"** — full card
  bodies enter the KB (read on demand), recall goes through the local resident
  `memory.md` index, not a KB pull (§3.3). 0017 has been narrowed accordingly and
  the two are consistent.
- **ADR 0020**: this ADR's "load long-term at startup / use all local channels /
  candidate-card and aggregation gates / `memory.py` absorbing scattered scripts"
  all depend on 0020's "index enforcement + SSOT dedup" to actually land.
- **`proof-review` skill (already modified, not just planned):** adds "a human
  mathematical opinion triggers proof-review, to be routed not obeyed", and "no
  human-opinion narration in `proof.tex`".

## 5. Non-goals

- Do not change hub-and-spoke, the task ledger, or the execution graph.
- Do not build a second knowledge base; facts are authoritative only in the
  KB-Manager wiki.
- Do not let agents write the wiki directly; math results always go through
  inbox + check.
- Do not stuff long-term negative constraints into KB pull (ineffective).
- Distillation (§3.5) is separately deferred.

## 6. Phased implementation plan

- **P0 — Pre-fixes.** Fix the `collector_write.py` CLI bug; verify past inbox
  writes; render `latest` into `index.md`. *(cli_tools)*
- **Phase 1 — Local tier.** Position as the "local tier"; lifecycle bound to the
  workspace; `index.md` uses all channels; optional `notation`/`readings` channel.
  *(cli_tools + prompts)*
- **Phase 1.5 — Dispatch skill (§3.1).** New `.agents/skills/memory-routing/SKILL.md`:
  delete-the-object test + decision tree + the exact command for each exit; wire
  in trigger words. *(skills + prompts)*
- **Phase 2 — Long-term resident tier.** Upgrade `memory.md` to the compact
  negative-constraint list rendered from experience cards (**location/structure
  unchanged, `AGENTS.md` untouched**); full cards into the KB; `memory.py
  render-longterm` generates `memory.md`; make "read `memory.md` at cycle start" a
  **hard-precondition gate** for "load at startup" (tied to 0020). `AGENTS.md` adds
  only one line "see `memory.md`, mandatory read at the start of every cycle".
  *(cli_tools + prompts + `memory.md`)*
- **Phase 3 — Unified entry (absorption, not wrapper; single model-facing entry).**
  Absorb `workspace_memory.py`/`collector_summary.py` as internal modules of
  `memory.py`, old commands as **internal thin shims (not in prompts, not in 0020
  allowlist, invisible to the model)** marked deprecated; single model-facing entry/
  format `memory read/refresh/render-longterm/aggregate-candidates`.
  *(cli_tools + prompts + 0020 allowlist)*
- **Phase 3.5 — Candidate-card enforcement + aggregation is the Orchestrator's.**
  Candidate cards as managed artifacts `memory/candidates/*`; the lint for FAIL/
  obstruction/correction packets enforces a candidate card (or `no-constraint`);
  `completion_gate` enforces "non-empty candidates → aggregated by the Orchestrator
  into the inbox"; `memory aggregate-candidates` is the Orchestrator's deterministic
  pre-dedup helper (decision still the Orchestrator's) (§3.6, tied to 0020).
  *(cli_tools/lint + orchestration)*
- **Phase 4 (deferred) — Distillation.** §3.5, ownership pending.
- **Phase 5 — Boundary enforcement.** Lint rejects inline facts in long-term cards
  and rejects constraint-type content written to the wiki. *(cli_tools/lint)*

## 7. Risks and open questions

- **R1 — Distiller over-generalizes.** Mitigation: human gate + mandatory
  `Failure modes`. (Distillation deferred.)
- **R2 — Boundary rule is judgment-heavy.** Mitigation: delete-the-object test +
  anything carrying a concrete statement defaults to inbox→KB.
- **R3 — Resident long-term tier consumes context.** Load-at-startup has a budget
  cost. Mitigation: ≤100-line hard cap + merge-first + inject only the two lines
  `trigger`/`statement`, full on demand.
- **Q1 (unified vs three, open).** §3.7's facade uses "unified facade + three
  underlying indexes", or physically merge? This ADR leans to the former.
- **Q2 (distillation/memory-management ownership, open).** A new `reflector` role
  vs folding into KB-Manager / the `regulator`'s run-end duty? Deferred, leaning to
  the latter. (No dedicated memory subagent, and no Codex/Claude-Code split —
  unified as Orchestrator run-end aggregation, see Diagnosis.)
- **Q3 (local memory reclamation).** How to reclaim a long-unused workspace (manual
  archive / N-cycle GC / keep an audit trace)?
- **~~Q4~~ (settled, closed).** Long-term tier "resident injection vs fold into KB"
  — **settled as "full content in KB, index in `memory.md`"**: full cards into the
  KB read on demand, recall through the local resident index. 0017 synced, closed.
- **Q5 (`heuristic-threshold` ownership).** Do threshold cards live in the resident
  long-term tier or the KB `Concept_*`? This ADR leans resident (thresholds also
  need "immediate effect" to prevent errors).
