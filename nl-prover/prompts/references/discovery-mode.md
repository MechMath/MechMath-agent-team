# Discovery Mode

Normative rules for any agent dispatched with `mode: discovery`.
The dispatch names the mode; this file defines it. Your role file defines who you
are and what you own — it does not repeat anything below.

Authority: ADR 0023. This file and `certification-mode.md` are the only two
places where mode-dependent rules live. If your role file appears to contradict
this file, this file wins and the contradiction is a bug to report.

## 1. What your output is

Discovery output is **conjectural evidence**. It is not mathematical
verification, it discharges no proof obligation, and it never merges into
`proof.tex`.

Two consequences, both absolute:

- **Your output does not cause a state transition.** You cannot mark a route
  `rejected`, `done`, or `blocked`. Only certification mode can.
- **Your output does not carry proof weight.** Anything you produce that later
  supports a proof must first pass the normal specialist + fresh Verifier path in
  certification mode.

**Where you write is what the dispatch names** — your role's normal output path,
under `artifact-ownership.md`. There is no separate `discovery/` tree; the region
is a property of the artifact, not of its directory.

So say which region it is, in the artifact's opening lines:

```
**Mode: DISCOVERY.** This artifact is conjectural evidence. It discharges no
proof obligation and carries no proof weight.
```

That header is what `proof.tex` is checked against: nothing declaring discovery
mode may be cited by it, wherever the file sits.

## 2. A failed attempt is a failed test case, not a failed theorem

"This attempt did not work" is a statement about **one attempt**.
"This route cannot work" is a statement about **a mathematical proposition**.
Never record the first as the second.

A route leaves discovery mode as `rejected` **only** with an exact
counterexample or a certification-mode fresh Verifier FAIL. Everything else
stays `open`. You do not need permission to re-propose an `open` route, and a
route appearing in the history is not a reason to avoid it — only `rejected` is.

## 3. Empty searches

Any search that finds nothing — computational, literature, counterexample,
construction attempt — is reported as:

```
NO_RESULT_IN_DECLARED_SCOPE
  searched: <the scope you actually covered>
  next:     <a different scope, stated explicitly>
```

Both fields are required. **The result is about the scope, not about the
object.** You may not conclude that the object does not exist; that conclusion
belongs to certification mode.

Do not invent status tokens. Words like `INCONCLUSIVE`, `*_CLAIM=NO`, or
`*_EXECUTABLE=NO` carry no meaning downstream — every reader collapses them to
"not PASS". Say what you mean in prose instead; only the tag above is machine-read.

## 4. A negative result must carry its scope

Whenever you close something off, record **which box you closed** and **the
artifact that closed it**. Closing one box never closes the family the box
belongs to.

Budget exhaustion is not a prohibition. If you stopped because you ran out of
budget, say so and leave the route `open`; do not write it as something that
must not be retried.

## 5. Arbitrary-but-declared is allowed here

A height bound, increment range, denominator template, degree cap, or any other
frame may be **chosen arbitrarily**, provided you (a) declare it before you look
at the result, and (b) hold out depth that took no part in the identification.
Declared frame plus untouched holdout plus exact residual is what protects
against overfitting — not a ban on running the experiment a second time.

"Any choice here would be arbitrary" is not a reason to stop. Declare one and try.

Provenance is not a precondition. A negative literature search closes the
question "where does this come from"; it closes no mathematical route. A fact
needs a source only when it must carry proof weight, and that is certification
mode's concern.

## 6. Strengthened-hypothesis progress is real progress

You may prove a version with an added hypothesis, provided the added hypothesis
is **written down explicitly** and recorded as a remaining obligation (remove it).
This is a route advancing, not a route failing: it must not be recorded as a
failure and must not trigger a change of direction.

## 7. Gaps become work orders, not exits

Locating the single missing ingredient and stating what it must satisfy is the
highest-value thing discovery produces. Never abandon at a gap.

State the gap as a specification with two required fields:

- `consumed_at` — which step it fills, i.e. which hole in the current
  decomposition it replaces.
- `acceptance` — how to tell a candidate is good enough. **Written by the
  consumer**, not by you. If that step has no owner yet, leave it empty; empty is
  better than restating the specification.

Write **necessary conditions, not a full description**. Every extra condition
shrinks the solution set, and extra conditions are usually traces of the one
implementation you happened to imagine. A specification is a reference, not a
contract: whoever takes the work order **is not bound by its letter** — an object
that fails one stated condition but fills the `consumed_at` hole counts as done,
and "that condition was unnecessary" goes back on the workbench as a finding.

## 8. Ranking

When ranking candidates, judge exactly two things:

1. **Feasibility** — how confident you are this route can be walked with current
   capability.
2. **Contribution** — if its central claim holds, how much of the target closes.

Everything else — history, risk, provenance, how checkable it looks — is
evidence you may cite, **not a scored dimension**. In particular, do not rank by
how easy something will be to verify: a genuinely new idea is least checkable at
the moment it is proposed. Making an idea checkable is the decomposition step's
job, later.

## 9. Effort, when you are inspecting someone else's candidate

Discovery-mode inspection is a scan, not an audit:

| | you must | you must not |
|---|---|---|
| read | only the candidate in front of you | the whole chain or the run history |
| cover | everything in it, missing nothing | — |
| depth | one line per concern: what it is | chase any concern down to a verdict |
| output | a list of concerns | a review packet, a `PASS`, or a `FAIL` |

**Depth is capped, coverage is not.** Skimming the whole thing costs almost
nothing extra; chasing each concern to ground is what makes a full audit
expensive. Stopping at the first concern is worse than scanning all of them,
because it turns one round into several.

Each concern then takes the cheapest route that fits it: fixable on the spot goes
straight back to the candidate's own owner as a revision; not fixable but
identifiable becomes a gap specification (§7); neither goes on the workbench for
certification mode to deal with. A revision is a new version of the same route —
it does not open a branch, does not enter route history, and does not change any
state.

## 10. Computation

Cheap experiments are part of exploring, not a privilege of auditing. Run them.
Results are grounds for trying something, never evidence for a claim.

Long or heavy runs belong to Code Executor with a reproducible package. Before
starting anything non-trivial, load the resource skill.

**If a computation is cut off by a resource limit, that is a resource fact, not a
mathematical one.** Make the experiment smaller and retry. Never close a route
because a run was terminated.

## 11. Enumeration before escalation

If a discrete ambiguity has an enumerable candidate set, enumerate it and test.
There is no cap on how many candidates justify this. Escalating to a human
requires stating why enumeration is infeasible — an unbounded set, or a per-check
cost with an order-of-magnitude estimate. "Too many" alone is not a reason.
