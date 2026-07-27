---
name: sorrifier
description: "Use when a complex Lean proof has a localized failing step that should be isolated manually: replace the failing subgoal with sorry, verify the file, write a helper lemma for that exact goal, and replace the placeholder with a helper call."
---

# Sorrifier — Proof Isolation Workflow

Structural refactoring workflow for isolating broken proof steps. Replace failing logic with `sorry`, manually extract the subgoal into a standalone helper lemma, and reconstruct the call site so the main theorem stays readable.

## Tools Used

| Tool | Skill | Purpose |
|------|-------|---------|
| `python cli_tools/lean.py check FILE` | [verification](../verification/SKILL.md) | Diagnose compilation errors and pinpoint failing lines |

## Execution Workflow

Follow these steps sequentially:

### Step 1: Diagnose
Run `python cli_tools/lean.py check FILE` to identify failing lines.
- Read `lean_messages` for entries with `severity: "error"`.

### Step 2: Inject `sorry`
Edit the Lean code: replace the failing tactic/expression with `sorry`.
- Scope the `sorry` to the smallest failing block, not the entire theorem.

### Step 3: Verify sorrified state
Run `python cli_tools/lean.py check FILE` again.
- Acceptance: zero errors. Warnings about `declaration uses 'sorry'` are expected.
- If errors persist, adjust sorry placement and repeat.

### Step 4: Extract a helper lemma manually

Create a helper lemma near the parent theorem:

- include exactly the local variables and hypotheses needed by the isolated subgoal;
- use the isolated subgoal as the helper conclusion;
- name the lemma after the parent theorem and mathematical step;
- leave the helper proof as `:= by sorry` only if the point is to split work into a new task;
- replace the original placeholder with a call to the helper lemma.

### Step 5: Final verification
Run `python cli_tools/lean.py check FILE` one last time.
- Acceptance: the parent theorem compiles by calling the helper. Any remaining `sorry` is isolated in the helper lemma and must be tracked as a separate task.

## Example

**Broken state:**
```lean
import Mathlib.Tactic

theorem sum_of_squares_helper (n : ℕ) : (n + 1)^2 = n^2 + 2*n + 1 := by
  have h1 : (n + 1)^2 = (n + 1) * (n + 1) := by ring
  rw [h1]
  exact magic_solve n  -- error: unknown identifier
```

**After manual extraction:**

```lean
import Mathlib.Tactic

lemma sum_of_squares_helper_lemma_1 (n : ℕ) (h1 : (n + 1) ^ 2 = (n + 1) * (n + 1)) :
  (n + 1) * (n + 1) = n ^ 2 + 2 * n + 1 := by
  sorry

theorem sum_of_squares_helper (n : ℕ) : (n + 1)^2 = n^2 + 2*n + 1 := by
  have h1 : (n + 1)^2 = (n + 1) * (n + 1) := by ring
  rw [h1]
  exact sum_of_squares_helper_lemma_1 n h1
```

## Best Practices

- **Scope narrowly:** Sorry the specific subgoal or `have` statement, not the entire theorem.
- **Name helpers meaningfully:** Prefer names that encode the parent theorem and proof step.
- **Keep ownership explicit:** If the helper remains unresolved, add or update the corresponding task ledger entry.
- **Next step:** Once extracted, solve the helper independently using search, informal proof tools, or manual Lean work.
