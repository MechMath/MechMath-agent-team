# ADR 0018: Searcher — Source Internalization, KB-Manager Collaboration, and Deep Search

## Status

Accepted — **implemented** (P1–P4).

> **Implementation status.**
> - **P1/P2 (prompts/skills).** `prompts/searcher.md` gained the "search wide,
>   do not gatekeep" positioning, KB-first recall, web search, deep reading for
>   sub-lemmas, the hop-budgeted frontier loop, the `knowledge/{findings,map,
>   leads}.md` digest, a `kb_pointer` field on `statements.jsonl`, and the KB
>   inbox deposit as the closing task of every invocation. The `source-theorem`
>   skill gained an explicit Audit Boundary table; the `search` skill gained the
>   deep-search playbook.
> - **P3 (tools).** `search.py frontier` (`_search/frontier.py`) persists the
>   candidate queue in `<workspace>/knowledge/`; hop budget is the only stop
>   condition. 18 tests.
> - **P4 (tools).** `search.py citation-graph` (`_search/citation_graph.py`)
>   walks OpenAlex references/cited-by, scores by keyword overlap, and merges
>   into the same frontier. Edge fetching sits behind an `EdgeProvider` seam so
>   a second source can be added. 20 tests, run against a fake provider (no
>   network).
> - **O-web is prompt-level, not a tool.** No `search.py web` subcommand was
>   added: general web search has no key-free API worth wrapping, and the
>   harness already provides web search/fetch. O-web is therefore implemented as
>   workflow steps in `prompts/searcher.md` and the `search` skill. This is the
>   option the ADR itself left open ("harness `WebSearch`/`WebFetch`, **or** a
>   thin `search.py web` wrapper").

> **Aligned with ADR 0016/0017 and the tool refactor.** The memory division of
> labour follows 0016 as settled (**full content in the KB, index in
> `memory.md`**; the anti-drift "pointer, not inline" rule is 0016 §3.4).
> References to 0017 now point at its **narrowed** structure (§1 card-family
> table / §2 `Experience_*` schema / §3). Tool names are unified into the five
> façades (`memory / search / external / gate / workspace`): KB writes go through
> `memory.py inbox-write --card-type`, literature retrieval through
> `search.py {arxiv,matlas,index}`, proof-attempt lint through
> `gate.py proof-attempt`.

This corresponds to user fix-points **#2** (upgrade Searcher per ADR 0015; make
it collaborate with Collector / KB-Manager) and **#3** (Searcher needs **deeper**
search). The deep-search part has **converged** after several rounds of review
annotations: all five mechanisms (O-web / O-read / O2 / O3 / O1) are in, the stop
condition is a hop budget, the citation API is OpenAlex, and caches land in the
workspace. Part C retains the trade-offs of each option and the rationale for the
dropped proposals (the former O4/O5) for the record.

## Background

Searcher today does literature tracing + theorem-package auditing:

- `prompts/searcher.md` → one `# Source Theorem Package` (`## Search and
  Literature Trace`, `## Theorem Candidate`, `## Preconditions`, `## Circularity
  and Strength Audit`, `## Use in Current Proof`), plus paper cards
  `references/papers/<paper_id>/{note.md, statements.jsonl, citation_trail.md}`.
- `statements.jsonl` records `{id, locator, statement, hypotheses, conclusion,
  source_quality: original theorem|secondary mention|derived in paper, fit}`.
- The `source-theorem` skill adds classification (`usable | needs-source | …`), a
  Component Bridge Ledger, an equivalence smoke test, and the
  `gate.py proof-attempt --status` mandatory hook (invariant 10).

Two gaps, exactly the ones ADR 0015 pointed out:

