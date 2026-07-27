# Stop Conditions

A run stops for exactly four reasons.

1. **Done.** The target compiles, scans clean, its axiom set is exactly the
   accepted base plus explicitly recorded assumptions, every protected statement
   still matches its snapshot, and the Regulator's final audit passes.
2. **Documented infeasibility.** A formalization boundary that is not a matter of
   effort — e.g. the source result depends on a theory Mathlib does not have, and
   the missing development is named and scoped.
3. **Genuine human ambiguity.** The source is unclear in a way no reading
   resolves, and guessing would formalize the wrong theorem.
4. **Documented budget exhaustion.** The branch queue is empty and each closed
   branch says why.

One failed specialist cycle is not exhaustion. A failing F-Generator means: pop
the next ledger task, or dispatch the Blueprinter to decompose the failing one.

## Before Any Stop

Every stop pays into the next run, whether or not the target was proved:

```bash
uv run python cli_tools/memory.py refresh <workspace>
uv run python cli_tools/memory.py aggregate-candidates <workspace>
uv run python cli_tools/gate.py stop <workspace> [--verified-proof]
```

`aggregate-candidates` dedups `memory/candidates/*.jsonl`, promotes the survivors
into `memory/experience/`, and re-renders `memory.md`. Without it, everything the
run learned dies in the workspace.

`gate stop` is mechanical and must pass: the local index is fresh, the long-term
tier was read this run, a run that recorded failures captured a lesson (a
candidate card, or an explicit `no_constraint` marker when there is genuinely
nothing to learn), candidates were promoted, and the stop left its export. Fix
what it reports rather than stopping past it.

Also close the ledger and the wave: the final `control.py wave` summary is what
makes the run restartable by someone who was not here.
