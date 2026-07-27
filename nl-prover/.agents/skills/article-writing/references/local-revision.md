# Local Revision

Use this workflow when revising one section, theorem, proof paragraph, or
expository passage.

## Required Context

Read the selected passage and enough surrounding context to match:

- theorem/proof environment style;
- notation and symbol names;
- language and tense;
- citation style;
- level of explanation;
- dependencies introduced before and after the passage.

If the surrounding context is poor because it is mechanically merged, preserve
the accepted mathematical content but use the default research-note/paper style
from `style-profile.md`.

## Output

Write one of:

- `writer/local_revision_candidate.tex` for replacement prose;
- a clearly marked patch-style candidate in the same file when exact placement
  matters.

Also update `writer/revision_notes.md` with:

- source files read;
- target passage;
- whether the revision is mechanical/expository only;
- any citation or grounding TODOs;
- whether adoption needs Verifier consistency review.

## Do Not

- rewrite adjacent unrelated sections;
- change theorem statements, hypotheses, or proof logic;
- silently normalize notation in a way that changes meaning;
- remove a load-bearing detail just to improve flow;
- introduce examples, remarks, or background unless requested or clearly useful.

If the local revision exposes a mathematical issue, stop and write a handoff
request instead of repairing it inside Writer.
