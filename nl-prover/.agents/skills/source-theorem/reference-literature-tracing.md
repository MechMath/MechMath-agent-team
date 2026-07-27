# Literature Tracing Reference

Use this reference before writing a source theorem package. The goal is to find
the original or best usable statement, not to accumulate search hits.

## Layered Search

Run only the layers needed for the current obligation, but record every layer
attempted.

1. Local references:

```bash
uv run python cli_tools/workspace.py references scan <workspace>
uv run python cli_tools/workspace.py references search <workspace> "<query>"
uv run python cli_tools/workspace.py references show <workspace> <reference_id>
```

2. Existing query outputs:

```bash
uv run python cli_tools/search.py index latest <workspace>
uv run python cli_tools/search.py index summarize <workspace>
```

3. Lightweight workspace memory, when relevant:

```bash
uv run python cli_tools/memory.py read --tier local <workspace>
uv run python cli_tools/memory.py read --tier local <workspace> --query "<query>"
```

4. Matlas and arXiv tools:

```bash
uv run python cli_tools/search.py matlas "<query>"
uv run python cli_tools/search.py arxiv "<query>"
```

If a tool is unavailable, rate-limited, or sparse, record that fact and continue
with another layer or a local derivation branch.

## Paper Card

When a paper is retained, write a compact card for later agents.

`references/papers/<paper_id>/note.md`:

```markdown
# Paper Card: <title>

## Bibliographic Data
- Title:
- Authors:
- Year:
- URL or arXiv:
- Local file:

## Why This Paper Was Kept
- Current obligation:
- Matching terms:
- Relevant theorem/lemma/proposition numbers:

## Usable Statements
- <statement id>: <short exact statement or pointer into statements.jsonl>

## Preconditions and Conventions
- <hypothesis, convention, parameter range, notation>

## Fit To Current Route
- Directly usable: YES | NO | UNCLEAR
- Bridge obligations:
- Circularity risk:
- Strength mismatch:

## Rejected Uses
- <claim that looked relevant but is not usable, with reason>
```

`references/papers/<paper_id>/statements.jsonl`:

```jsonl
{"id":"thm-1","locator":"Theorem 2.3","statement":"...","hypotheses":["..."],"conclusion":"...","source_quality":"original theorem|secondary mention|derived in paper","fit":"direct|bridge-needed|not-usable"}
```

`references/papers/<paper_id>/citation_trail.md`:

```markdown
# Citation Trail

## Entry Point
- Found from:
- Query or paper:

## References Followed
| Depth | Cited work | Reason followed | Result |
|-------|------------|-----------------|--------|

## Stopping Reason
- original statement found | secondary mention only | no accessible source |
- next recommended trace:
```

## Source Availability Is Not A Terminal Result

If no usable theorem is found, write a restartable trace:

- keyword families attempted;
- local references and query outputs read;
- candidate papers rejected and reasons;
- citation layers followed;
- exact missing statement or precondition;
- next owner: Searcher, Auditor, Generator for local
  derivation, Sketcher for route change, Regulator for mixed ownership, or
  Human for unavailable external material.
