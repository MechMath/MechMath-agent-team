# Subagent Dispatch Cookbook

Use the smallest specialist that owns the current blocker. Do not default to
Sketcher/Generator/Verifier when another prompt owns the work.

## Two Required Dispatch Parameters

Every dispatch names both. They are Orchestrator decisions, not specialist ones.

**`mode`** — `discovery` or `certification`. It decides what counts as a
conclusion, what counts as a failure, what the specialist ranks by, and whether
its output can carry proof weight. Defined in
`prompts/references/discovery-mode.md` and `certification-mode.md`.
**All thirteen specialists can be sent to either mode**; each role file states
only which one applies when the dispatch omits it.

Discovery-mode output goes to the role's normal output path — there is no
separate `discovery/` tree — and **declares its mode in its opening lines**, which
is what keeps it out of `proof.tex`. It **cannot change any route state**: in
particular a discovery-mode Verifier reports concerns and does not issue
`PASS`/`FAIL`.

**`resume`** — whether to wake the same instance again or start a fresh one.
Resuming keeps the instance's working subdirectory and does not require it to
re-deliver a complete artifact.

Two cases where resuming is not allowed:

- a certification-mode Verifier is always fresh (ADR 0003);
- an Auditor performing an independent audit is always fresh, for the same
  anti-anchoring reason. It may be resumed for non-audit work.

Do not leave `resume` to the specialist: given the choice it will always prefer
more context, and the anti-anchoring cases above would lose their enforcer.

## What a verification dispatch may contain

`resume: false` buys a fresh **instance**. It does not buy a fresh **view** — that is
decided by what the dispatch prompt says, and the prompt is written by the Orchestrator
after it has read everything.

Measured over **87 verification dispatches**: 100% told the Verifier it was a fresh,
stateless, independent referee, and **84% supplied, in the same prompt, the thing that
independence excludes** — 57% the Generator's own account of its work, 45% what earlier
verifiers concluded. 16% handed over the artifact and nothing else. So the freshness
sentence is not doing the work it appears to do; the prompt around it is.

**Include, and nothing else:**

1. the artifact under review, **by path**, and the statement it must satisfy;
2. each dependency's `statement.md`, and its verdict — the *state*, `PASS` / `NEEDS_REVISION`
   / none, never the reasoning behind it;
3. the mode (`discovery` / `certification`) and the output path;
4. the required sections of the packet, and what makes it acceptable;
5. **a budget and a stopping condition.** 1 dispatch in 87 named one.

**Exclude by default:**

- the Generator's account of its own work — `generator/status.md`,
  `response_to_verifier.md`, and any "the Generator reports that …" in the prompt body;
- prior verdicts as narrative — "six rounds, all NEEDS_REVISION", "prior reviews flagged X",
  a recital of earlier findings;
- how confident anyone is, and any defence of the artifact;
- anything from another agent's transcript.

**Unresolved concerns still have to travel — put them in the artifact, not the prompt.**
An open concern belongs in the lemma's own obligation ledger or in the packet's open-question
section, written as a question about the mathematics: *"does Step 14 need `n ≥ 3`?"* — not as
a verdict about a document: *"three referees rejected Step 14"*. The first is a thing to
check; the second is an answer to agree with. This is the whole distinction, and it is why
the transfer channel is the frozen artifact rather than the covering message.

A disclaimer does not neutralise anchoring content. "Read them but treat their findings as
UNVERIFIED input" appeared verbatim in these dispatches and is the construction being
replaced, not an exemption from it.

| Situation | Dispatch | Advantage | Output | Next |
|-----------|----------|-----------|--------|------|
| No generator-ready DAG, route unclear, or repeated strategy failure | Explorer x2-3 with distinct constraints | Produces diverse mechanisms and prevents single-route overfitting | `routes/brainstorm_<N>.md` | Synthesizer |
| Multiple candidate routes or conflicting advice | Synthesizer | Ranks, merges, rejects duplicates, and builds a queue | `routes/synthesizer_<N>.md` | Sketcher or active queue |
| What is missing, or who owns it, is unclear | Regulator | Names the smallest missing thing and one owner, in prose | `recovery/regulator_decision_<N>.md` | Active dispatch plus queued alternates |
| Proof attempt locally incomplete while statement and plan look sound | Generator | Repairs proof text without changing the global plan | `lemmas/<id>/generator/proof_v<N>.md` | Fresh Verifier |
| Lemma statement, dependency edge, final bridge, or DAG incomplete | Sketcher or Refiner | Repairs canonical plan instead of forcing proof text | `sketch/revision_<N>.md` or refined plan | Plan verification |
| Named theorem, folklore result, classification, theorem package, or major estimate carries the proof | Searcher | Traces literature, audits exact statement, source route, preconditions, and circularity | `routes/source_theorem_<N>.md` | Sketcher/Generator |
| Specialized notation, named family, convention, or target reading is unstable | Auditor or target-reading workflow | Prevents guessed definitions from supporting proof or obstruction | `routes/definition_audit_<N>.md` or `sketch/target_contract.md` | Sketcher/Verifier |
| KB-Manager/local knowledge may resolve a source or definition | KB-Manager through query workflow | Grounds work in local knowledge without polluting proof text | `queries/<id>/kb-manager.md` | Source/definition owner |
| Boundary failure, degenerate case, possible falsehood, or impossible precondition appears | CE-Hunter, then Regulator using proof-review workflow | Attacks the target while preventing premature terminal claims | `routes/counterexample_<N>.md` plus optional proof-review artifact | Verifier only if Regulator says obstruction-ready |
| Finite enumeration, exhaustive check, or computation evidence is load-bearing | Code Executor | Audits finite/computed evidence before it carries proof weight | `routes/computation_audit_<N>.md` | Verifier |
| Complete proof has passed fresh verification | Refiner | Shortens accepted proof while preserving fallback | `refinement/proof_refined.tex` | Fresh Verifier |
| Verified proof needs final presentation, local rewrite is requested, or the human asks for progress reporting | Writer using article-writing skill | Keeps exposition separate from proof search and prevents Orchestrator from authoring mathematical prose | `writer/article_candidate.tex`, `writer/local_revision_candidate.tex`, or `writer/progress_notes.tex` | Orchestrator compiles/exports PDF; Verifier only if mathematics may change |

