# Proof audit — domain-generic stages

These stages apply to any proof audit. Nothing here is specific to a subject
area. Item typing (`[M]` / `[A]`) and the pass gate are in `SKILL.md`; read that
first, and read the stage→gate table there before hand-checking anything —
several items below are already enforced mechanically.

Run once per independent `OR` proof route.

Where the source specification said "adversary", read it as the general case:
the ambient hypotheses, the quantifier structure, the admissible parameter
range, and any opponent-shaped object (a counterexample hunter, a competing
bound, a worst-case instance) that the argument must survive.

## B.1 Intake, scope, and frozen baseline

- [ ] **B1.1 [M]** Every adjudicated theorem or conclusion has an atomic,
      falsifiable, fully quantified claim record.
- [ ] **B1.2 [M]** A **model snapshot** freezes and references the versioned goal,
      definitions, ambient hypotheses and quantifier structure, parameters, the
      object under study, the correctness convention, and any distributions or
      averaging conventions. One snapshot reference, not a second free-form copy
      of those objects.
- [ ] **B1.3 [M]** The **evidence obligation set** lists the proof, falsification,
      counterexample, parameter, source, reproduction, and independent-review
      obligations **and each one's exit condition**.
- [ ] **B1.4 [M]** Subject, proof route, dependency graph, and auxiliary artifacts
      all carry immutable versions and complete lineage.
- [ ] **B1.5 [M]** Audit scope distinguishes the abstract theorem, the concrete
      parameter instance, the effective/explicit refinement, the claim as it will
      be stated to a reader, and the **explicit non-goals**.
- [ ] **B1.6 [A]** Every external definition, theorem, or datum has a frozen
      version, location, errata status, and retrieval cutoff.
- [ ] **B1.7 [M]** Any substantive change to subject, model, dependency, or
      parameters creates a new version and **invalidates the old review** for it.

## B.5 Dependency graph, assumptions, and variants

The three failures in this stage are the ones that survive careful reading, so they
are stated as prohibitions rather than as checks.

- [ ] **B5.1 [M]** The dependency graph preserves every conjunctive premise, every
      complete alternative route, and every within-route dependency.
      **No flattening of `AND`/`OR`.** A conjunction rendered as a list, or an
      alternative rendered as a note, has lost the structure the audit runs on.
- [ ] **B5.2 [M]** Every external unproved premise has a typed **assumption card**.
      A goal, a definition, or an ambient hypothesis is *not* duplicated as an
      assumption merely because the same phrase appears in both.
- [ ] **B5.3 [A]** Every dependency references an exact, versioned **variant** of a
      statement, not a result-family name. There is no unversioned "the large
      sieve", "the standard estimate", "the usual Tauberian argument".
- [ ] **B5.4 [M]** Every dependency edge binds: definition, model, source and target
      variants, direction, parameter region, resource or uniformity model, and
      evidence scope.
- [ ] **B5.5 [M]** The proof **neither transfers family-level evidence to an
      unchecked variant nor splices children from different `OR` branches.** Both
      produce an argument that reads as complete and proves nothing: the first
      borrows confidence earned by a sibling (a theorem proved for one range or
      one normalization, invoked for another), the second assembles a route that
      no single branch supports.
- [ ] **B5.6 [M]** Premise kinds are classified on **orthogonal fields**, not one
      multi-select list — evidential standing, idealization, and role in the
      proof are different dimensions and a single `type` tag conflates them.
- [ ] **B5.7 [M]** Known contrary evidence, invalid parameter regions, circular
      dependencies, alternative assumptions, and sensitivity are recorded.
- [ ] **B5.8 [M]** Node and edge versions are fresh; any invalidation has propagated
      to every downstream claim.

## B.6 The step chain

- [ ] **B6.1 [M]** The **first step exactly matches the frozen definition** or the
      frozen statement of the lemma being proved — not a paraphrase of it.
- [ ] **B6.2 [M]** The **last step exactly matches the terminal object of the
      argument**: the previously proved lemma, the exact statement of the cited
      theorem, the unfolded definition, the axiom, or the proved terminal
      proposition it lands on. "Which reduces to the known result" is not a
      terminal object until the known result's exact statement is written down.
