# ADR 0012: Rethlas-Inspired Tooling, PDF Pre-Extraction, and AI-Readable Indexes

## Status

Proposed.

## Context

This ADR compares NL-Prover with `/data/caosip/github/Rethlas`. The
decision is: **do not change NL-Prover's architecture**. NL-Prover
keeps the current hub-and-spoke specialist system. It will not become a single
generation agent, and it will not adopt Rethlas's verification service.

The useful idea is the tooling layer:

1. search, memory, and branch-state actions should be exposed as
   `skill + cli_tools`;
2. PDF references should be pre-extracted before a proof run;
3. workspace state should have short AI-readable indexes instead of forcing
   agents to repeatedly read long `STATUS.md` files and scattered artifacts;
4. tools need information-granularity controls: short by default, expandable by
   parameters when detailed evidence is needed.

The core idea is not MCP itself. The core idea is: **skills tell agents when to
use tools; CLI tools perform deterministic execution, caching, indexing, and
file writes**.

## Existing Problem

NL-Prover already has:

- `STATUS.md`: current run summary and active branch queue;
- `recovery/` and `route_history.md`: failed routes and recovery evidence;
- `queries/<query_id>/`: Collector / Matlas / arXiv query workflow;
- `memory.md`: cross-task recurring-error memory;
- Writer outputs: `well-written-proof.pdf` and `well-written-progress.pdf`.

The problem is not lack of records. The problem is that these records are
mostly maintained by prompt discipline. In long runs, `STATUS.md` can grow,
route/recovery/query/presentation artifacts become scattered, and later agents
spend context rediscovering the workspace.

This ADR makes existing files tool-writable and AI-readable through short
indexes. Agents should be able to request `compact -> summary -> full`
granularity instead of reading whole directories.

## Rethlas Ideas To Borrow

Rethlas's generation MCP server exposes:

- `search_arxiv_theorems(query, num_results)`: sends theorem-shaped searches to
  an endpoint and returns theorem-shaped results. NL-Prover should not
  adopt this directly because it already has arXiv / Matlas / Collector tools
  and is not Lean/formal-first.
- `memory_init(problem_id, meta)`: initializes problem-local JSONL memory
  channels.
- `memory_append(problem_id, channel, record)`: appends a JSON record to a
  channel.
- `memory_search(problem_id, query, channels, limit_per_channel)`: runs BM25
  search over JSONL memory.
- `branch_update(problem_id, branch_id, state)`: appends structured branch
  state to the `branch_states` channel.
- `verify_proof_service(statement, proof)`: local HTTP verification service.

NL-Prover should not adopt `verify_proof_service`, and should not add a
LeanSearch-style theorem-search entrypoint. The ideas to adopt are memory and
branch state: memory channels, structured branch updates, and length-controlled
memory output. Existing search tools such as Matlas should only be connected to
the unified indexes.

## Decision

### 1. Tool Design: Skill + CLI + Granularity

Each new capability has two layers:

```text
.agents/skills/<skill>/SKILL.md
  -> trigger timing, input paths, output paths, common commands,
     and when to use compact/summary/full

cli_tools/<tool>.py
  -> deterministic execution: search, extraction, indexing,
     JSONL append, markdown summary generation
```

Tool output is short by default. Parameters control granularity:

- `--format json|md|plain`: for tools, agents, or humans;
- `--view compact|summary|full`: controls output length;
- `--limit N`: controls item count;
- `--channel ...`, `--kind ...`, `--owner ...`: controls search scope;
- `--source <path>`: extracts from a concrete source artifact;
- `--refresh` / `--force`: controls cache updates;
- `--include-static` / `--include-context`: explicitly requests heavier output.

This follows the design philosophy of
`/data/caosip/github/Prover/docs/adrs/0003-lean-local-inspection-cli-tools.md`:
agents should not read full files for local questions; they should request the
smallest sufficient view.

### 2. Existing Search/query Tools Join The Index

The existing `queries/<query_id>/` workflow and arXiv / Matlas / Collector tools
remain. This ADR does not add a new search tool. It adds a thin index wrapper
that normalizes and summarizes existing query results, then writes them to
workspace memory.

```text
uv run python cli_tools/query_index.py summarize <workspace> \
  --query-id <id> --view compact

uv run python cli_tools/query_index.py refresh <workspace> \
  --source arxiv --source matlas --source collector

uv run python cli_tools/query_index.py latest <workspace> \
  --source matlas --limit 5 --view summary
```

Responsibilities:

- read existing `queries/<query_id>/request.md`, `status.md`, `arxiv.md`,
  `matlas.md`, and `collector.md`;
- generate short summaries containing query purpose, source, success/failure
  state, reusable findings, and source paths;
- write source-theorem or literature findings to `memory/source_findings.jsonl`;
- support `latest` so agents can read the most recent N queries without scanning
  all of `queries/`;
- not replace the existing arXiv / Matlas / Collector execution tools.

This must be tested for failed queries, empty results, HTTP 429 retry states,
and duplicate-query caching behavior.

### 3. Workspace Memory Ledger

Each workspace gains:

```text
memory/
|-- branch_states.jsonl
|-- failed_paths.jsonl
|-- proof_steps.jsonl
|-- verification_reports.jsonl
|-- source_findings.jsonl
|-- presentation.jsonl
`-- events.jsonl
```

Channel meanings:

- `branch_states.jsonl`: active/queued/blocked/rejected/done branch snapshots;
- `failed_paths.jsonl`: failed routes, reasons, evidence paths, reusable work;
- `proof_steps.jsonl`: index of accepted or candidate proof steps; not a
  replacement for `proof.tex`;
- `verification_reports.jsonl`: Verifier verdicts, packet paths, merge-blocker
  summaries;
- `source_findings.jsonl`: Searcher, Collector, Matlas, and arXiv
  usable/unusable findings;
- `presentation.jsonl`: Writer outputs, well-written PDFs, progress PDFs,
  presentation failures;
- `events.jsonl`: runtime events that do not fit another channel.

CLI design:

```text
uv run python cli_tools/workspace_memory.py refresh <workspace> \
  --view compact

uv run python cli_tools/workspace_memory.py append <workspace> \
  --channel failed_paths --source <path> --kind verifier_reject

uv run python cli_tools/workspace_memory.py search <workspace> \
  --query <text> --channel branch_states --channel failed_paths --limit 5

uv run python cli_tools/workspace_memory.py show <workspace> \
  --channel verification_reports --view summary --latest 10
```

Principles:

- source-of-truth artifacts remain `proof.tex`, `STATUS.md`, `recovery/`,
  `queries/`, Verifier packets, and other owned artifacts;
- `memory/*.jsonl` is an index, not proof evidence;
- specialists write their own source artifacts, while the memory ledger is
  generated or appended by CLI tools;
- before choosing the next step, the Orchestrator must call `refresh` or
  `search` instead of scanning the whole workspace (a required per-cycle
  precondition per ADR 0020, not optional).

### 4. PDF Reference Pre-Extraction Tool

Use workspace-local references:

```text
<workspace>/references/
<workspace>/references/.extracted/
```

Supported files: `.md`, `.tex`, `.txt`, `.pdf`. PDFs are extracted as:

```text
references/foo.pdf
  -> references/.extracted/foo.txt
```

CLI design:

```text
uv run python cli_tools/reference_extract.py scan <workspace> \
  --view compact

uv run python cli_tools/reference_extract.py extract <workspace> \
  --backend pdftotext --view summary

uv run python cli_tools/reference_extract.py show <workspace> \
  --ref foo.pdf --page 3 --context-lines 20

uv run python cli_tools/reference_extract.py search <workspace> \
  --query <text> --limit 5 --view summary
```

Details:

- `scan` lists references, sizes, mtimes, extraction status, and stale status;
- `extract` calls `pdftotext -layout` for PDFs and indexes non-PDF text files;
- `.extracted/meta.json` records source path, size, mtime, hash, backend,
  extraction time, and failure reason;
- unchanged PDFs are not re-extracted unless `--force` is used;
- `show` returns snippets by reference, page, or line range;
- `search` runs lightweight keyword/BM25 search over extracted text;
- each run writes `references/index.json` and `references/index.md`;
- extraction failures are recorded explicitly and never silently skipped.

This must be tested for missing `references/`, successful PDF extraction,
cache hits, `--force`, extraction failure reporting, and snippet/search output
that does not dump whole PDFs into context.

Agents should inspect `references/index.*` or call `show/search` before proof
runs, searches, Searcher work, or Auditor work. Local
references are source material, not verified facts. Any theorem that carries a
proof still requires Searcher or Verifier checking.

### 5. Presentation/static Index Tool

Add:

```text
presentation/index.json
presentation/index.md
presentation/static/
```

Relationship:

- `STATUS.md` remains the current run summary;
- `memory/*.jsonl` records process indexes;
- `presentation/index.*` records display-ready artifacts and AI entrypoints;
- `presentation/static/` is not UI; it is a normalized markdown/tex mirror.

This entrypoint is primarily for AI and tools: it tells later agents which
files to read. `index.md` can also be skimmed by humans, but it is not the
formal report. Human-facing output remains Writer PDFs or progress notes.

CLI design:

```text
uv run python cli_tools/presentation_index.py build <workspace> \
  --view compact

uv run python cli_tools/presentation_index.py show <workspace> \
  --section proof --view summary

uv run python cli_tools/presentation_index.py latest <workspace> \
  --section presentation --limit 5 --view compact

uv run python cli_tools/presentation_index.py sync-static <workspace> \
  --include writer --include recovery --include source
```

`index.json` contains:

- current mathematical status;
- authoritative proof path;
- active/recovery state entrypoints;
- proof summary;
- well-written proof/progress PDFs;
- Writer tex files;
- source theorem package paths;
- last update time;
- presentation failure status and failure files.

Granularity:

- `build --view compact`: paths, status, timestamps;
- `build --view summary`: short summaries and next action;
- `show --section ...`: expands one section such as proof, writer, recovery,
  source, or verification;
- `latest --limit N`: reads recent presentation / recovery / verification
  records;
- `sync-static`: explicitly generates heavier text mirrors; default build does
  not.

## Non-Adoptions

- no Rethlas verification service;
- no single generation-agent architecture;
- no UI;
- no replacement of `proof.tex`, Verifier packets, or original query outputs by
  memory ledger records.

## Implementation Order

1. Add the PDF reference pre-extraction CLI and `references/` convention.
2. Add the presentation index CLI.
3. Add the workspace memory CLI.
4. Add the query-index thin wrapper so existing arXiv / Matlas / Collector
   outputs can write into unified memory/index files.

## Open Questions

1. Should `references/` be workspace-only, or should a project-level shared
   reference directory also be supported?
2. Should memory ledger entries be fully generated from source files, or may
   the Orchestrator actively append selected records?
3. Should `presentation/static/` mirror only Writer outputs, or also
   verifier/source/recovery summaries?
4. Which comes first after this ADR: search upgrades or removing structural
   verification?