## Diversity Constraints

When launching multiple Explorers or Sketchers, assign distinct constraints:

- `direct-elementary`: avoid heavy theorem packages where possible.
- `known-theorem`: search for a load-bearing known theorem and list source
  risks.
- `counterexample-risk`: attack the statement through boundary cases and
  obstruction shapes.
- `bypass-current-dag`: avoid the current decomposition entirely.
- `minimal-lemma`: minimize the number of lemmas and final assembly steps.
- `max-verifiability`: prefer obligations that Verifier can check locally.
- `construction-first`: start from the key object, map, invariant, or witness.
- `obstruction-first`: start from no-go theorems or global invariants.

Do not launch two agents with nearly identical constraints in the same round.

## What counts as a batch

**A group of same-role specialists ran concurrently if and only if the spread
between their artifact landings is smaller than one agent's typical turnaround.**
Agents that worked at the same time finish at roughly the same time; agents that
were walked one at a time finish one turnaround apart, and the gaps say so no
matter what the dispatch intended.

A workspace whose one documented parallel pair landed **23 seconds** apart had
serial batches averaging **8 minutes** between members. That is the whole test —
there is no ambiguous middle in practice.

Sending N task calls is not the same as sending them together. If they are issued
in separate turns, they are N rounds wearing one name. `gate.py speed <workspace>`
checks this after the fact and reports the widest group that actually met the
criterion.

**Put `counterexample-risk` or `obstruction-first` in every Explorer batch.** An
adversarial constraint costs nothing extra — it is one more member of a batch that
is already running — and it moves the discovery of a normalisation trap or a
boundary failure from proof time back to plan time. A trap found during plan
verification costs one round; the same trap found during proving costs the proof.

## Retry in parallel, not in series

**Once a lemma has come back `NEEDS_REVISION` twice, stop sending one Generator
at a time. Send two, with different constraints, to different target files.**

```
lemmas/<id>/generator/proof_v4.md    <- constraint A, e.g. repair the flagged step in place
lemmas/<id>/generator/proof_v4b.md   <- constraint B, e.g. restructure around the flagged step
```

The third attempt at a lemma is not more likely to succeed than the second — a
measured retry loop reached **eleven versions** on one lemma, and each round cost
a full dispatch latency whether or not it was going to work. Two attempts in
parallel cost one extra dispatch and collapse two rounds into one.

**This does not add verification and must not.** The first artifact to land goes
to a fresh Verifier, exactly as now. The other is held unread as a fallback and
sent only if the first comes back `FAIL` or `NEEDS_REVISION`. So the number of
Verifier rounds is unchanged or lower; what changes is that the second attempt
did not have to wait for the first to fail.

- **Different constraints, or it is waste.** Two Generators told the same thing
  produce the same thing. Name the divergence in each dispatch: repair-in-place
  versus restructure, or lean on the dependency versus prove it locally.
- **Never merge them.** Adopt one, discard the other.
- **Two, not six.** Beyond two, the constraints stop being genuinely different
  and you are paying for copies.

## Certify the algebra mechanically before proving it

**When a lemma rests on an identity, a normalisation, a transform, or a finite
computation, dispatch Code Executor for a `PASS_AUDIT` before dispatching
Generator.** The Generator then writes a proof of something already known to be
numerically true, rather than discovering mid-proof that it was proving a
mis-transcribed identity.

`PASS_AUDIT` is **not a verification verdict and carries no proof weight** — the
Verifier's job is untouched and its checks are unchanged. It is a cheap mechanical
filter whose only purpose is to reduce the *number* of Generator/Verifier rounds,
not their depth.

Evidence, and its limit: the one workspace in the corpus that did this before
proving got **5 lemmas, none needing a second version, and zero recovery
decisions** — the cleanest run on record. That is n=1 and cannot be separated from
the problem simply being easier. What makes it worth doing anyway is the cost
shape: the audit is one cheap dispatch, and the failure it prevents is the retry
loop, where a single lemma has been measured at eleven versions and 7.9 hours.

## Prompt-Only Specialization

Different subagents remain useful even when they share the same base model. The
separation comes from:

- different input files;
- different allowed write targets;
- different forbidden actions;
- different output schemas;
- different success and failure criteria;
- different completion markers;
- different cognitive role in the route queue.

The goal is not more votes. The goal is to prevent the Orchestrator from
privately doing route design, proof repair, verification, source auditing, and
counterexample search, or article writing in the same context.
