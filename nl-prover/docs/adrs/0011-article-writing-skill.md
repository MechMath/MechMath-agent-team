# ADR 0011: Article-Writing Skill and Writer Agent

## Status

Proposed. **Partly superseded** — see the note below.

> **Superseded in part (2026-08-25 back-pointer).** ADR 0021 supersedes the
> progress-note parts of **§3 below** and the export-name parts of this ADR; ADR
> 0025 adds a second stop document. Concretely, three things in the body are no
> longer current: the note is **mandatory** at every non-proof stop, not written
> "when needed"; the file is `writer/progress_notes.tex` and the output type is
> `PROGRESS_NOTES`; and §3's five content bullets are replaced by ADR 0021 §B's
> five numbered sections, whose SSOT is
> `.agents/skills/article-writing/references/progress-note.md`. §3's exclusions
> — no owner or agent scheduling details, no long internal path lists, no
> transcript of which agent did what — survive and are now also enforced on the
> summary by `gate summary`. The rest of this ADR (the Writer agent, the
> `article-writing` skill, the layering, the adoption rules) stands.

This ADR defines a lightweight `article-writing` skill and a matching Writer
subagent. The goal is to turn verified or explicitly state-marked mathematical
material into reader-facing LaTeX prose without letting proof-search agents
become exposition writers.

## Context

NL-Prover already has `proof-summarize`. That skill produces a concise
`proof_summary.tex` from an accepted `proof.tex`, extracts reusable correct/error
notes, and maintains `memory.md` for recurring proof mistakes. Its scope is
correct and should not be split.

The new `article-writing` layer solves a different problem:

> How should verified or explicitly state-marked mathematical material be turned
> into a readable, unified research-note or paper-style main text, candidate
> rewrite, or progress note?

We want the final `proof.tex` to read like a research note or paper, not like an
Orchestrator run log. Writer is not merely a postprocessor that makes a separate
article from `proof.tex`; it produces high-quality candidates that can be
adopted into `proof.tex`, plus local rewrites and progress notes when needed.

The current failure modes are:

- Progress or blocker reports for unfinished proofs often become internal file
  path lists instead of human-readable mathematical progress notes.
- Local rewrites inspect only the selected paragraph and ignore surrounding
  context, causing inconsistent language, notation, environments, and citation
  style.
- `proof.tex` can be a mechanically assembled Orchestrator artifact and should
  not automatically be treated as the style exemplar.

## Decision

Add two layers:

1. Writer subagent: writes `article_candidate.tex`, local rewrite candidates,
   and `progress_note.tex`.
2. `article-writing` skill: the Writer's cookbook for style, grounding, local
   rewrite, and progress-note rules.

The control path is:

```text
nl-prover skill / Orchestrator
  -> writer custom agent
    -> prompts/writer.md
    -> article-writing skill
```

That is, the Orchestrator chooses the Writer custom agent when the current work
is writing work. The execution contract lives in `prompts/writer.md`; the
writing workflow, default templates, and style/grounding details live in the
`article-writing` skill. Other proof-search subagents do not need to load the
article-writing rules, so reader-facing exposition constraints do not leak into
the automatic proof pipeline.

Writer is a writing specialist, not a proof specialist. It does not prove,
verify, recover routes, or decide whether a mathematical conclusion is true. It
only turns verified or explicitly state-marked material into human-readable
text.

## Lightweight V1 Structure

The implementation should stay lightweight, but v1 should directly split a few
references so that `SKILL.md` and `prompts/writer.md` remain short.

```text
.agents/skills/article-writing/
|-- SKILL.md
`-- references/
    |-- style-profile.md
    |-- mathematical-grounding.md
    |-- local-revision.md
    |-- progress-note.md
    `-- latex-research-note-template.md

.codex/agents/writer.toml
prompts/writer.md
```

Responsibilities:

- `SKILL.md`: short trigger guidance and reference map.
- `prompts/writer.md`: Writer input contract, outputs, forbidden actions, and
  done marker.
