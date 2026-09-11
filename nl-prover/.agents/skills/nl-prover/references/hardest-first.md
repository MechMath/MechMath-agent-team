# Assemble before you prove

## The failure this exists to prevent

A target is decomposed into lemmas, the lemmas are proved one after another because each
is tractable, and the assembly is attempted last — where it turns out the decomposition
never closed the target. Everything proved on top of the missing step is spent, and the
run reported progress the whole way: seven lemmas accepted is seven lemmas accepted, and
it is also nothing at all if the eighth cannot exist.

This is not a scheduling preference. It is what the harness already knows and does not
act on: `gate dag` computes the assembly node and reports when nothing above it vouches
for it — *"top node X — nothing above it depends on it, so no accepted lemma in this
workspace vouches for it"* — and that finding is advisory.

## What to do instead

**A lemma is usable by the assembly as soon as it is stated.** `dag.py` calls that state
`statement-only`, and it is the normal state for a lemma the Sketcher has written and
nobody has proved. The assembly argument needs the lemma's *statement*, not its proof —
`prompts/sketcher.md` says so itself when it rejects the edge *"B uses the object A
constructs"*.

So:

1. The Sketcher states the whole decomposition, and names the **keystone** — the lemma
   that, if it fails, makes the rest pointless.
2. The assembly is written against the stated lemmas, before any of them is proved. If it
   does not close the target, the finding is a decomposition defect and it has cost one
   round instead of the whole run.
3. Only then are the lemmas dispatched — and they go out the way this harness dispatches
   everything else: every independent blocker in one batch, up to six.

## This does not make a queue

`orchestrator-cookbook.md` is right that listing one smallest blocker is what turns a set
of independent lemmas into a queue, and that the question is "what is blocked *right
now*", not "*first*". Nothing here changes that. Everything independent still goes out
together.

The rule applies only where a choice is forced — the frontier is wider than the batch
cap, or two blockers contend for one specialist. Then rank by the two dimensions the
Synthesizer already ranks routes on (`prompts/synthesizer.md`, "How To Rank"):

- **Feasibility** — can this be walked with current capability?
- **Contribution** — if its central claim holds, how much of the target closes?

The assembly node carries the highest Contribution there is: if it holds, the target
closes. That is why it goes out early, and it is the same rule already in use one level
up, not a new one.

And the ban that comes with it applies here too: **do not rank by how checkable it
looks.** That is exactly the reading that spends a run on the tractable lemmas.

## The judgement you still have to make

An accepted lemma is durable: it survives in `proof.tex`, it can be cited, and a later
route can reuse it. A run that spends everything on an assembly that will not close
produces nothing. So the rule is not "always do the hard thing first" — it is **test the
decomposition before you invest in it**, which step 2 does cheaply because the lemmas are
only stated.

When the assembly is plainly out of reach this cycle, say so in `STATUS.md` and work the
lemmas deliberately — as a decision with a reason, not by default because they were the
ones that were easy.

## What the harness checks

- `gate dag` reports the assembly node and whether anything accepted vouches for it.
- `workspace status` names the target beside the lemma count, so `7/8 PASS` no longer
  reads as progress when the eighth is the assembly.
- `gate summary` refuses a numeric distance-to-proof in the stop document; the blocker is
  required above the achievements.
