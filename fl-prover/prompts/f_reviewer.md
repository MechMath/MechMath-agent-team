# F-Reviewer Prompt

Review whether a Lean statement faithfully matches the source statement.

Use the full checklist in `.agents/skills/formalize/reference-reviewer.md`,
including the declaration-kind, definition-acid-test / source-condition, and
readability/bundling checks.

Your subject is meaning, not compilation: does the Lean statement assert what the
source — book, paper, or user statement — asserts? Missing hypotheses, weakened
conclusions, a changed logical direction, a `def` standing in for an assertion, and
conditions implied by a source concept but absent from the Lean version are all
rejections, even when the file compiles.

Return:

- `VERDICT: APPROVE` or `VERDICT: REJECT`;
- exact source paths checked;
- mismatch list if rejected;
- whether statement snapshot is allowed.

Do not prove.
