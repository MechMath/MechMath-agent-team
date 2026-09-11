# ADR 0007: arXiv Search and Research Integration

## Status
Accepted

## Context

Many mathematical problems — especially at competition or research level — benefit from knowledge of existing results, techniques, and related work. An agent that approaches a problem "from scratch" may waste significant effort rediscovering known results or attempting dead-end strategies that the literature has already explored.

The Prover project integrates multiple search tools (leandex, loogle, leansearch, state_search) for formal proof search. The Collector project provides a persistent knowledge base with ingestion and query capabilities. NL-Prover needs analogous research capabilities for informal mathematics.

Update: deep Collector reads are now handled by the project-scoped `collector`
Codex custom agent, which reads local Collector/wiki files directly and writes a
query result file. The old CLI wrapper has been removed.

Update: arXiv, Matlas, and Collector queries now share the problem-local
`queries/<query_id>/` workflow described in `prompts/orchestration.md`. Older cache
paths under `sketch/` are historical.

## Decision

### Research Tools Available to Agents

#### 1. arXiv Search (`arxiv-search` skill)

Searches arXiv for papers related to a mathematical topic or technique.

**CLI**: `uv run python cli_tools/arxiv_search.py "query" [--max-results N] [--max-retries N]`

**Output**: Structured results with title, authors, abstract, arXiv ID, and PDF link.

**Caching**: Results are cached under `workspace/<problem_id>/queries/<query_id>/arxiv/` to avoid duplicate API calls and keep all query outputs together.

**Primary user**: Orchestrator, when executing a Sketcher or Generator query request.

#### 2. Web Search

General-purpose web search for mathematical references, technique descriptions, and encyclopedia entries.

**Tool**: Built-in WebSearch tool.

**Primary user**: Orchestrator, when executing a Sketcher or Generator query
request. Sketcher and Generator agents request web-backed research through the
same problem-local query workflow instead of calling web tools directly.

#### 3. Collector Knowledge Base Integration

If the Collector project is configured (via `COLLECTOR_DIR` environment variable), the Orchestrator can route queries to the accumulated mathematical knowledge base.

**Summary** (zero-cost index scan): `uv run python cli_tools/collector_summary.py` — lists concept pages and analysis/comparison pages currently indexed in the Collector wiki. Reads the local `index.md` directly — no API call, no token cost. The Orchestrator calls this before a deep Collector query to see what is available and narrow the query scope.

**Read** (deep query): spawn the `collector` custom agent through the unified `queries/<query_id>/` workflow. The agent reads local Collector/wiki files directly and writes `collector.md`.

**Write**: `uv run python cli_tools/collector_write.py <file>` — drops files into Collector's inbox for later ingestion. Use this to save proven results back to the knowledge base.

**Primary users**:
- Sketcher and Generator: identify research needs and request Collector queries through `queries/<query_id>/`; they do not execute Collector CLIs directly.
- Orchestrator: calls `collector_summary.py` before deep Collector reads, routes Collector query requests, and calls `collector_write.py` to save verified results.
- Collector custom agent: reads `wiki/index.md` and the smallest relevant set of local wiki pages, including concept, source, Lean, and analysis pages.

### Research Protocol for the Sketcher

1. **Read the problem statement** — identify key mathematical objects, theorems, and techniques
2. **Request local analysis preflight when relevant** — if prior methods, proof-hygiene warnings, previous failures, or counterexamples may matter, request `Sources Requested: collector` only so the Collector checks local `Analysis_*`, `*ErrorKnowledge`, and `*CounterexampleKnowledge` pages
3. **Identify separate research needs** — for each nontrivial theorem lookup, literature search, ordinary Collector/wiki read, or outside discussion need, choose `collector`, `matlas`, `arxiv`, or `all`
4. **Request research through the Orchestrator** — print `QUERY_REQUESTED ...`, or draft `queries/<query_id>/request.md` only when the Orchestrator explicitly asks for that file
5. **Wait for returned query outputs** — the Orchestrator executes Matlas, arXiv, web-backed research, and Collector summary/routing; Collector writes `collector.md`
6. **Synthesize** — read `queries/<query_id>/matlas.md`, `arxiv.md`, and/or `collector.md`, then write `research_notes.md` summarizing findings and how they inform the decomposition
7. **Propagate analysis risks to Verifier** — if local analysis preflight found relevant warnings, add `Analysis Preflight For Verifier` to `sketch/decomposition.md` and `Verifier Risk Checklist` to each affected lemma statement
8. **Cite sources** — reference specific papers/results/local wiki pages in `decomposition.md` and `statement.md`

### What NOT to Research

- Do not spend time searching when the problem is straightforward (e.g., basic calculus, linear algebra)
- Do not attempt to find a complete solution online — the goal is to find relevant techniques and background, not to copy an existing proof
- Do not trust arXiv preprints blindly — note the citation as context but verify the claimed results independently
- Do not let Sketcher or Generator execute research CLIs, web tools, or Collector reads directly; these agents request research and consume Orchestrator-returned files.
- Do not attach Matlas or arXiv to analysis-page preflight queries. Analysis pages are local Collector memory only; create a separate theorem/literature query if external sources are needed.

## Consequences

### Pros
- **Informed decomposition** — the Sketcher can leverage known techniques instead of reinventing them
- **Reduced dead ends** — literature awareness helps avoid known impossibility results or hard barriers
- **Knowledge accumulation** — verified proofs fed back to Collector build institutional memory across sessions
- **Proper attribution** — research notes create an audit trail of which external results informed the proof

### Cons
- **Research time** — routed arXiv, Matlas, Collector, and web-backed searches add latency to the sketching phase
- **Distraction risk** — excessive research can delay proof work; the Sketcher must balance breadth vs. depth
- **Quality variance** — web sources vary in reliability; agents must be skeptical of unvetted claims
- **API dependencies** — arXiv API and web-backed research require internet access
