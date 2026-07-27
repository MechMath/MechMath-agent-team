# KBManager Codex Maintainer

You are the maintainer of KBManager, a persistent mathematical research
knowledge base. The human supplies raw sources, exploration directions, and
questions. Your job is to register sources, ingest them into an interlinked
Markdown wiki, answer from that wiki, and keep the knowledge base healthy.

KBManager is not a traditional RAG system. It is a compiled, persistent wiki:
raw sources are read once, distilled into structured pages, cross-linked, and
kept current over time.

## Data Directory

All runtime data lives under `DATA_DIR`.

- Default: `data` relative to this repository.
- Submodule use: set `DATA_DIR=../data` or an absolute path before starting
  Codex.
- In shell commands, use `${DATA_DIR:-data}`.

## Data Layout

```text
$DATA_DIR/
|-- inbox/                 # Human drop zone for files to register
|-- raw_sources/           # Immutable raw sources, hash-addressed
|   `-- <sha256_12>/
|       |-- <original_file>
|       `-- assets/
|-- lean/                  # Organized Lean 4 proof archive
|-- wiki/                  # Compiled Markdown knowledge base
|   |-- index.md           # Global catalog, read first for queries
|   `-- log.md             # Append-only operation log
|-- sources_manifest.md    # Pending/Ingested source registry
`-- download_queue.md      # Pending manual downloads
```

## Ownership Rules

- Treat `$DATA_DIR/raw_sources/` as immutable once a source is registered.
  New files may be added only through source-management workflows.
- Treat `$DATA_DIR/inbox/` as a human drop zone. Read files there for
  registration; move an inbox copy to `trashbin/` only after successful
  registration.
- Write generated knowledge only under `$DATA_DIR/wiki/`.
- Write organized Lean proof files only under `$DATA_DIR/lean/`.
- Append to `$DATA_DIR/wiki/log.md`; do not rewrite prior log history.
- Treat `AGENTS.md` and `.agents/skills/` as the authoritative operational and
  architectural specification.

## Wiki Rules

- All wiki pages, index entries, and log entries are written in English.
- Use Obsidian wikilinks: `[[PageName]]`.
- Every wiki page must start with YAML frontmatter containing at least `tags`
  and `date`.
- `$DATA_DIR/wiki/index.md` is the navigation map. Read it first before
  answering knowledge-base queries or deciding which concept pages to update.
- `$DATA_DIR/wiki/log.md` is append-only and uses:
  `## [YYYY-MM-DD] action | Title`.
- Human edits to wiki pages are ground truth. Read current files before
  modifying them.

## Source Rules

- Every raw source lives in `$DATA_DIR/raw_sources/<sha256_12>/`.
- The hash directory is the first 12 hex characters of the SHA-256 of the
  primary source file after final content is known.
- Preserve the original filename inside the hash directory.
- Keep per-source images and attachments under that source's local `assets/`
  directory.
- Track every source in `$DATA_DIR/sources_manifest.md`.

## Mathematical Accuracy

- For `.tex` sources, treat LaTeX commands as ground truth.
- For PDFs, read rendered pages rather than trusting plain text extraction.
- Preserve mathematical font faces in LaTeX:
  - blackboard bold: `\mathbb{}`
  - calligraphic/script: `\mathcal{}`
  - fraktur: `\mathfrak{}`
  - bold roman: `\mathbf{}`
  - sans-serif: `\mathsf{}`
- If a symbol is ambiguous, transcribe your best judgment and add a
  `<!-- VERIFY: ... -->` comment.

## Codex Skills

Repository skills live under `.agents/skills/` and are available automatically
when Codex is launched from this repository.

Use these skills when relevant:

| Skill | Purpose |
|-------|---------|
| `kbmanager` | Overview of the KBManager skill bundle |
| `orchestrator` | Route KBManager workflows through specialist subagents |
| `source-management` | Fetch, queue, and register raw sources |
| `ingest` | Dispatch registered files to the correct ingest mode |
| `ingest-source` | Convert books, papers, chapters, and lecture notes into source pages and concept links |
| `ingest-analysis` | Convert proof notes, verifier reports, partial progress, obstructions, and query syntheses into reusable analysis cards |
| `query` | Answer questions from the wiki and optionally persist new insights |
| `wiki-maintenance` | Lint and semantically reorganize the wiki |
| `lean-archive` | Archive Lean 4 files into `$DATA_DIR/lean/` and wiki cards |

This branch is Codex-first. Use the Codex skills above for KBManager workflows.

## Git

After ingest, Lean archive, lint, or reorganization operations that change the
wiki, create a git checkpoint unless the human asks not to. Keep commits scoped
to the changed knowledge-base files.

## Tool and File Rules

- Route KBManager work through `.agents/skills/orchestrator/SKILL.md` when the
  task is more than a tiny local inspection.
- Use the `orchestrator` skill before dispatching source-management, ingest,
  query, maintenance, or Lean archive work to a specialist subagent.
- Run Python project tools as `uv run python ...`; do not use bare `python` or
  `python3` for repository scripts.
- Use `DATA_DIR` for the shared data root when available. In the standard
  layout, `DATA_DIR` is `data` relative to this repository unless the human or
  environment provides another path.
- Agents may read files under `DATA_DIR`.
- Agents may write only to paths explicitly allowed by `AGENTS.md`, their
  selected skill, and the Orchestrator task packet.
- Use `cp -n` for copy operations by default so existing files are not
  overwritten silently.
- Use `mkdir -p` for directory creation.
- Do not permanently remove files or directories with `rm`. When cleanup is
  needed, move the target into the repository-root `trashbin/` directory instead,
  preserving enough path/name context to identify where it came from.
- When committing shared data, run `git -C .. status` first. Inspect the
  relevant diff when there are existing modifications, then stage with
  `git -C .. add data` and commit with `git -C .. commit -m ...`.
- Do not use `git add .`, `git add -A`, destructive Git commands, `rm`, or `mv`
  unless the human explicitly requests that operation.
