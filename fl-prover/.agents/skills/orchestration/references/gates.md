# Merge Gates

Nothing enters `target/` without passing all four. They are mechanical: run them,
read the JSON, do not argue with it.

```bash
uv run python cli_tools/lean.py check  FILE --compact          # 1. it compiles
uv run python cli_tools/lean.py scan   FILE --plain            # 2. no sorry / admit
uv run python cli_tools/lean.py axioms FILE                    # 3. axiom set is clean
uv run python cli_tools/lean.py guard  check --workspace WS --task T   # 4. statement unchanged
```

## 1. Checking

`lake env lean` over the file. Exit 0 and `"okay": true` means the kernel
accepted every declaration in it. Warnings are not failures, but a warning about
an unused hypothesis in a statement is worth reading — it often means the
statement is weaker than intended.

## 2. Scanning

Real `sorry` / `admit` outside comments and strings. A `sorry` is a proof
obligation with an owner and a next action, never a terminal state, and never
something to hide by moving it into a helper.

## 3. Axioms

`#print axioms` per declaration. The accepted base is `propext`,
`Classical.choice`, `Quot.sound`. Anything else is a finding:

- `sorryAx` — something in the dependency chain is still unproved, even though
  this file scans clean.
- a project-local `axiom` — someone got past a hard step by assuming it. It is a
  proof obligation, and it needs an explicit recorded boundary before it can
  stay.

Widen the accepted set only with `--allow`, only for an assumption the human
approved, and record why in the ledger.

## 4. Guarding

The F-Reviewer approves a statement, `lean.py guard snapshot` freezes it, and
every later gate run re-checks it. If a proof only compiles after the statement
moved, the proof did not succeed — a weakened statement that compiles is the most
expensive failure mode in formalization, because it looks like progress.

Statement changes are legitimate when the F-Reviewer finds the original
formalization unfaithful to the source. That route is: F-Reviewer finding →
Formalizer revision → F-Reviewer approval → new snapshot. Never a silent edit
inside a proof attempt.

## Semantic Fidelity

The detailed criteria live in the `formalize` skill —
`.agents/skills/formalize/reference-reviewer.md` is the F-Reviewer's checklist
(missing hypotheses, weakened conclusion, reversed logical direction, `def` where
the source asserts, source-entailed conditions dropped, universe over-restriction).

The gates are necessary, not sufficient. A file can pass all four and still prove
the wrong theorem, because the compiler checks the Lean statement, not its
correspondence to the source. That correspondence is the F-Reviewer's job, and
the Regulator re-checks it at wave close against the reference the target came
from.

Before a node is accepted as proved, a fresh `statement-readback` agent receives
only the declaration and definitions named by its type. Record its literal
reading in the typed node store with `dag.py put --readback`. This is distinct
from F-Review: the reviewer compares code with the source, while read-back checks
what the code says without being primed by the intended theorem.

For retained build output, `lean.py verdict read` converts the log into an
explicit `PASS`, `FAIL`, or `STALL`; `lean.py verdict audit` records an
independent rerun. These commands audit the evidence for a build claim and do
not replace the four merge gates.