- [ ] **B6.3 [M]** Every step makes **one localized change**, classified as one of
      four relations to the previous state:
      *exact equality* (an identity, a rewriting, a substitution that changes
      nothing); *quantified closeness* (the difference is bounded by a named,
      carried term); *equivalence valid only in a stated regime* (asymptotic,
      limiting, or conditional on a hypothesis — the two sides are
      indistinguishable **to the resolution this argument works at**, and that
      resolution is stated); *conditioning on an exceptional case* (the step holds
      off a bad set, and that set is named and bounded).
- [ ] **B6.4 [M]** Adjacent steps have comparable objects, hypotheses, ranges of
      the quantified variables, and normalization conventions.
- [ ] **B6.5 [M]** Every invariant, coupling, identity, independence or
      orthogonality condition, and lemma a step relies on is **stated explicitly**.
- [ ] **B6.6 [A]** Induction and hybrid indices, index guessing, dyadic
      decomposition, and averaging arguments have correct quantifiers, endpoints,
      and losses.
- [ ] **B6.7 [M]** Differences, directions of inequality, absolute values, and
      triangle inequalities are correct, and **the chain contains no unproved
      step**.
- [ ] **B6.8 [A]** Branching chains close separately; terminal objects and bounds
      from different routes are not combined.

## B.8 Residual terms, resource transformation, effective bounds

- [ ] **B8.1 [M]** Every residual term is **typed** — error term, exceptional-set
      contribution, approximation/idealization error, or a *proved* refinement
      term.
- [ ] **B8.2 [M]** Every exceptional case or bad event has a unique name, the space
      it lives in, its condition, its bound, and the step it affects.
- [ ] **B8.3 [A]** The chosen distance, norm, or divergence satisfies the
      monotonicity and triangle-inequality premises actually being used.
- [ ] **B8.4 [M]** Union bounds, independence products, conditional probabilities,
      and tail bounds reflect the **actual** dependency structure.
- [ ] **B8.5 [M]** Error terms of different types, over different ranges, or lacking
      a proved composition rule **are not added merely because each is
      numerically small**.
- [ ] **B8.6 [M]** Every resource or precision field has a type, unit, quantifier,
      and meaning at the interface. **No undeclared bare `q`, `t`, `N`, `ε`,
      `X`.** An omitted field is not silently zero, not silently infinite, and not
      silently uniform in the other parameters.
- [ ] **B8.7 [M]** Every transformation of one bound into another gives
      componentwise accounting: the auxiliary construction, any preprocessing or
      setup, **every invocation of an external estimate** (each application of a
      cited bound, sieve, table, or numerical evaluation, with its own cost and
      its own validity range), and the bookkeeping of moving between parameter
      regimes.
- [ ] **B8.8 [M]** Every loss factor traces to a **specific** induction step,
      guess, abort, dyadic sum, repetition, or multi-instance conversion — not to
      "the reduction" or "standard losses".
- [ ] **B8.9 [M]** Every applicable resource is accounted: work or computation
      time, memory, number of applications of a cited estimate, samples or data,
      range of validity, uniformity, advice or precomputation.
- [ ] **B8.10 [A]** Worst-case, average, amortized, and one-time costs — and
      pointwise versus on-average bounds — are not substituted for one another.
- [ ] **B8.11 [A]** Repetition, amplification, iteration, and multi-instance
      conversions have proved independence conditions and a total cost.
- [ ] **B8.12 [M]** A concrete instance substitutes **every** loss and residual
      term and gives reproducible numbers: effective constants, the explicit
      threshold or range beyond which the bound holds, the rounding or
      truncation rule, and the valid parameter region. **An asymptotic conclusion
      is not an effective bound**, and an implied constant that was never tracked
      cannot be reported as one.

## B.11.2 Mechanization scope and trusted computing base

- [ ] **B11.8 [M]** Formalization scope and the unformalized remainder are recorded
      as `na / specified / partial / kernel_checked`.
- [ ] **B11.9 [A]** An item-by-item semantic mapping connects the natural-language
      definition, its formal semantics, the program or proof model, and the
      mechanized theorem. Audited, not asserted.