1. **No digestion layer.** Nobody rewrites retrieved results in **this problem's
   notation** (specialized lemmas), builds a knowledge map, or proposes attack
   routes. Sketcher/Generator each re-read the raw query output. (Searcher's
   current artifacts are the six-section `# Source Theorem Package` listed above
   plus the `references/papers/…` paper cards; these are *provenance + audit*
   artifacts and contain no "rewrite in this problem's notation and plan the
   attack" digestion layer.)
2. **Searcher and Collector are peers with no shared digestion layer.** In
   `orchestration.md` the `context-source` failure class lists "Searcher /
   Auditor / Collector" as equals; Collector statelessly reads `wiki/` per query,
   Searcher writes `references/papers/…`, the two are unconnected, and there is
   no direct agent-to-agent channel (hub-and-spoke). **State-of-the-world check:
   write-back is not yet implemented.** The `memory.py inbox-write` *tool* landed
   in ADR 0016/0017 (the inbox→check→wiki path works), but `prompts/searcher.md`
   currently only covers the **read side** ("look at the Collector summary") and
   has **no** step that writes a `Source_` card back to the KB inbox. Wiring
   Searcher to that tool is exactly what Part B / P2 of this ADR does; it is not
   implemented yet.

**Deep search today is shallow**, narrow on all three axes:

- **Too few sources.** `search.py arxiv` only does `all:<query>` relevance search
  (no citation/cited-by API); `search.py matlas` is single-shot; both are
  content-addressed one-off caches with no cross-query linking. **There is
  currently no web search at all** — only the two mathematical-library entry
  points arXiv/Matlas, which cannot reach textbooks, lecture notes, blogs,
  MathOverflow, or journal pages, often the clearest source for a given result.
  No citation-graph tooling.
- **Too shallow.** Step 7 of `searcher.md` only follows "at least one citation
  level" (going further only when a paper cites an older theorem); the `Depth`
  column of `citation_trail.md` is filled in by hand.
- **Reading is too coarse.** After a hit there is **no deep read**: today it only
  summarizes/surfaces bibliographic records by relevance and never actually goes
  into the body to extract the statement to be used together with its
  preconditions. And — **the result to be used is often not the paper's main
  theorem but one of its sub-lemmas / propositions / corollaries** (frequently
  the piece that actually fits this problem's obligation); shallow
  record-level retrieval misses precisely that layer.

## Decision

### Part A: Fold source internalization into Searcher (adopting ADR 0015's Scholar)

Rather than adding a standalone Scholar agent, **extend Searcher** to carry the
internalization step. After (or alongside) building the Source Theorem Package,
Searcher produces a problem-local **digest** under the workspace `knowledge/`
directory (born and dying with the problem; **this directory is new in this ADR
and does not exist in the current repository**):

**Digestion ≠ audit.** Searcher does only a **light audit** (whose result is
this, where does it come from, does it roughly fit this problem).
**Correctness auditing is not its job** — that belongs to Auditor, delivered in
ADR 0019. So the three artifacts below focus on **"what interesting result was
found / how it might be used (weak hint) / where it comes from"**, not on
delivering audited usable statements.

- `knowledge/findings.md` (originally to be named `toolbox.md`) — records
  **interesting findings** one by one: what the result is (restated in this
  problem's notation to the level of "downstream can understand it"), **how it
  might be used** (explicitly marked as a *weak hint, not a commitment*), a
  provenance pointer (paper_id + locator), and a proved/attributed marker. **A
  complete specialized statement is optional**: write it if you can, and do not
  block if you cannot — whether the specialization is right and whether the
  preconditions hold is left to Auditor/Verifier; Searcher does not decide for
  them.
- `knowledge/map.md` — the strength/special-case relations among results, the
  list of remaining gaps, and **entries that do not currently fit this task**
  (marked "does not fit this problem" with a reason). **Do not write "dead
  ends"**: a literature result is never a dead end in itself; a different task or
  a different use may make it useful. This file only records *fit with this
  problem* and never condemns a result.
- `knowledge/leads.md` (originally to be named `attack_plans.md`) —
  **candidate leads** (not "attack plans"): several possible ways "these findings
  might be strung together", each noting the `findings.md` entries used, the key
  remaining gaps, and **points to watch**. The wording is deliberately kept
  **open and diverse** — listing several mutually distinct routes in parallel is
  encouraged, err on the side of more; "points to watch" are **hints, not
  vetoes**, must not be written as discouraging conclusions, and downstream is
  entitled to ignore them and keep exploring. Routed by the Orchestrator as
  needed — to whoever needs it (commonly the branch queue of
  Explorer/Synthesizer, but possibly Sketcher/Generator/Regulator), with no
  preset recipient.

Discipline (from ADR 0015): **active-recall self-check** (close the source,
restate from memory, then cross-check, correct, and only then write). Every entry
in `knowledge/` must be traceable to some query result or paper note — **no
fabricated results** (this is Searcher's only hard constraint; it is "provenance
honesty", not a correctness audit). The digest is a *hint layer* and grants no
permission by itself: a named theorem still has to pass the Auditor audit (ADR
0019), `gate.py proof-attempt --status` (invariant 10), and a fresh Verifier
review (invariants 3, 12) before it enters a proof — **none of these three is
executed by Searcher**.

*Why fold in rather than add a Scholar*: keeps the paper's 12 roles; "everything
about external results" has a single owner; reuses Searcher's existing package
pattern. (Revisited under open questions below.)

### Part B: Searcher ↔ Collector (KB-Manager) collaboration protocol

All collaboration is routed by the Orchestrator through artifacts (no direct
messages), obeying the principle that "the KB is the sole authority for
declarative statements" (ADR 0016 §3.4 / 0017 §1 card-family table):

1. **Read side (KB → Searcher).** Before external retrieval, Searcher must
   **query the KB first** and reuse existing `Source_` cards rather than
   re-tracing a paper the KB already holds. **The read side goes uniformly
   through the memory tool settled in 0016/0017** (`memory.py read --tier kb`),
   which performs recall over the KB and returns the matching
   `Source_`/`Concept_` pointers to Searcher — it is **not** some Collector agent
   surfacing pages directly from `wiki/`. (`memory.py` is the single entry point
   for the three memory tiers, and KB recall is its responsibility;
   Collector/KB-Manager appears only on the **write** side of
   inbox→check→wiki.)
2. **Write side (Searcher → Collector inbox).** **The bar is not "fully
   usable"** — as soon as Searcher judges an external result **meaningful and
   extensible** (potentially reusable across problems), it may submit a
   `Source_`/`Concept_` card to the Collector **inbox** via
   `memory.py inbox-write --card-type Source_` (the `--card-type` write
   convention is ADR 0017 P1). **This is consistent with the "divergent, no
   gatekeeping" positioning: what is written is the inbox, not the wiki.**
   Correctness is decided by subsequent review — a card in the inbox enters the
   wiki only after review by an **Auditor dispatched by the Orchestrator**
   (ownership per ADR 0019); **passing the audit is the admission condition, and
   Searcher does not carry that step**. The Orchestrator routes this review but
   must never perform it itself: judging a `Source_` card's correctness is a
   mathematical judgement, and Core Invariant 1 confines the Orchestrator to
   routing and collation. Declarative content
   therefore lands in the KB once and is reused across problems; Searcher's
   `references/papers/…` cards become the *provenance chain* backing that KB
   card.

   **Q-write-timing → settled as "write at handoff" (settled).** **Writing the
   inbox is the last task of every Searcher invocation**: as it hands the handoff
   artifacts to the next specialist and then does a workspace cleanup pass, it
   also drops whatever deserves to be retained into the inbox, and only then is
   the round complete. Writing is therefore bound to the **wrap-up of a single
   Searcher call**, not to the wrap-up of the whole problem.

   Implementation point: add this step explicitly to the completion conditions of
   `prompts/searcher.md` (before `SOURCE_THEOREM_SCOUT_DONE`), making it part of
   the role contract rather than an optional action.

   *(The other two candidates and why they were dropped, kept for the record:
   **(a) write anytime** — submit on discovery, loses the least, but produces the
   most inbox noise; **(b) write when the problem is done** — highest quality but
   **loses everything on a crash/interruption**. (c) gets both a natural batch
   boundary and interruption resistance: an interruption loses at most the last
   round.)*

3. **Non-duplication (best effort is enough).** The KB card is authoritative;
   `statements.jsonl` links it via `locator` + a KB pointer (a concrete
   application of ADR 0016 §3.4's "pointer, not inline" anti-drift rule). Before
   writing back, Searcher **checks for duplicates in passing**: if the KB already
   has a card for that statement, prefer **supplementing/updating the existing
   card** (adding the provenance chain, locator, a more precise statement) over
   creating a near-duplicate. **But this is best effort only and must not become
   a hard gate** — the Collector side already has a dedup gate that blocks
   duplicate writes, so Searcher need not take on the burden or abandon a
   submission because a dedup check failed.

Net effect: Collector becomes the durable literature memory, and Searcher is its
field agent + per-problem internalizer.

### Part C: Deep search — mechanisms, script design, settled parameters

The problem: reliably finding the *useful* premise for a hard open problem — it is
often not a paper's main theorem but a sub-lemma / proposition / corollary buried
in the body, several citation hops away, or stated only in a textbook, lecture
notes, or some Q&A thread.

**Positioning (per review feedback): Searcher is a divergent role whose goal is
"breadth + extracting the interesting results", and it does no gatekeeping.** All
candidates are passed downstream; whether they are *trustworthy/usable* is
Auditor's call (exactly the division of labour in ADR 0019). Deep search
therefore prioritizes **recall/diversity** and adds no precision filter gate.

Against the three background gaps (few sources / shallow depth / coarse reading),
**all five mechanisms are adopted** (O-web/O-read/O2/O3 in P3, O1 in P4):

| Option | Mechanism | Requires | Trade-off |
|--------|-----------|----------|-----------|
| **O-web add web search** | Beyond arXiv/Matlas, add a general web retrieval path reaching textbooks, lecture notes, blogs, MathOverflow/MSE, journal pages, **and non-paper sources such as GitHub** (formalization libraries, experiment code, data tables, conference slides — often hiding constructions, counterexamples, or numerical evidence not written up in papers, which are themselves "interesting results") — and often the clearest source for a given result | the harness's `WebSearch`/`WebFetch` (or a new thin `search.py web` wrapper), reusing the content-addressed cache | highest breadth, fills the math-library blind spots; noisy (left to downstream/Auditor to judge) |
| **O-read deep read after a hit** | For a hit, take more than the bibliographic record: go into the body and extract the **statement to be used (including sub-lemmas/propositions/corollaries)** together with its preconditions and locator into `knowledge/findings.md` | existing `workspace.py references extract` (local PDFs) + `WebFetch` (online) + an extraction prompt | directly cures "coarse reading + missed sub-lemmas"; more expensive per paper, so only done for highly relevant hits |
| **O2 query expansion / keyword-family iteration** | Generate a family of synonym/notation-variant keywords, search each, merge | existing tools only + an expansion prompt | cheap; misses results phrased with distant vocabulary |
| **O3 iterative-deepening frontier** | Maintain a (paper, depth) frontier in the workspace, expand the highest-scoring node until the budget is exhausted | a thin script managing frontier state (design below) + a Searcher-driven loop | controllable cost, interruptible and resumable; needs a good stopping rule (see Q-stop) |
| **O1 multi-hop citation graph** | Follow citations/cited-by N hops, dedupe, rank by relevance to the obligation | the OpenAlex citation/cited-by API (see Q-API) → new `search.py citation-graph` (internally `_search/citation_graph.py`) | highest recall for "buried original theorems"; the only new external dependency, hence scheduled in P4 |

**How the O3 script is designed (answering "do we need to write a script?").**
Yes, but **a very thin state script, not a searcher**. The key division:
**the script only persists and queues frontier state; it does no retrieval and
makes no scoring judgement** — retrieval is done by Searcher calling
`search.py {arxiv,matlas,web}`, and "how relevant is this" is judged by Searcher
(the model). That keeps it a repository-defined "mechanical index tool" and stops
it from crossing into mathematical judgement.

The frontier is stored as one JSONL file in the workspace
(`knowledge/frontier.jsonl`, born and dying with the problem, matching
Q-cache=workspace), one candidate node per line:

```json
{"id": "arxiv:2103.01234", "title": "...", "source": "arxiv|matlas|web|citation-graph",
 "depth": 1, "parent": "arxiv:1901.05678", "score": 0.72,
 "status": "queued|expanded|skipped", "why": "matches the sub-lemma keywords of the obligation"}
```

A new `search.py frontier` (internally `_search/frontier.py`), five subcommands,
all mechanical:

```
search.py frontier init   <workspace> --obligation "<the statement sought for this problem>"
search.py frontier push   <workspace> --id ... --title ... --source ... --depth N --parent ... --score S --why ...
search.py frontier next   <workspace> [--n 3] [--max-depth 2]     # pop the n highest-scoring queued nodes
search.py frontier mark   <workspace> --id ... --status expanded|skipped
search.py frontier status <workspace>                             # expanded count, queue length, per-depth distribution, budget usage
```

Searcher's loop is then: `init` → run one search round with
`search.py {arxiv,matlas,web}` → `push` the hits into the frontier (score and
`why` supplied by the model) → `next` to take the following batch → run the
O-read deep read on what was taken, `push`ing newly discovered citations if
needed → `mark` what has been processed → until the `--max-depth` hop budget is
exhausted (see Q-stop).

Three side benefits: **interruptible and resumable** (state is on disk, a crash
does not mean starting over), **natural dedup** (idempotent `push` by `id`), and
**visible budget** (`status` shows the Orchestrator directly how much has been
spent). Note that `status: skipped` only means "not expanded this round" and is
**not** a verdict that the result is useless — the same principle as `map.md` not
writing "dead ends".

**How exactly O1 is designed (answering "feels a bit complex").** **Settled: O1
is implemented too** (no longer optional/deferred). The complexity is all in the
external API and rate limiting; the algorithm itself is tiny. Minimal version:

```
search.py citation-graph <seed_paper_id> --obligation "<the statement sought for this problem>" [--hops 1]
```
1. Resolve `seed_paper_id` (arXiv id / DOI) → call **OpenAlex** (see Q-API) to
   fetch the paper's `referenced_works` + `cited_by` edge lists;
2. BFS up to `--hops` hops (**default 1**), deduping by work id;
3. Rank each node by **cheap scoring** (keyword overlap of title/abstract with
   `--obligation`), **making no truth judgement**;
4. Return the sorted `(paper, hop, why)` list and `push` the nodes into O3's same
   `knowledge/frontier.jsonl` (the two share a frontier, `source:
   citation-graph`).

**Until O1 lands, degrade temporarily to a manual single hop**: Searcher picks
from a paper's reference list itself and queries each with `search.py arxiv` as
before. So O1 is the increment that "automates this step + goes multi-hop" — it
does not block P3 and can proceed in parallel.

> **The former O5 ("reuse the deep-research skill fan-out") has been deleted.**
> To clear up the question raised: **there is no `deep-research` skill in the
> repository** (existing skills: article-writing / human-review / knowledge / llm
> / memory-routing / nl-prover / proof-recovery / proof-review / proof-summarize
> / search / source-theorem / target-reading / verification). That line was a
> fabricated reference from an early draft. "Fan out → fetch → adversarially
> verify → synthesize" is a general pattern of the Workflow orchestration layer,
> not a callable repository skill; if we really want it, it should be built as a
> loop over O-web + O-read above, not by referencing a nonexistent skill.

> **The former O4 (cross-source triangulation) has been deleted.** Per review
> feedback: it adds a precision gate to Searcher, contradicting the "diverge,
> pass everything interesting downstream, let Auditor judge" positioning;
> gatekeeping is ADR 0019's responsibility, not this one's.

**Implementation scope (settled)**: **all five are done** — O-web + O-read + O2 +
O3 go first (using only existing harness tools, no new external dependency),
**O1 is implemented as well**, merely scheduled after them because it needs an
external API; until O1 is in place, the manual single hop fills in.

**The four former open questions are now all settled:**

- **Q-stop → hop budget (settled).** Use a **hop budget** uniformly as the stop
  condition (O1's `--hops`, O3's `--max-depth`), with a **small default of `1`**.
  The Orchestrator may raise it at dispatch time (a large-scale deep search gets
  more hops) or keep the default (a small search) — it is a tunable dispatch
  parameter, not a hard-coded constant. *(No token budget is introduced: hops
  already bound the cost well enough, and stacking two budgets only makes
  stopping behaviour unpredictable.)*
- **Q-API → settled as OpenAlex (settled).** The arXiv API itself has **no**
  citation/cited-by edges, so a citation graph requires an external scholarly
  graph API. Two candidates:
  - **OpenAlex (the open-source successor to Microsoft Academic Graph)** —
    `api.openalex.org`. Fully open, **no key required**, and generous quota in
    the polite pool (requests carry a contact email) (~100k/day); every work
    carries `referenced_works` and `cited_by`, with enormous coverage.
    **← Adopted**: no key means no credential management and friendly
    offline/headless operation, and the quota is wide enough that no complex
    backoff design is needed.
  - **Semantic Scholar (Allen Institute for AI)** — the Graph API at
    `api.semanticscholar.org`. Each paper carries `references` and `citations`
    edge lists, plus abstract, SPECTER vectors, and tldr. Free; rate limits
    without a key are tight (single-digit requests per second), and decent quota
    requires applying for a key. **Kept as a fallback**: if OpenAlex coverage is
    poor for some problem, it can serve as a second data source.

  In implementation, factor the edge-fetching step into a thin adapter layer so
  the source can be swapped or two sources merged later.
- **Q-precision vs recall → keep diversity (settled).** Do not add a mandatory
  corroboration gate to `usable`; Searcher stays divergent, erring on the side of
  inclusion, and whether something is actually useful is judged by downstream
  subagents / Auditor (ADR 0019). (Matching the deletion of O4 above.)
- **Q-cache → workspace (settled).** The persistent frontier/graph cache for deep
  search lives in the **workspace** (born and dying with the problem), not in
  `DATA_DIR`.

## Non-goals

- Do not add a Scholar/Reflector agent here (Reflector ownership is ADR 0016 §7
  Q2 — the current landing point is to add no agent and have the Orchestrator
  aggregate at the end of a run; Scholar is folded into Searcher as above, but
  see the open questions below).
- Do not build semantic/vector retrieval and do not train a retrieval model:
  scoring stays at cheap keyword-overlap heuristics, and ranking is used only for
  *queueing*, never for *judging truth*.
- Do not change invariant 10's lint or Verifier discipline.
- Do not do correctness gatekeeping inside Searcher (that belongs to Auditor /
  ADR 0019).

*(The former item "do not lock down the deep-search algorithm or citation API" is
void: this revision settles that O1–O3 are all done, the citation API is
OpenAlex, and the stop condition is a hop budget.)*

## Phased plan (after approval)

- **P1** — Extend `prompts/searcher.md` + the `source-theorem` skill with the
  `knowledge/{findings,map,leads}.md` internalization artifacts and the
  active-recall self-check; state the boundary "Searcher does only a light audit;
  correctness auditing belongs to Auditor (ADR 0019)". *(prompts/skills)*
- **P2** — The Searcher↔Collector protocol: the query-KB-first rule, write-back
  of `Source_` cards via `memory.py inbox-write` (bar = meaningful/extensible,
  not `usable`), and a KB pointer field in `statements.jsonl`. *(prompts/skills;
  `--card-type` writing is already implemented in ADR 0017 P1. **Write timing is
  settled as "write at handoff"**: the last task of the wrap-up of a single
  Searcher call, written into the completion conditions.)*
- **P3** — The body of deep search: implement O-web + O-read + O2 + O3 as a loop
  over existing harness tools — add a web retrieval path, deep-read extraction of
  sub-lemmas after a hit, keyword-family expansion, and an iterative-deepening
  frontier; add `search.py frontier` (`_search/frontier.py`) to manage frontier
  state, with the cache landing in the **workspace**; the stop condition is
  uniformly a hop budget (`--max-depth`, default 1, tunable by the Orchestrator).
  The deep-search orchestration playbook is delivered as a skill.
  *(cli_tools + skills)*
- **P4** — Implement the O1 citation graph: the `search.py citation-graph`
  subcommand (internally `_search/citation_graph.py`), placed under the search
  façade, data source **OpenAlex** (edge fetching factored into a thin adapter
  layer for source swapping / adding Semantic Scholar), with nodes merged into
  P3's same `frontier.jsonl`. **Does not block P3, can run in parallel**; until
  it lands, Searcher fills in with the manual single hop. *(cli_tools)*

## Risks and open questions

- **R1 context budget (ADR 0015 risk B)**: internalization may blow up the
  prompt. Mitigation: `knowledge/` goes to disk first; the Orchestrator reads
  only the completion receipt + a summary of `knowledge/leads.md`; downstream
  reads on trigger hits; Verifier is given none of it.
  - **File rename**: the former `attack_plans.md` → **`leads.md` (search
    leads)**. "Attack plan" sounds like a settled battle plan, the opposite of
    the "divergent, weak hint, do not discourage exploration" positioning;
    `leads.md` makes clear these are **leads produced by search**. (Alternatives:
    `search_leads.md`, `findings_leads.md` — if the shared lineage of
    `findings.md` / `leads.md` should be made more visible.)
  - **Budget loosened**: the former "≤4 lines" was indeed too tight and would
    force Searcher to cut diversity — conflicting with the recall this ADR wants
    to preserve. Changed to **the Orchestrator reading a summary of `leads.md` by
    default (1–2 lines per lead, roughly a 6–10 item cap)**, with the full body
    left on disk to be read on demand. Better to list several more leads than to
    keep only one to save tokens.
- **R2 Searcher overload**: stuffing internalization + deep search + provenance
  into one role may be too heavy. *Q:* keep it folded in (12 roles, recommended)
  or split internalization back out into a standalone Scholar side branch for
  parallelism? (Echoes ADR 0016 §7 Q2.)

  **How each part lands (clarifying the prompt / skill / tool division):**

  | Capability | Carrier | Landing place | Why this carrier |
  |------------|---------|---------------|------------------|
  | The boundary of the light audit (what it does, and that it does **not** do correctness auditing) | **prompt** | `prompts/searcher.md` | it is a role definition and prohibition, must be resident in Searcher's context |
  | The format and writing conventions of `knowledge/{findings,map,leads}.md` | **prompt** (skeleton) + **skill** (details/templates) | `prompts/searcher.md` + `source-theorem` skill | the skeleton must be resident; templates, examples, and the active-recall checklist load on demand to avoid blowing up the prompt |
  | How the deep-search loop runs (O-web/O-read/O2/O3 orchestration, when to deepen, when to stop) | **skill** | the `search` skill (or a new `deep-search` skill) | it is a multi-step process playbook, loaded only when a deep search is actually needed |
  | Frontier state persistence / queueing / budget statistics | **tool** | `search.py frontier` (`_search/frontier.py`) | purely mechanical, interruptible and resumable, contains no judgement |
  | Web retrieval entry point | **tool** (thin wrapper) or the harness directly | `search.py web` or `WebSearch`/`WebFetch` | it just fetches data; the caching strategy matches the existing arxiv/matlas |
  | Deep-read extraction after a hit | **tool fetches the body** + **prompt/skill does the extraction** | `workspace.py references extract` / `WebFetch` + extraction rules written into the skill | fetching the body is mechanical; "which sub-lemma to extract" is judgement and belongs to the model |
  | Multi-hop citation graph | **tool** | `search.py citation-graph` (`_search/citation_graph.py`, OpenAlex) | pure API calls + BFS + cheap scoring |
  | KB read/write | **tool** (existing) | `memory.py read --tier kb` / `memory.py inbox-write` | already landed in 0016/0017, reuse directly |

  Division principle: **judgement goes to prompt/skill, state and data fetching
  go to tools.** If Searcher still looks heavy after this split, consider peeling
  the "deep-search loop" off as a whole into a parallelizable side branch (at
  which point it looks more like a skill-driven subprocess than a 13th/14th
  role).
- **R3 statement drift** (if write-back is careless). Mitigation: the KB card is
  the sole authority; `references/papers/…` serves only as provenance (ADR 0016
  §3.4 "pointer, not inline").
