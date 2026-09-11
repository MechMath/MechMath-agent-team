import Kakeya.DimensionThree.MainLemma1.B3EndToEnd

/-! Kernel-checked obstruction for the all/singleton degenerate skeleton.

At `τ = δ` and `θ = 1`, the fine-all, middle-singleton, coarse-singleton
specialisation of the three analytic clauses reduces to
`10*av ≤ 3*γ - 2 ≤ 4*av'`.  The B3 gain constraint then leaves only the
isolated endpoint `γ = 2/3`, `av = av' = 0`.
-/

theorem singleton_extreme_exponent_audit
    {a a' gamma : ℝ}
    (ha : 0 ≤ a) (haa' : a ≤ a')
    (hfine : 10 * a ≤ 3 * gamma - 2)
    (hcoarse : 3 * gamma - 2 ≤ 4 * a')
    (hgain : 8 * a' ≤ 10 * a) :
    gamma = (2 : ℝ) / 3 ∧ a = 0 ∧ a' = 0 := by
  have ha_upper : a' ≤ (5 : ℝ) * a / 4 := by linarith
  have ha_zero : a = 0 := by linarith
  have haa'_zero : a' = 0 := by linarith
  constructor
  · linarith
  · exact ⟨ha_zero, haa'_zero⟩

#print axioms singleton_extreme_exponent_audit

/-! The concrete `γ = 1`, `N = δ⁻⁶` stress test for the same skeleton.
The fine-all clause (with multiplicity/cardinality at the crude ED bound) asks
`3/4 ≤ av'`; the singleton-middle clause at `τ/θ = δ` asks `av ≤ 1/10`.
These are already inconsistent with the gain constraint, independently of
any geometric implementation details.
-/

theorem gamma_one_extreme_skeleton_contradiction
    {a a' : ℝ}
    (ha : 0 ≤ a) (haa' : a ≤ a')
    (hfine : (3 : ℝ) / 4 ≤ a')
    (hmiddle : a ≤ (1 : ℝ) / 10)
    (hgain : 8 * a' ≤ 10 * a) : False := by
  linarith

#print axioms gamma_one_extreme_skeleton_contradiction

/-! Aggregate budget for the constant-map/replication attempt at `γ = 1`.
Write `q` for the exponent in `τ = δ^q`, `θ = 1`, and `α, β, χ` for the
cardinality/multiplicity exponents carried by the fine, middle and coarse
families.  The three analytic clauses yield the displayed half-exponent
inequalities.  Their sum can never reach the available `δ⁻⁷` ED-cardinality
budget once the B3 gain constraint is imposed.
-/

theorem replicated_skeleton_total_exponent_le_six
    {alpha beta chi q a a' : ℝ}
    (hq0 : 0 ≤ q) (hq1 : q ≤ 1)
    (ha : 0 ≤ a) (haa' : a ≤ a')
    (hgain : 8 * a' ≤ 10 * a)
    (hfine : alpha / 2 ≤ 4 * a' + 1 - q)
    (hmiddle : beta / 2 ≤ q - 10 * a)
    (hcoarse : chi / 2 ≤ 4 * a' + q) :
    alpha + beta + chi ≤ 6 := by
  linarith

#print axioms replicated_skeleton_total_exponent_le_six