- [ ] **B11.10 [A]** The TCB lists proof assistant, kernel, libraries, plugins,
      solvers, computer-algebra systems, extractor, compiler — with versions.
- [ ] **B11.11 [A]** Axioms, trusted lemmas, opaque external results,
      `sorry`/`admit`, numerical oracles, floating-point evaluation, and unchecked
      code are **fully disclosed**.
- [ ] **B11.12 [A]** A clean build under frozen dependencies, a kernel-check log,
      and a replay entry point exist.
- [ ] **B11.13 [A]** If extraction, compilation, or floating-point semantics fall
      outside the TCB, the gap and the conclusion boundary are explicit.
- [ ] **B11.14 [M]** **Partial mechanization is not represented as a complete
      proof.** `kernel_checked` is claimable only against the current subject and
      the disclosed TCB.

## B.12 Adversarial validation, conclusion, reporting, archival

"Adversarial" here means the review posture, not an opponent in the theorem: the
reviewer's job is to try to break the argument, not to follow it.

### B.12.1 Independent adversarial validation

- [ ] **B12.1 [M]** Reviewer and generator are independent across principal, run,
      model, and input lineage. A reviewer who read the generator's account of its
      own work is not independent of it.
- [ ] **B12.2 [M]** Counterexample search covers boundary parameters, degenerate
      and extreme cases, small instances, the endpoints of every range, the
      equality cases, and the branches the proof passed over.
- [ ] **B12.3 [M]** Critical identities, bounds, step differences, and constant
      accounting are **recomputed independently**, not read approvingly.
- [ ] **B12.4 [M]** Adjacent definitions, stronger statements, and excluded
      parameter regions are used to test whether the conclusion **exceeds its
      scope**.
- [ ] **B12.5 [M]** Known counterexamples, barriers and obstruction results,
      errata, retractions and withdrawals, and later work before the cutoff are
      checked against the claim and against every node of the dependency graph.
      A cited result that has been corrected or withdrawn invalidates the edge
      that rests on it.
- [ ] **B12.6 [M]** Sensitivity is examined: remove or weaken each assumption,
      change the parameter region, switch `OR` routes.
- [ ] **B12.7 [A]** Finite-instance tests, symbolic computation, and numerical
      evaluation are evidence **within their stated scope only** and never replace
      a general proof.
- [ ] **B12.8 [M]** The report identifies, for every failure, blockage, and
      counterexample, the exact claim and evidence reference — **and states the
      scope of pass**: what the pass does not cover.

### B.12.2 Conclusion, reporting, archival

- [ ] **B12.9 [M]** Every obligation is satisfied, needs revision, is blocked, or
      has a justified `not_applicable`. **None is silently omitted.**
- [ ] **B12.10 [M]** Every conclusion references its atomic claim, the subject
      version, the model snapshot, and the dependency graph.
- [ ] **B12.11 [M]** Theorem, abstract, and title preserve the definition, the
      hypotheses, the assumptions, the parameter region, the losses, the residual
      terms, the uniformity and effectivity claims, and the limitations.
      Summarizing is where scope is lost.
- [ ] **B12.12 [M]** **Mathematical proof, mechanized check, numerical experiment,
      heuristic estimate, and plausibility argument are never represented as one
      another.** Record which kind of evidence was actually established.
- [ ] **B12.13 [M]** An open obligation, conflicting evidence, or an undecidable
      applicable item produces `INCONCLUSIVE` or a revision route — **not a pass**.
- [ ] **B12.14 [M]** Negative results, failed routes, counterexamples, and rejected
      `OR` branches are **retained and traceable**. They are the expensive part.
- [ ] **B12.15 [M]** The archive holds the claim records, model snapshot,
      dependency graph, variant cards, proof dossier, scripts, logs, review packet,
      and evidence. Where a computation supports the claim, it also holds the
      source or patch, the dependency lock, and a single-entry replay package.
- [ ] **B12.16 [M]** A review is valid only for the subject version it was bound to.
      Dependency, model, or implementation updates mark downstream claims stale and
      trigger re-audit of the affected checks.
- [ ] **B12.17 [M]** The overall verdict is derived from the aggregation rule over
      valid route results — **not from majority vote, not from the fact that
      artifacts were archived, and not from one subclaim.**
