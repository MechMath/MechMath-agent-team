# ADR 0019: External-Result Trust — Provenance, Citation Integrity, and Source Audit

## Status

Accepted — **implemented** (P1–P5).

> **Implementation status.**
> - **P1 (ledger + lint + routing).** `workspace.py ledger`
>   (`_workspace/ledger.py`) is the safe writer/reader of
>   `references/ledger.jsonl` with two-role field ownership (Searcher provenance
>   fields; a fresh Verifier's `set-trust`). `gate.py proof-attempt --ledger`
>   cross-checks theorem-like citations by `claim_id` and fails on
>   `pending-audit` (warns on `borrowed`). `prompts/searcher.md` records
>   provenance; `prompts/orchestration.md` states the pending-audit → fresh
>   Verifier dispatch. 14 tests.
> - **P2 (refs.bib).** `workspace.py refs-bib` (`_workspace/refs_bib.py`) fetches
>   real BibTeX from Crossref by DOI (no key), synthesizes a sparse real entry
>   otherwise, and reports missing metadata instead of writing `TODO`. Fetch sits
>   behind a `BibtexProvider` seam. 7 tests (offline).
> - **P3 (Writer).** `prompts/writer.md` + the `article-writing` skill: cite once
>   at first load-bearing use, attribute existing results, ledger-only
>   load-bearing keys, free related-work citations. `TODO`-citation policy
>   removed everywhere.
> - **P4 (trust = fresh Verifier).** `prompts/verifier.md` step 7 now owns the
>   source-theorem trust verdict (its auto-FAIL #10) and writes the ledger trust
>   fields via `ledger set-trust`; the definition Auditor only supplies readings.
> - **P5 (final audit).** `gate.py citation-audit` (`_gate/citation_audit.py`):
>   unresolved-key, cite-at-first-use, no-settled-use-of-pending/borrowed, and the
>   "existing result passed as original" attribution detector. Wired into the PDF
>   gate in `orchestration.md`. 10 tests.
>
> **Aligned with the tool refactor and ADR 0016/0017.** Tool names are unified
> into the five façades: audit/lint goes through `gate.py` (`proof-attempt`,
> `complete`, the new `citation-audit`), external-LLM cross-checks go through
> `external.py {gpt,gemini}`, literature metadata through `search.py arxiv`, and
> workspace reference/citation products through `workspace.py {references,refs-bib}`.
> The two tools still to be built are slotted into their façades: the `refs.bib`
> generator = `workspace.py refs-bib` (internally `_workspace/refs_bib.py`), the
> citation audit = `gate.py citation-audit` (internally `_gate/citation_audit.py`).
> The provenance ledger's "promotion to Collector" follows the inbox→check→wiki
> path of 0016/0017.
>
> **Aligned with ADR 0018 (implemented).** 0018 fixed that Searcher is a
> **divergent role that does no gatekeeping**: it does only a light
> provenance-level audit, and **correctness/trust verdicts belong to the fresh
> Verifier** (source-theorem audit = Verifier auto-FAIL #10; the definition
> Auditor only supplies readings when the notation of a cited statement is
> ambiguous, see the role clarification at the top of "Decision"). This round,
> per the user's annotations, restructures:
> - **Audit strength scales with use** — extremely loose during exploration,
>   strict only for load-bearing use / entering the final draft; the trust
>   boundary is at "use", not at "ingestion" (§2/§3).
> - **Audit is triggered per-claim, on demand**, not one Verifier batch-auditing
>   all the literature: "wanting to use a given claim as a load-bearing step" is
>   the signal to dispatch an audit of that one claim (§1).
> - **The three-state trust includes "borrowed" (`borrowed`)**: it allows
>   use-before-verification, requiring the verification obligation be discharged
>   only before the final draft, and does not disable on the spot so as not to
>   harm diversity (§2).
> - **The ledger folds into `references/`** (no separate `provenance/`);
>   **Writer's `refs.bib` takes real bibtex (OpenAlex/Crossref), leaving no
>   `TODO`** (§1/§4).
> - **§3 rewritten per the Collector check**: Collector has no content-audit
>   agent, so rather than adding a "full audit before promotion" heavy gate to
>   the KB, ingestion stays light (mechanical) and auditing is per-claim at use
>   time.
> - Ledger **field ownership**: Searcher fills only the provenance facts;
>   `audit_status`/`independent_warrant`/`trust` are assigned by the fresh
>   Verifier.
> - **External-LLM cross-check makes no direct verdict**: `external.py {gpt,gemini}`
>   is an input tool the Verifier calls, not something that decides trust
>   directly over the Verifier's head (§Background/Non-goals).
> - **`proof-attempt --status`'s ledger cross-check is given a concrete
>   implementation**: reuse the existing "theorem-like citation" detection, bind
>   `references/ledger.jsonl` across files by `claim_id`, and do only an
>   existence + status check (§1).

This corresponds to user fix-points **#4** (Writer must cite correctly, in KLMM
style, with citations in the right place), **#5** (results largely taken from
others' papers must be marked as existing results and cited correctly, not
passed off as original), and **#6** (results must be verified/audited before
use — especially arXiv sources). These three are really one problem: **how an
external result earns trust, and how that trust is recorded and presented to the
reader.**

