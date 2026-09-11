# ml1_b3_nlprover_exact_w36

## Scope

Used `/home/caoyichuan/caoyichuan/github/NL-Prover-v1`'s
`cli_tools/external.py discuss` backend (`gemini-2.5-pro`) to search for a proof of the exact
protected theorem
`Kakeya.ml1Boot.exists_isTwoScaleFactors_of_frostmanDividingBlock`. The declaration in
`CaseTwo.lean` was not edited. No master file was edited by this task.

## NL-Prover runs

1. Full `B3EndToEnd.lean` plus the exact protected request.
   NL-Prover returned a purported full proof, but it contained multiple `sorry`s, assumed
   `s = s'`, and identified the arbitrary `exists_parentFamily` map with
   `U.cover.assign a`. These assertions do not follow from the protected hypotheses. The draft
   is rejected and was not made into a Lean candidate.
2. Exact endpoint producer from `LossLedger.lean`, with the invalid assumptions called out.
   NL-Prover correctly confirmed that the endpoint producer's `TTheta/pTheta` is unrelated to
   the dividing block's `U.cover.tube/assign`. It proposed a constrained producer, but its own
   proposed statement required a new good-node/branch assumption and its proof still contained
   `sorry`; it is not a candidate.
3. Exact exponent-feasibility audit against `AnalyticEndgame.lean` for all/singleton structural
   factors. NL-Prover simplified the three target right sides to

   - fine: `delta^(-4 av') * (delta/tau)^(2-3 gamma) * Nf^(1-gamma/2)`;
   - middle: `delta^(10 av) * (tau/theta)^(2-3 gamma) * Nm^(1-gamma/2)`;
   - coarse: `delta^(-4 av') * theta^(2-3 gamma) * Nc^(1-gamma/2)`.

   With fine=all and middle/coarse singleton, the constraints reduce at
   `tau=delta, theta=1` to
   `10 av <= 3 gamma - 2`, `3 gamma - 2 <= 4 av'`, and
   `8 av' <= 10 av`. They are compatible only at the isolated boundary
   `gamma=2/3`, `av=av'=0`, not uniformly on the protected range. With fine/coarse singleton
   and middle=all, the Frostman epsilon loss has the wrong sign against the positive
   `delta^(10 av)` gain. Thus the weak-record all/singleton bypass is not a uniform proof.

The query texts are `NL_QUERY.md`, `NL_QUERY_2.md`, and `NL_QUERY_3.md` in this scratch
directory.

## Kernel-verified existing staging

The current `B3EndToEnd.lean` was rechecked in the current Numina environment:

```text
lake env lean Kakeya/DimensionThree/MainLemma1/B3EndToEnd.lean   PASS
lean.py scan B3EndToEnd.lean --plain                            PASS
lean.py axioms B3EndToEnd.lean                                  PASS
accepted axioms: propext, Classical.choice, Quot.sound
```

In particular, these existing components are real, axiom-clean progress:

- retained hierarchy factor construction and controlled ambientization;
- exact branch-card and scalar-loss assembly;
- exact numeric tail from `IsTwoScaleAnalyticBounds`;
- exact protected wrapper from a `B3PostCertificate` callback.

They do not prove the protected theorem because the analytic callback is still an input.

## Exact first blocker

There are two current reductions, and both erase data needed by the analytic consumer.

### Endpoint reduction

`LossLedger.exists_caseTwo_ambient_fineEndpoint_productOnly_with_loss` constructs
`TTheta/pTheta` using an arbitrary ambient `exists_parentFamily` (see its docstring and proof at
`LossLedger.lean:610-670`). The dividing block controls only `U.cover` on `s'`. Hence its
`frostman_nodes` and `frostman_lower` fields cannot be applied to the endpoint middle/coarse
factors. This is a route/API mismatch, not evidence that the protected statement is false.

### Hierarchy/dedup reduction

`B3EndToEnd.eventually_b3_raw_certificate_of_dedup` does build a factor tied to the block via
`exists_b3_ambient_factor_of_controlled`, but its `hpost` contract (lines 1180-1205) is universal
over an arbitrary bare `IsTwoScaleFactors`. The call at lines 1257-1259 passes only `hB3` and has
already discarded the construction-specific facts.

`IsTwoScaleFactors` itself (ScalarFactorization.lean:659-708) stores no ball containment,
essential distinctness, Frostman bounds, density brackets, item-IV free-scale lower bound, or
positive quantitative fullness. In this producer it is instantiated with
`lamF=lamM=lamC=0`. Therefore the first analytic consumer premise that cannot be recovered from
the passed value is already a positive fine threshold of the form

```lean
(delta : ENNReal) ^ gFine <=
  ShadedBody.fullness (fibre s pTau kF) (fun i => (Yf i).toShadedBody)
```

together with the matching fine Frostman/geometry facts. The middle consumer then also needs the
free-scale item-IV container/density statement, and the coarse consumer needs density/Frostman
data. None is a field of the bare B3 record.

The required next theorem is not another universal callback from `IsTwoScaleFactors`. It must
inline or strengthen the hierarchy factor producer so that it returns its selected factors
together with `AnalyticEndgameW27.IsTwoScaleAnalyticBounds`, or at least all producer-specific
premises consumed by `eventually_b3_analytic_bounds_of_consumers`, before controlled
ambientization erases their provenance. The exact protected theorem need not change.

## Verdict

No complete sorry-free body was produced by NL-Prover in this task. Every Lean draft it returned
contained placeholders or an invalid extra assumption, so none was submitted for integration.
No inconsistency of the exact protected statement was found. The verified blocker is a missing
producer-specific analytic construction/interface, not the already-closed structural or numeric
tail.

## W36 structural-certificate attempt

The requested constant-map/fullShade/zeroExtend route was checked against the exact exponents.
`card_ge_of_frostmanConstIn_le` supplies the volume lower bound, but it does not control the
ambient multiplicity. The available pairwise-ED count is only the eventual `δ⁻⁷` bound. For
`γ = 1`, `τ = δ^q`, `θ = 1`, the three analytic clauses force the carrier/multiplicity
exponents `α, β, χ` to satisfy

```
α / 2 ≤ 4 av' + 1 - q
β / 2 ≤ q - 10 av
χ / 2 ≤ 4 av' + q.
```

Together with `0 ≤ q ≤ 1` and `8 av' ≤ 10 av`, these imply
`α + β + χ ≤ 6`. This is kernel-checked by
`replicated_skeleton_total_exponent_le_six` in `ExponentAudit.lean`. Therefore a replicated
three-family skeleton cannot carry the permitted `δ⁻⁷` ambient cardinality while retaining the
absorption gain. The simpler fine-all/middle-singleton stress test is also kernel-checked in
`gamma_one_extreme_skeleton_contradiction`.

The exact first unresolved target in a body using this route is the middle analytic inequality
(and, after replication, the sum of the three analytic inequalities); all skeleton fields and
the product/branch arithmetic can be constructed, but the analytic conjunction has no uniform
finite-parameter proof from the protected hypotheses. The helper file compiles in the current
Numina tree after `lake build Kakeya.DimensionThree.MainLemma1.B3EndToEnd`, has zero `sorry`/`admit`,
and all three declarations depend only on `[propext, Classical.choice, Quot.sound]`.

An additional NL-Prover call was attempted with `NL_QUERY_4.md`; the current environment has no
`OPENROUTER_API_KEY` or `OPENAI_API_KEY`, so the facade returned that error before proof search.
