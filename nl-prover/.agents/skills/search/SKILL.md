---
name: search
description: "Literature search: matlas/arXiv/web retrieval, deep multi-round search, citation-graph traversal, and query indexing"
---

# Search Tools

Everything runs through the `search.py` facade: `uv run python cli_tools/search.py <subcommand> ...`.

## Available Tools

| Subcommand | Purpose | When to use |
|------------|---------|-------------|
| **`search.py matlas`** | Semantic search over 8M+ statements from 435K papers & 1.9K textbooks | Precise theorem, lemma, definition, and terminology search in published literature and textbooks |
| **`search.py arxiv`** | Search arXiv for preprints and recent papers by topic | Alongside matlas for research-level/current topics, recent variants, and papers matlas may not index |
| **harness web search** | General web retrieval | Textbooks, lecture notes, blogs, MathOverflow/MSE, journal pages, GitHub — sources neither matlas nor arXiv reaches |
| **`search.py citation-graph`** | Multi-hop references/cited-by traversal via OpenAlex | Finding a result buried a few citation hops away, or the original source of a theorem only cited secondhand |
| **`search.py frontier`** | Persistent candidate queue for multi-round search | Any search that runs more than one round: makes it interruptible and its cost visible |
| **`search.py index`** | Summarize existing `queries/<id>/` outputs | After query outputs exist, so later agents do not re-read raw dumps |

## Search Strategy

Do not treat matlas and arxiv as interchangeable. They cover different parts of the literature:

- `matlas-search` is strongest when you need exact mathematical statements from indexed published sources and textbooks.
- `arxiv-search` is necessary to complement matlas because arXiv contains preprints, recent work, and results that may not appear in matlas.

For nontrivial research problems, run both:

1. Start with matlas to identify canonical names, theorem statements, and standard formulations.
2. Run arXiv with those names and nearby keywords to find recent papers and missing preprint context.
3. If matlas results are sparse, stale, or too textbook-like, use arXiv to broaden the search before concluding no relevant literature exists.
4. Record both sources in research notes, distinguishing "precise statement from matlas" from "paper/context from arXiv".

In orchestrated proof work, route searches through the problem-local
`queries/<query_id>/` workflow from `prompts/orchestration.md` instead of placing
ad hoc caches under `sketch/` or `generator/`.

After query outputs exist, index them for later agents:

```bash
uv run python cli_tools/search.py index summarize <workspace> --query-id <query_id> --view compact
uv run python cli_tools/search.py index refresh <workspace> --source arxiv --source matlas --source kb-manager
uv run python cli_tools/search.py index latest <workspace> --source matlas --limit 5 --view summary
```

`search.py index` does not replace arXiv, Matlas, or KB-Manager execution. It
summarizes existing `queries/<query_id>/` artifacts and writes source findings
to workspace-local `memory/source_findings.jsonl`.

## Deep search (multi-round)

Use this when one round of matlas/arXiv did not surface the needed premise —
typically because the result is stated only in a textbook or a specialized
paper, sits a few citation hops away, or is a **sub-lemma inside** a paper whose
title looks unrelated.

Guiding rule: **search wide, judge later.** Recall beats precision here. Pass
interesting candidates downstream with honest provenance; correctness is
audited by Auditor (ADR 0019) and a fresh Verifier, not during retrieval.

1. **Check the KB first** — `memory.py read --tier kb`. Do not re-trace a paper
   the KB already holds.
2. **Open the frontier** so the run is interruptible and its cost is visible:

   ```bash
   uv run python cli_tools/search.py frontier init <workspace> \
       --obligation "<statement being sought>" --max-depth 1
   ```

   The hop budget (`--max-depth`) is the **only** stop condition. Default is 1;
   the Orchestrator raises it for a large sweep and leaves it alone for a small
   one. Never silently exceed the budget you were given.
3. **Widen the query.** Build keyword families — synonyms, notation variants,
   older vocabulary — and run each against matlas, arXiv, and web search.
   `push` every plausible hit into the frontier with a score and a `why`.
4. **Deepen along citations.** Where an arXiv id or DOI resolves:

   ```bash
   uv run python cli_tools/search.py citation-graph <seed> \
       --obligation "<statement>" --hops 1 --push-frontier <workspace>
   ```

   Otherwise follow one hop by hand from the paper's reference list. Results
   merge into the same frontier — there is one queue, not two.
5. **Deep-read what you pop.** `search.py frontier next <workspace> --n 3`, then
   go into the body of each hit and extract the actual statement plus its
   preconditions and locator into `knowledge/findings.md`. Do not stop at
   abstracts, and look for sub-lemmas, propositions, and corollaries, not only
   main theorems. `mark` each node when done.
6. **Repeat** until `search.py frontier status <workspace>` shows the hop budget
   exhausted or nothing worthwhile is left queued. Report what the budget cut
   off — a silently truncated search reads as an exhaustive one.

`frontier` and `citation-graph` are mechanical: they store, queue, and rank a
work list. You supply every score and every `why`, and ranking orders work only
— it never decides whether a result is true or usable. `status: skipped` means
"not expanded this round", never "this result is useless".

For full parameters and examples, read the corresponding `reference-<tool>.md` file in this directory.