## Background

The whole pipeline has a provenance/attribution hole end to end:

- **Searcher** records provenance in
  `references/papers/<paper_id>/{note.md, statements.jsonl, citation_trail.md}` —
  `statements.jsonl` even has `locator` and `source_quality: original
  theorem|secondary mention|derived in paper`. But these **never reach Writer**,
  and there is **no structured link from a specific proof step / theorem in
  `proof.tex`/`article_candidate.tex` back to a `paper_id`/locator, and no
  `\cite` key generated from one.**
- **Writer** (`prompts/writer.md`, the `article-writing` skill) has only the
  conservative rule: "do not fabricate citations. Keep existing citations or
  write `TODO`." **There is no "cite at the point of use" requirement, no
  "existing result" marking, no provenance obligation.**
  `mathematical-grounding.md` treats the source-theorem package as an acceptable
  source but never requires the article to mark it as *someone else's theorem*.
- **KLMM is ready but not actually used for citations.** `tex/KLMM/klmm.sty`
  loads `natbib` (`sort&compress`, `numbers,square`), `tex/KLMM/klmm.bst` is a
  plainnat-family style; `tex/template.tex` ends with
  `\bibliographystyle{KLMM/klmm}` + `\bibliography{refs}`. But **there is no
  `.bib` file anywhere in the repo**, nothing generates cite keys, and
  `workspace.py references` handles reference *files*, not citations. So citing
  at the point of use is mechanically impossible right now.
- **No source audit / final-draft audit.** `gate.py complete` (internally
  `_gate/completion.py`) is a **mechanical wrap-up gate**: it scans for `\sorry`,
  `TODO/FIXME/TBD`, blueprint placeholders and similar "unfinished" markers,
  checks that `STATUS.md`'s open-obligation lines are all resolved, that lemma
  lines/phases/review-packets are conformant, and that candidate-card
  aggregation meets the bar — **all structural, non-mathematical checks** that
  never touch whether a statement is correct. It governs "is this thing
  complete", not "is this thing true".