- `style-profile.md`: how to read or create `writer/style_profile.md`.
- `mathematical-grounding.md`: claim grounding, citation, and TODO rules.
- `local-revision.md`: local rewrite workflow.
- `progress-note.md`: human-facing explanation format for unfinished proofs.
- `latex-research-note-template.md`: default research-note/paper LaTeX
  structure.

## Writer Workspace

Writer writes only under `writer/`.

```text
writer/
|-- style_profile.md
|-- article_plan.md
|-- article_candidate.tex
|-- local_revision_candidate.tex
|-- progress_note.tex
`-- revision_notes.md
```

Rules:

- Full article output goes to `writer/article_candidate.tex`.
- Local rewrites go to `writer/local_revision_candidate.tex` or a patch-style
  candidate.
- Unfinished proof progress explanations go to `writer/progress_note.tex`.
- `style_profile.md` lives under `writer/` and does not pollute the main
  workspace.
- Markdown is for plans and notes; formal reader-facing output is preferably
  `.tex`.
- Writer does not modify `proof.tex` by default. The Orchestrator or human
  adopts a candidate only after review.

## Verification / Adoption

Writer output is not automatically adopted.

Before a full article candidate or local rewrite enters `proof.tex`, it needs an
appropriate check:

- If the candidate only changes layout, language, or structure, the Orchestrator
  may do mechanical checks and diff review.
- If the candidate may change a theorem statement, hypotheses, proof logic,
  citation claim, or mathematical meaning, it must go to Verifier or the
  corresponding specialist.
- For `writer/article_candidate.tex`, at least one Verifier-facing consistency
  check is recommended: confirm that theorem statements, hypotheses,
  dependencies, and the verified proof route were not changed.

## Default Article Norms

Unless the user gives explicit style instructions, default to:

- English;
- research note / paper;
- LaTeX;
- no agent execution history;
- no blog or public-account style;
- do not write Chinese merely because the conversation is in Chinese;
- mathematical claims come from verified material or explicitly marked
  progress/restart state;
- citations must come from existing sources or be marked `TODO`; do not invent
  references;
- theorem/proof environments are clear, notation is stable, and hypotheses are
  not hidden;
- intuition may be included, but it must be separated from formal proof.

## Use Cases

### 1. Full Article Candidate

Generate `writer/article_candidate.tex` from completed or near-completed
material. The intended result is a research-note/paper version that can later be
adopted as `proof.tex`.

Writer should:

- read the accepted proof, target contract, source packages, and review packets;
- write `writer/article_plan.md` when helpful;
- write unified LaTeX prose;
- preserve theorem statements and hypotheses;
- avoid introducing new mathematics.

### 2. Local Rewrite

Rewrite part of an existing proof or article.

Writer should:

- read surrounding context;
- create or reuse `writer/style_profile.md`;
- preserve language, notation, theorem environments, citation style, and
  explanatory granularity;
- output a candidate `.tex` or patch;
- stop and hand the issue back to the proof pipeline if mathematical content
  must change.

`proof.tex` may be a mechanically merged Orchestrator artifact. If its style is
poor or inconsistent, Writer should use the default research-note/paper format
instead of imitating bad formatting.

### 3. Progress Note

When the proof is not complete, Writer may write `writer/progress_note.tex`, but
it must state that the text is not a final mathematical result.

It should explain:

- what the current problem is;
- which mathematical routes have been tried;
- why those routes are unavailable or only route state;
- what the core blocker is;
- what kind of idea, construction, theorem, or evidence is needed next.

It should not include:

- owner or agent scheduling details;
- long internal file path lists;
- a transcript of which agent did what.

Internal files may be evidence sources, but the body should explain the
mathematics. If necessary, add a short evidence note at the end instead of
letting paths dominate the article.

## Boundary With Existing Workflows

### `proof-summarize`

Keep it as-is. It remains responsible for:

- `proof_summary.tex`;
- reusable correct/error notes;
- recurring-error memory in `memory.md`.

Do not split it and do not let `article-writing` take over memory.

### `article-writing` / Writer

Responsible for:

- full article candidates;
- local rewrite candidates;
- progress notes;
- style profiles;
- LaTeX research-note/paper exposition.

### `proof-recovery`

When the state is restartable rather than solved, Writer may only write a
progress note. It must not continue proving, and it must not present a blocker
as a final result.

### `verification`

If a writing candidate may change mathematical content, it must go through
Verifier or the corresponding specialist. Writer does not judge correctness.

## Inputs

Writer may read:

- `problem.md`;
- `proof.tex`;
- `proof_summary.tex`;
- `STATUS.md`;
- accepted review packets;
- source-theorem packages;
- target contract;
- route recovery packets;
- human-provided audience/style/venue instructions;
- existing article/proof context for style matching.

## Writer Prompt Requirements

`prompts/writer.md` must say:

- do not prove;
- do not verify;
- do not do recovery;
- do not modify `proof.tex` by default;
- write only under `writer/`;
- the primary output is `.tex`;
- default to English research note / paper style;
- do not write agent history by default;
- local rewrite requires surrounding context;
- if mathematical content must change, stop and hand the issue back to the
  proof pipeline.

## Writing Workflow

### 1. Output Contract

Record:

- output type: full article, local rewrite, or progress note;
- language: English by default unless the user explicitly asks for Chinese;
- output file;
- whether proof-search work is allowed;
- citation policy.

### 2. Style Profile

Record style in `writer/style_profile.md`.

If no reliable style context exists, use the default research-note/paper format.
Do not blindly imitate `proof.tex` merely because it exists.

### 3. Article Plan

For a full article candidate, write `writer/article_plan.md` when useful. Do not
force every section to exist.

Optional sections:

- main theorem;
- motivation;
- notation setup;
- proof idea;
- technical lemmas;
- remarks/examples when genuinely useful;
- final proof route;
- citation obligations.

### 4. Grounding Pass

Every substantive mathematical claim must come from one of:

- accepted `proof.tex`;
- accepted `proof_summary.tex`;
- accepted Verifier packet;
- source-theorem package;
- human instruction;
- route artifact explicitly marked as progress/restart state.

When a citation is needed, preserve an existing citation or write `TODO`. Do not
invent references.

### 5. Draft

While drafting:

- introduce the problem and main result first;
- introduce notation before dense formulas;
- keep theorem/proof structure clear;
- separate intuition from formal proof;
- do not hide hypotheses;
- do not use internal file paths as a substitute for mathematical explanation;
- do not write agent history unless the output is a progress note;
- do not add unnecessary examples, figures, or background.

### 6. Review

Before finishing, check:

- theorem statement changed or not;
- hypotheses changed or not;
- proof logic changed or not;
- notation consistency;
- citation is real or marked `TODO`;
- progress/restart state was not presented as a result;
- local rewrite matches surrounding style;
- primary output is a `.tex` file.

## Acceptance Criteria

Implementation is acceptable when:

- a lightweight `article-writing` skill and the references above exist;
- a Writer custom agent exists;
- the `nl-prover` skill or Orchestrator can route writing requests to
  Writer, and Writer can load the `article-writing` skill;
- full article, local rewrite, and progress note are distinguished;
- default output is `.tex`;
- default language/style is English research note / paper;
- conversation language alone does not change article language;
- unfinished proofs produce only progress notes, not final results;
- progress notes do not expose owner/agent scheduling details;
- local rewrite reads surrounding context;
- style profile is written to `writer/style_profile.md`;
- Writer does not blindly imitate bad Orchestrator-generated `proof.tex`
  formatting;
- full article candidates may include an article plan, but unused sections may
  be skipped;
- mathematical claims are grounded;
- citations are real or marked `TODO`;
- Writer does not modify `proof.tex` by default;
- adoption of article candidates has mechanical diff review and, when needed,
  Verifier consistency checking.
