---
name: compute-budget
description: "Use immediately before running a program, starting a search or sweep, or launching any computation that is not instant — sizing memory, wall clock, and output so a shared machine is not wedged, and so a terminated run is not mistaken for a mathematical answer. Trigger on: about to execute code, run a script, start a REPL session, launch a sweep or enumeration, PSLQ or lattice reduction, symbolic computation, or any loop whose bound is not obviously small."
---

# Compute Budget

You are about to run something. This machine is shared — with other agents in
this run, with concurrent runs, and with the human. Nothing terminates a runaway
process for you.

## Size it before you write it

Answer these before the first line of code, not after the first hang:

- **How many iterations?** If you cannot bound it, the loop needs an explicit
  cap, and the cap needs to appear in the output so a truncated run is
  recognisable as truncated.
- **How much memory at peak?** Anything that materialises a full product,
  power set, or dense matrix is worth an estimate. An order of magnitude is
  enough.
- **How long?** Estimate from a small case and extrapolate. This is nearly free
  and catches the three-orders-of-magnitude mistakes, which are the ones that
  actually hurt.
- **How much output?** A large printed result costs more than the computation
  that produced it, because every downstream reader carries it. Write bulk to a
  file and print a summary.

## Start small, then scale

Run the smallest case that could show the effect. Confirm the shape of the
answer. Then scale, in steps you could stop between.

This is not caution for its own sake: a small case that behaves unexpectedly
tells you more than a large one that never finishes, and a decisive experiment is
often seconds long. In one run the experiment that would have settled the
question cost 0.455 seconds.

## Concurrency

Several agents may be computing at once. Prefer several short runs to one long
one; a long single run holds resources through every other agent's turn.

Nothing coordinates this automatically. Assume you are not alone.

## The rule that matters most

**A terminated or truncated computation is a resource fact, not a mathematical
one.**

If a run is killed, times out, exhausts memory, or hits a cap you set: make the
experiment smaller and retry. Report it as what it is.

**Never conclude that an object does not exist, that a bound fails, or that a
route is dead because a computation did not finish.** A route closes only on an
exact counterexample or a certification-mode Verifier FAIL. Recording a resource
limit as a mathematical result is the specific failure this rule exists to
prevent, and it has cost entire routes.

## Reporting

An empty result is about the frame you searched, not about the object:

```
NO_RESULT_IN_DECLARED_SCOPE
  searched: <the frame actually covered>
  next:     <a different frame, stated explicitly>
```

A cut-off result is neither of those — say it was cut off, say at what size, and
say what you will try next.