- **External-LLM cross-check should not serve as a direct audit verdict.**
  `external.py gpt` / `external.py gemini` (sharing `VERIFY_PROMPT`: "citing a
  paper does not remove the need to give a valid reason for the cited argument,
  unless the proof itself supplies that reason") **are tools, not judges**.
  **Per review feedback: do not wire them directly into the trust decision** —
  the one that decides trust is the **fresh Verifier**, which **may call**
  `external.py` to obtain an independent opinion as input and then reach its own
  conclusion. This preserves the value of the external opinion without letting an
  LLM score decide over the Verifier's head whether a result is trustworthy
  (consistent with invariant 16, "mechanical/external tools ≠ mathematical
  verification"). The current hole is: there is neither a Verifier-led source
  audit nor any article-level check ensuring every external citation points to an
  audited source.
- **After ADR 0018 landed, the flow of unaudited candidates grew significantly.**
  0018 explicitly adds no precision gate to Searcher (the former O4 was deleted
  for exactly this reason), and added web search and non-paper sources (GitHub,
  lecture notes, MathOverflow), `search.py frontier` multi-round frontier, and
  `search.py citation-graph` (OpenAlex) multi-hop expansion. The result is
  **more, messier, less peer-reviewed candidates** flowing downstream, and 0018
  pushes all the deciding power to this ADR's audit layer. This is both the
  necessity for this ADR and its load source: the audit gate must withstand that
  flow, or 0018's recall advantage turns into a noise disaster.

## Decision

> **Role clarification: the verdict owner of "source audit" is the fresh
> Verifier, not the definition Auditor.** The two roles in the repo divide the
> labour differently:
> - **Verifier** (`prompts/verifier.md`): the proof-correctness verdict,
>   fresh/stateless, judging "is the argument valid". Its **auto-FAIL #10 is
>   precisely the source-theorem audit** — "a named theorem carries a proof but
>   is not stated in the exact form used, lacks an independent source or
>   derivation route, or has unchecked preconditions"; circularity corresponds to
>   #1. So the trust verdict for external results is naturally the Verifier's job.
> - **Auditor** (`prompts/auditor.md`): the **reading** audit of
>   definitions/notation/named families/boundary conventions, judging "what does
>   this thing mean", producing an accepted reading. It **does not judge
>   statement truth and does not judge trust level**.
>
> Therefore in this ADR: **the trust level is decided by the fresh Verifier**;
> **the definition Auditor appears only when the notation/convention of a cited
> statement is itself ambiguous**, supplying a reading to feed the Verifier.
> Terminology reminder: the ledger field name `audit_status` and the "audit" in
> "source audit" in the prose are an **activity name**, whose executor is the
> Verifier, not "the Auditor role".

The core of this ADR is really two things:

**Core one: audit strength scales with "use", not with "whether there is a
provenance".** ADR 0018 has already opened up the inputs — arXiv, textbooks,
lecture notes, MathOverflow, even GitHub repos can flow in. Their trustworthiness
varies wildly and cannot be treated uniformly. The key criterion is not "does it
have a provenance" but **"what is it being used for"**:

- **Exploration phase: extremely loose.** Borrow freely, try freely. When
  Searcher/Explorer/Generator is trying a route, a conclusion of unknown origin
  may also be picked up first just to see whether it works. This phase sets no
  audit gate (consistent with ADR 0018's divergent positioning).
- **Load-bearing use / entering the final draft: extremely strict.** Once an
  external result is to **genuinely support a proof step**, or **is to appear in
  the final paper**, it must pass a strict audit to stay.

This criterion's origin is exactly the cause of this problem: **an arXiv result
was cited and later shown to be wrong.** So "has a provenance" is by no means
"trustworthy" — **even published, already-cited content must be checked before
load-bearing use.** "Having a source" only lowers the prior risk; it does not
exempt the audit.

**Core two: correct citation is Writer's job.** How to correctly cite the
external results used (cite at the point of use, mark as existing results,
generate an accurate bibliography) belongs to Writer, which in the final-draft
phase **aggregates uniformly all citations used across the whole workspace** and
settles them. The audit is responsible for "can it be trusted / how should it be
marked", Writer for "writing it out correctly".

Accordingly, introduce a **provenance ledger** running through Searcher → proof →
Writer → audit: the exploration phase only records and does not block;
load-bearing use triggers an **on-demand, per-claim** source audit (not a one-off
batch audit of all the literature); at the final draft Writer cites uniformly
what the ledger says should be cited, and adds a mechanical + mathematical
final-draft audit gate to stop "passing others' results off as original".

**Implementation responsibilities and dispatch (first make clear "who does what
when").** This ADR has no daemon; everything follows hub-and-spoke: **the audit
is not "pending auto-jumps to Verifier" but a mechanical signal surfacing, on
which the Orchestrator dispatches.**

| Mechanism | owner | Trigger point | Carrier |
|-----------|-------|---------------|---------|
| Fill provenance fields, deposit to inbox | Searcher | Wrap-up of each invocation (ADR 0018) | prompt (`searcher.md`) |
| Ledger existence + status check | mechanical lint | Every `gate.py proof-attempt` | tool (`_gate/proof_attempt.py`, add `--ledger`) |
| **Per-claim source audit** (sets trust level) | **fresh Verifier** (+ the definition Auditor for a reading when notation is ambiguous) | **lint reports some `claim_id`'s `trust` is still `pending-audit`** → Orchestrator dispatches a fresh Verifier to audit that one claim | prompt/skill (the source-theorem-audit part of `verifier.md`) |
| Generate `refs.bib` | mechanical | Before Writer produces a draft | tool (`workspace.py refs-bib`) |
| Citation integrity + attribution | Writer | Final draft | prompt/skill (`writer.md`, `article-writing`) |
| Final-draft audit gate | mechanical lint + fresh Verifier | Before PDF acceptance | tool (`gate.py citation-audit`) + Verifier |

Key clarification (answering the concern that "should orch actively call verifier
/ or does pending auto-jump"): **it is the Orchestrator dispatching actively, not
an auto-jump.** The mechanism is — `proof-attempt` lint turns "the `claim_id`
cited by some load-bearing step is not yet audited" into a **non-zero exit** (a
visible mechanical signal), the Orchestrator reads that signal and, per the
existing routing, dispatches a **fresh Verifier** (when the cited statement's
notation is itself ambiguous, first dispatch the definition Auditor to fix a
reading) to audit **that one claim**; once audited it writes the trust field back
to the ledger. This puts "want to depend on it → dispatch an audit" inside the
Orchestrator's routing loop, consistent with how other lint failures are handled,
introducing no automation magic.

### 1. Provenance ledger (the connective tissue linking #4/#5/#6)

**Put it under `references/`, no separate folder.** Paper cards are already at
`references/papers/<paper_id>/`, and `workspace.py references` scans here too, so
folding the ledger in is most natural: one workspace artifact
**`references/ledger.jsonl`** (a mechanical index, non-mathematical), one record
per external result the proof depends on. This is also what Writer will need
later, so no separate `provenance/`.

```json
{
  "claim_id": "L2.step4",              // point of use (lemma/step label)
  "statement": "…the statement used here…",
  "paper_id": "BSV2020",               // links to references/papers/<paper_id>/
  "locator": "Thm 3.2",
  "source_quality": "original theorem|secondary mention|derived in paper",
  "audit_status": "usable|needs-source|needs-local-derivation|obstruction-candidate",
  "independent_warrant": "PASS|FAIL|UNCLEAR",
  "cite_key": "BSV2020",               // BibTeX key in refs.bib
  "trust": "cite-as-existing | borrowed | pending-audit"
}
```

**What each field is:**

| Field | Meaning |
|-------|---------|
| `claim_id` | **Where** this external result is used — the label of a lemma/proof step, e.g. `L2.step4`. The same paper used in two places is two records |
| `statement` | The exact statement actually used here (in this problem's notation) |
| `paper_id` | The source paper, linking to `references/papers/<paper_id>/` |
| `locator` | The position in the original, e.g. `Thm 3.2` / `Lemma 4.1` / `§5 eq.(12)` |
| `source_quality` | This statement's identity in the **original**: original theorem / secondary mention / derived in that paper |
| `audit_status` | The usability verdict after audit (see §2) |
| `independent_warrant` | Whether it is independent of the target to be proved (guards against circular reasoning): PASS/FAIL/UNCLEAR |
| `cite_key` | The BibTeX key in `refs.bib`, consistent with the citation in §4 |
| `trust` | The trust level (see §2): `cite-as-existing` (audited, citable as an existing result) / `borrowed` (being borrowed, verification obligation not yet discharged) / `pending-audit` (want to use it → must dispatch an audit) |

**Field ownership (aligned with ADR 0018, key):**

| Field | Who fills | Note |
|-------|-----------|------|
| `claim_id`, `statement`, `paper_id`, `locator`, `source_quality` | **Searcher** | Pure provenance facts, from `references/papers/<id>/statements.jsonl` (a structured record, one per paper) |
| `audit_status`, `independent_warrant`, `trust` | **fresh Verifier** | The trust verdict (source-theorem audit = Verifier auto-FAIL #10). Searcher **must not** fill or preset these |
| `cite_key` | generated by `workspace.py refs-bib` | mechanical |

> **On `findings.md` (clarifying an ADR 0018 product).** The ledger's provenance
> fields come from `statements.jsonl` — that is a structured file **one per
> paper** (`references/papers/<id>/`), not all the literature stuffed into one
> big markdown. `knowledge/findings.md` is a different thing: it is a **short
> digest** for **this problem**, recording only "a few interesting results found
> + how they might be used (weak hints)" for quick human browsing, not a full
> corpus, and does not enter the ledger as a conclusion. The real per-paper
> detail always lives in `references/papers/<id>/`. If some problem's
> `findings.md` looks bloated, that is a sign the detail belongs in the paper
> cards and only a pointer belongs here.

- Every record Searcher hands over lands uniformly with **`trust: pending-audit`**;
  **only the fresh Verifier may change the trust fields.** The Source Theorem
  Package's `## Circularity and Strength Audit` is demoted from "fill the ledger"
  to an **input** to the Verifier — it is Searcher's observation, not a verdict.
- Extend `gate.py proof-attempt --status` (invariant 10): any theorem-like
  citation in a proof attempt must have a matching ledger entry — closing the
  "used but not recorded" gap.

  **Concrete implementation (reusing the existing mechanism, not writing a new
  one):** `proof_attempt.py` **already** detects "theorem-like citations"
  (theorem/lemma/proposition/estimate/bound…) in the proof body via
  `THEOREM_LIKE_CITATION_PATTERNS` and requires each to have a matching record in
  the `Dependency Lemmas Used` / `Theorem Preconditions Used` / `Source theorem
  obligations invoked` subsections of `## Hypotheses and Preconditions Audit`,
  erroring otherwise. This ADR only adds a **cross-file check** on top of that
  existing check:
  1. `proof-attempt` adds a `--ledger references/ledger.jsonl` argument;
  2. For each detected theorem-like citation, require the proof's audit
     subsection to give a **`claim_id`** (e.g. `L2.step4`) that must hit a record
     in `references/ledger.jsonl`;
  3. The hit record's `trust` must not be `pending-audit` (a load-bearing use
     must have been audited first, see §2); `borrowed` is allowed through but
     **marked as an undischarged obligation** left for the final-draft gate (§5)
     to catch;
  4. No matching ledger entry found → report "used but not recorded", non-zero
     exit.

  That is: bind "a theorem is mentioned in the body" and "this external result is
  recorded in the ledger" mechanically by `claim_id`, and the lint does only an
  **existence + status** check (purely mechanical), not judging statement truth.
**The audit is triggered per-claim, on demand, not a one-off batch audit of all
the literature (answering the concern that "one Verifier auditing everything is
too heavy").** A `pending-audit` record in the ledger triggers a Verifier
dispatch **focused on that one claim** only when it **is about to become a
load-bearing use** (see §2's "want to depend on it → dispatch an audit"). This
way: (1) piling up candidates during exploration costs no audit; (2) each audit
eyes only one statement and its preconditions, at fine granularity and more
likely to catch a latent error, rather than having one Verifier scan dozens of
papers at once with attention spread thin. The Orchestrator's dispatch timing is
therefore clear: **the moment a proof attempt is about to use an external result
as a load-bearing step** is the moment to dispatch a fresh Verifier to audit that
one claim.
### 2. Trust levels — three states, scaling with use, decided by the fresh Verifier (fix-point #6)

The three trust levels are not a one-off verdict of "can it be used" but a state
machine of **"used to what degree, verified to what degree"**. The grading and
state transitions are the **fresh Verifier's responsibility** (source-theorem
audit = its auto-FAIL #10; circularity = #1); whatever Searcher hands over is
uniformly `pending-audit`.

- **`pending-audit`** — not yet audited. **This is not a disabled state but a
  trigger state**: during exploration it may be looked at freely; but **the
  moment someone wants to use it as a load-bearing step, that "wanting to depend"
  is the signal to dispatch a fresh Verifier to audit that one claim** (the
  per-claim dispatch of §1). Once audited it migrates to one of the two states
  below. In other words, it is not "must not depend on it" but "want to depend on
  it → dispatch an audit first".
- **`borrowed` (being borrowed, formerly `must-justify-locally`)** — allows
  **use-before-verification**, preserving diversity. When the audit is not yet
  clean (secondary mention, out-of-scope rewrite, unsigned-off preprint, or
  `independent_warrant: UNCLEAR`), **do not forcibly forbid use**: you may borrow
  it to push the proof forward first, but **at the same time register an
  undischarged verification obligation**. The rule is "borrowing is allowed, use
  first then verify, but you must remember to verify once done":
  - during the borrowing the step carries a `borrowed` marker, an **undischarged
    proof obligation**;
  - **before the load-bearing path is finalized (entering the final draft / that
    branch being judged complete), this obligation must be discharged** — either
    Generator gives a local reason turning it into a self-proof, or the audit
    upgrades it to `cite-as-existing`, or it is downgraded and abandoned;
  - the final-draft audit gate (§5) will reject any load-bearing result still
    carrying an undischarged `borrowed`. This preserves the `VERIFY_PROMPT`
    principle while not strangling routes during exploration.
- **`cite-as-existing`** — an established, audited, unambiguous result.
  Requirements: the statement is exact / the rewrite matches and carries a
  locator, `independent_warrant: PASS`, and for a **non-peer-reviewed source**
  (arXiv preprint, web/GitHub/lecture notes, etc.) there must be an explicit
  **audit sign-off**: a fresh Verifier or a human checks that the exact statement
  used matches the source. → The article states it as a **cited existing
  theorem** and does **not** re-prove it.
  - *Exception (per review feedback): when a result is wrong but still has
    insight, you may try to re-prove it yourself.* At that point it is no longer
    "citing an existing result" but becomes a local proof obligation (going the
    `borrowed` / self-proof route), with the original provenance only cited as a
    related-work source of the insight.

**Non-peer-reviewed sources default to the strict path (fix-point #6):** arXiv
preprints, web, GitHub, lecture notes, etc., without sign-off and recorded in the
ledger, never reach `cite-as-existing` — at most `borrowed`, use-before-verification.
This is exactly the hole this ADR's cause (citing an arXiv result later
falsified) is meant to plug.

### 3. External results in the KB — audited not at promotion, but at use

**Check conclusion (having read `/home/cyc/caosip/github/Collector`): Collector
currently has no content-audit agent.** In its inbox→check→wiki, "check" is only
**mechanical**: SHA-256 dedup at registration, reading and asking for **human
confirmation** of 3–5 key points at ingest, and `wiki-maintenance lint`
afterward for orphan pages / missing frontmatter / duplicate concepts. **No role
judges whether a `Source_` card's statement is correct or whether its provenance
is trustworthy** — it is transcribed, not vetted. So the "let the KB's own audit
agent gatekeep" route does not work right now.

But this **does not require** adding a "full audit before promotion" heavy gate
to the KB in this ADR — that is exactly the "one Verifier auditing everything is
too heavy" that was rejected above. The right approach follows core one: **the
trust boundary is at "use", not at "ingestion".**

- **A KB card = a reusable declarative statement, not an audited truth.** A
  `Source_` card that has entered the wiki carries a provenance + an
  **unaudited** marker (the peer-review status of its corresponding source); it
  is only "someone somewhere has stated this" and by itself constitutes no
  permission.
- **Ingestion still goes through Collector's mechanical process** (dedup, format,
  human key-point confirmation); the NL-Prover side adds **no** mathematical gate
  for wiki promotion. This way Searcher's inbox deposit at each wrap-up (ADR
  0018) is not blocked by an audit, and the KB keeps accumulating fast.
- **The audit happens at the downstream pull.** Whenever some problem pulls a KB
  card via `memory.py read --tier kb` and wants to use it as a **load-bearing
  step**, that claim enters the problem's `references/ledger.jsonl` as
  `pending-audit`, triggering §2's per-claim audit — **treated identically to any
  arXiv/web source**. A KB hit only saves one retrieval; it does not exempt the
  audit.
- For the parts concerning statement correctness, hand to a fresh Verifier per
  invariants 3, 12; `gate.py proof-attempt --status` (invariant 10) requires the
  ledger entry as usual.

Net effect: light ingestion (mechanical), heavy use (per-claim audit) — neither
pressing an unbearable batch gate onto the KB nor letting unaudited content
quietly be load-bearing.

**Should we add a check/verify at the inbox? — After weighing: add only a
mechanical light check, no content audit.**

- **Adding a "content verify" (judging whether the statement is correct): not
  done.** Reasons: (1) this is exactly the rejected heavy gate, one Verifier
  auditing everything is too heavy; (2) most inbox cards may never be used again,
  so paying content-audit cost for all cards is waste; (3) cards that are
  actually used get audited per-claim at use time anyway (§3), so nothing is
  missed. **The right place for content auditing is "at use", not "at
  ingestion".**
- **Adding a "mechanical check" (format/dedup/provenance completeness): worth it,
  but basically already covered by Collector.** Collector's ingestion already
  does SHA-256 dedup + frontmatter validation + human key-point confirmation.
  This ADR only needs to **stipulate that a card must carry**: a provenance
  pointer (paper_id/locator/DOI) and an **unreviewed marker** (peer-review
  status), so the downstream pull knows it has not passed content audit and
  defaults to the strict path (§2). This is a **field convention**, not a new
  audit gate, at near-zero cost.

Conclusion: at the inbox **add no content verify**, relying only on Collector's
mechanical check + an "unreviewed" field convention; keep the whole verify budget
for "per-claim audit at use time".

### 4. Citation integrity — Writer, KLMM, point of use (fix-points #4/#5)

In `prompts/writer.md` (Hard Rules),
`article-writing/references/mathematical-grounding.md` (Citation Policy), and
`.../latex-research-note-template.md`, change the citation policy from "keep or
`TODO`" to a positive obligation:

- **Cite at the first load-bearing point of use; no need to re-cite at every
  occurrence.** Each result that has a ledger entry is cited once with the natbib
  KLMM command at its **first load-bearing occurrence**: `\citet{key}` when the
  author is the subject, otherwise `\citep{key}` — producing KLMM `[N]`
  numeric-square-bracket style. **This is not "cite everywhere"**: as with human
  writing, when the same result is mentioned repeatedly afterward, follow natural
  prose and need not attach a citation each time. The two extremes to avoid are —
  dumping a pile at the end, or using it but never citing it in the whole piece.
  The final-draft audit (§5) only requires "each load-bearing external result be
  cited **at least** once at its first point of use", and does not count
  subsequent restatements.
- **Existing results must be attributed, not passed off as original (#5).** A
  ledger entry with `trust: cite-as-existing` renders as an **attributed
  theorem** — `\begin{theorem}[{\citet{key}}] …` or "by the theorem of X
  \citep{key}, …". For a `borrowed` (use-before-verification) result: if it is
  finally turned into a self-proof, write it as a local proof with the original
  provenance cited as related work; if it still relies on borrowing for support,
  it must not enter the final draft (see §2/§5).
- **A `refs.bib` generator that takes real bibtex, leaving no `TODO` (answering
  the question "can we get fully accurate bibtex").** Add `workspace.py refs-bib`:
  for each `cite_key` in the ledger, **prefer fetching BibTeX directly from an
  authoritative metadata source** — using **OpenAlex** (already wired in by ADR
  0018; **no API key needed**: the polite pool only requires a contact email in
  the request, which is exactly why 0018 chose it; with a DOI you can also go
  through Crossref `content-negotiation`, which returns `application/x-bibtex`
  directly, likewise key-free), falling back to `references/papers/<id>/` and
  `search.py arxiv` metadata (`arxiv_id`, authors, `published`, `pdf`). Put the
  generated `refs.bib` next to the `.tex`, with `cite_key` consistent with the
  ledger. **Only when no source can produce it is that entry marked missing and
  reported to a human**, rather than stuffing a `TODO` into the body. This
  supplies the missing link that makes KLMM citations resolvable (the `bibtex`
  step in the compile sequence).
- **Writer receives those two files under `references/`, but citations are not
  limited to the ledger — distinguish "load-bearing citation" from "background
  citation".** Writer's input is `references/ledger.jsonl` + `references/refs.bib`
  (both under `references/`, alongside the paper cards). The two kinds of
  citation follow different rules:
  - **Load-bearing citation** (an external result supporting some proof step):
    **must come from the ledger**, `cite_key` already in it, and already past the
    §2 audit (`cite-as-existing` or a discharged `borrowed`). Writer may not add
    these out of thin air — adding out of thin air equals bypassing the audit of
    a load-bearing item.
  - **Background / related-work citation** (related work, "see also", motivation,
    history): **Writer is allowed to add these**, not limited to papers already
    in the ledger. Because they **support no proof step**, they **need not go
    through §2's mathematical/trust audit** — nothing depends on their
    correctness. But two bottom lines remain: (1) they must be **real literature**
    with resolvable bibtex (added to `refs.bib` via `workspace.py refs-bib` or an
    accurate entry Writer supplies), not fabricated; (2) **a background citation
    must not quietly become load-bearing** — the moment somewhere actually uses
    it to support reasoning, it upgrades to a load-bearing citation, must be
    back-filled into the ledger and trigger an audit (§1's lint catches exactly
    this overreach, erroring because a theorem-like citation in the body has no
    ledger entry).

  In one line: **the audit governs "load-bearing", not "mention".** Writer may
  cite freely when writing related work; as long as it is not used to support the
  proof, the mathematical audit does not intervene.

### 5. Final-draft audit gate (#5/#6)

Before the article/proof PDF is accepted, add an **article audit** step (reviving
the "final article verifier" idea; made of a fresh Verifier + a mechanical lint):

- **Mechanical** (`gate.py citation-audit`, non-mathematical): every
  `\citep/\citet` key resolves in `refs.bib`; every `cite-as-existing` result is
  cited **at least at its first load-bearing point of use** once; no load-bearing
  external result is in the dangling state of "neither cited as an existing
  result nor locally proved"; **no `borrowed`-undischarged or `pending-audit`
  result is used as settled support in the final draft**; and it flags any
  theorem treated as original whose statement matches some ledger
  `source_quality: original theorem` entry.
- **Mathematical / attribution (fresh Verifier) — this is the crux of #5: others'
  results must be cited, not silently written as one's own.** Spot-check every
  **seemingly self-proved load-bearing statement** in the final draft: if it
  actually matches some existing-result ledger entry (especially
  `source_quality: original theorem`), then it is **cite-worthy-but-uncited,
  passing others' results off as this paper's contribution** — it must be sent
  back and changed to an attributed citation. Conversely, for `cite-as-existing`
  non-peer-reviewed sources (arXiv, etc.), sample-check that the statement used
  matches the cited source (audit sign-off). **The core is not "is the statement
  copied correctly" but "is the attribution correct": existing things must be
  cited, and only original things count as one's own.**
- Failure blocks PDF acceptance, but per existing policy, **presentation failure
  does not change the mathematical stop status** (`orchestration.md`).

## Non-goals

- Do not automatically judge the mathematical correctness of a cited theorem
  (that is the Verifier's job); the ledger records the *trust level*, not the
  truth value.
- Do not build a citation *recommender*; keys come only from Searcher provenance.
- Do not replace the external-LLM cross-check tools (`external.py gpt` /
  `external.py gemini`), but also **do not let them serve directly as the trust
  verdict**: they are **input tools** the fresh Verifier may call, and the
  verdict is made by the Verifier (consistent with invariant 16).
- **Do not push gatekeeping back onto Searcher.** ADR 0018 already settled that
  Searcher diverges and sets no precision gate; this ADR takes on the deciding
  power and must not, on the grounds of "lightening the audit burden", require
  Searcher to pre-filter candidates.

## Phased plan (after approval)

(For each mechanism's owner / trigger point / carrier see the **Implementation
responsibilities and dispatch** table at the top of "Decision"; below breaks the
phases down in landing order.)

- **P1** — The provenance ledger schema + populate the **provenance fields** from
  Searcher output (trust fields left blank, default `pending-audit`);
  `gate.py proof-attempt` adds `--ledger` for a `claim_id` existence + status
  check; **write into the routing doc "lint reports `pending-audit` →
  Orchestrator dispatches a fresh Verifier to audit that one claim"** (not an
  auto-jump). *(cli_tools/prompts/orchestration)*
- **P2** — `workspace.py refs-bib` (ledger + paper cards + arxiv metadata →
  `references/refs.bib`): **prefer fetching real BibTeX from OpenAlex/Crossref**,
  mark missing only when it cannot be fetched, leaving no `TODO`.
- **P3** — Rewrite the Writer + `article-writing` citation policy:
  `\citep/\citet` at the first point of use (no re-citing at every occurrence),
  attribution of existing results, KLMM, ledger keys only. *(prompts/skills)*
- **P4** — **Land the trust grading + per-claim audit as the fresh Verifier's
  responsibility** (three-state verdict, sign-off for non-peer-reviewed sources,
  per-claim audit when a downstream pulls a KB card): write the source-theorem
  trust audit into `prompts/verifier.md` (its auto-FAIL #10 already covers it,
  extended to read/write the ledger trust fields); the definition Auditor only
  supplies a reading when a cited statement's notation is ambiguous;
  `prompts/searcher.md` and the `source-theorem` skill record only the
  **boundary** (Searcher does not judge trust level), which is already
  implemented with ADR 0018. *(prompts/skills)*
- **P5** — `gate.py citation-audit` (including the "passing others' results off as
  original" detector) + fresh Verifier final-draft attribution audit; wire in the
  pre-PDF gate. *(cli_tools/orchestration)*

## Risks and open questions

- **R1 over-blocking**: a strict arXiv audit may stall a route that legitimately
  depends on a good preprint. Mitigation: `borrowed` (use-before-verification)
  allows borrowing during exploration/proof advancement, requiring the
  verification obligation be discharged only before the final draft, rather than
  halting on the spot, preserving the route.
- **R2 ledger maintenance cost**: yet another artifact. Mitigation: it is
  generated from Searcher output, not hand-written; coverage is enforced by lint.
- **Q1 cite-key scheme**: author-year (`BSV2020`) or `arxiv_id`? It must be
  stable within a project so the KB `Source_` card and `refs.bib` agree (linked
  with ADR 0018's write-back).
- **~~Q2 where the ledger lives~~ (settled)** — in the workspace
  **`references/ledger.jsonl`** (alongside the paper cards, `workspace.py references`
  already scans here), no separate `provenance/`. Cross-problem reuse **does not
  rely on "promoting the ledger"**: declarative statements are reused across
  problems through the KB (`Source_` cards) as usual, while the trust verdict is
  re-audited per §3 **at each problem's use time** — because trust is a
  use-dependent judgement of "can this step in this problem rely on it", not
  something to be transplanted whole to another problem as an established
  conclusion.
- **Q3 audited vs preprint signal**: how to judge "peer-reviewed" (has a DOI, has
  a journal field, Matlas vs arXiv provenance)? This decides who goes the strict
  path. **Note**: the web / non-paper sources introduced by ADR 0018 (lecture
  notes, blogs, MathOverflow, GitHub) have **no peer-review signal at all** and
  should default to the strict path (`borrowed` to start, use-before-verification),
  unless an audited source can be traced.
