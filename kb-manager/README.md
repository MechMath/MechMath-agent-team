# KBManager

A persistent research knowledge base maintained by Codex. Researchers supply raw sources; Codex handles reading, extraction, cross-referencing, and compiles reusable knowledge into `$DATA_DIR/wiki/`.

---

## Directory Structure

```
mmat/
├── kb-manager/                    # This component
│   ├── AGENTS.md                   # Codex project instructions
│   ├── .agents/skills/             # KBManager workflow skills
│   ├── .codex/                     # Codex defaults and permission rules
│   └── .codex-plugin/              # Codex plugin manifest
└── data/                           # Shared runtime data (`$DATA_DIR`)
    ├── inbox/                      # Drop zone for files to register
    ├── raw_sources/<sha256_12>/    # Immutable, hash-addressed raw sources
    │   ├── paper.pdf               # Primary source; original filename preserved
    │   └── assets/                 # Per-source images and attachments
    ├── lean/                       # Organized Lean 4 proof archive
    ├── wiki/                       # Compiled knowledge base
    │   ├── index.md                # Global catalog, read first for queries
    │   └── log.md                  # Append-only operation log
    ├── sources_manifest.md         # Pending/Ingested source registry
    └── download_queue.md           # Resources pending manual download
```

---

## How Researchers Participate

### Option 1 — Fetch a publicly accessible resource

If a paper or article is available via a public URL (arXiv, open-access journal, blog post), let Codex download and process it automatically:

```
$source-management https://arxiv.org/abs/xxxx.xxxxx
```

Codex will convert the page to Markdown, download any images locally, save the result to `$DATA_DIR/raw_sources/`, and ask whether to hand off to `ingester`.

---

### Option 2 — Register a locally downloaded file

Place the file in `$DATA_DIR/inbox/`, then run:

```
$source-management paper.pdf
```

Or simply invoke `$source-management` if there is only one file in the inbox — Codex will pick it up automatically. Codex computes the SHA-256 hash, creates `$DATA_DIR/raw_sources/<hash12>/`, copies the file there, registers it in `$DATA_DIR/sources_manifest.md`, and offers to hand off to `ingester`. The inbox copy is moved to `trashbin/` after successful registration.

You can also point to any path outside the inbox:
```
$source-management /path/to/paper.pdf
```

---

### Option 3 — Track resources that cannot be fetched automatically

For paywalled papers, content behind institutional login, or anything requiring authenticated access, there are two ways to register them:

**Auto-register** (let Codex try first, then fall back on failure):
```
$source-management https://doi.org/10.xxxx/xxxxx
```
If the fetch fails, Codex automatically adds the resource to the `## Pending` section of `$DATA_DIR/download_queue.md` and tells you exactly where to place the file.

**Direct registration** (when you already know it cannot be auto-fetched):
```
$source-management queue https://doi.org/10.xxxx/xxxxx
$source-management queue "Author et al. 2023, Journal of X, doi:10.xxx"
```

Either way, an entry like this will appear in `$DATA_DIR/download_queue.md`:

```markdown
### [1] Title of the Paper
- **URL**: https://...
- **DOI**: 10.xxx/xxx
- **Authors**: Author1, Author2
- **Year**: 2023
- **Target filename**: `$DATA_DIR/raw_sources/<hash_tbd>/Author2023_Title.pdf`
  *(hash directory will be determined after manual download)*
- **Added**: 2026-04-12
- **Failure reason**: HTTP 403 - Access restricted
- **Status**: `pending`
```

Once you have downloaded the file, run:

```
$source-management ~/Downloads/Author2023_Title.pdf
```

Codex will compute the hash, place the file in the correct directory, remove it from the queue, and offer to hand off to `ingester`.

---

## Querying the Knowledge Base

Once sources have been ingested, ask questions in natural language:

```
$query What are the main results established in the ingested sources?
$query What open problems or conjectures are discussed across the literature?
```

Codex reads the index first, then retrieves only the relevant pages, synthesizes a cited answer, and — if the synthesis surfaces a new connection — proactively creates a new wiki page to preserve it.

---

## Mathematical Card Schema

KBManager uses the wiki as a mathematical card graph, not as a folder of generic notes.
Each page type is designed for a different reuse pattern:

| Card type | Purpose |
|---|---|
| `Source_*` | External references: definitions, statements, hypotheses, proof ideas, examples, remarks, and bibliography |
| `Concept_*` | Cross-source mathematical objects: definitions, variants, dependencies, related results, warnings, and examples |
| `Analysis_*` | Reusable reasoning lessons: proof patterns, verifier feedback, missing hypotheses, checklists, and false shortcuts |
| `PartialProof_*` | Reusable partial progress assets: intermediate statements, partial routes, useful reductions, dependencies, and repair directions |
| `Obstruction_*` | Falsified path constraints: ruled-out assumptions, invalid shortcuts, incompatible definitions, counterexample signals, or impossible precondition audits |
| `Lean_*` | Formal proof artifacts: Lean declarations, type signatures, imports, namespaces, docstrings, and proof status |

Links between cards should carry mathematical meaning: source support, concept dependency, partial-progress reuse, obstruction, formalization, or warning/checklist relevance. Future queries should retrieve both facts and prior progress or ruled-out paths.

---

## Wiki Health Check

Run periodically to catch orphan cards, missing metadata, duplicate concepts,
weak partial-proof links, unresolved obstructions, and index gaps:

```
$wiki-maintenance lint
```

Codex reports all findings and proposes fixes. **Nothing is changed until you confirm.**

---

## Browsing in Obsidian

Open `$DATA_DIR/wiki/` as an Obsidian vault to:

- Visualize concept connectivity in **Graph View**
- Query YAML frontmatter with the **Dataview plugin** (filter by tag, sort by date, etc.)
- Edit any wiki page directly — Codex will treat your edits as ground truth on its next operation

---

## Working with Mathematical PDFs

This system is designed for pure mathematics research. Mathematical notation is handled with strict accuracy.

### Recommended workflow for a PDF paper

**For arXiv papers** — always try this first:
```
$source-management https://arxiv.org/abs/2301.12345
```
Codex will automatically attempt to download the LaTeX source (`.tex` file) from arXiv. If successful, you get mathematically perfect notation since it is the actual source. The PDF is only used as a fallback.

**For short papers (under ~40 pages)** downloaded locally:
```
$source-management ~/Downloads/paper.pdf
handoff to `ingester`
```
Codex reads the PDF page-by-page using vision, transcribing all mathematical notation into LaTeX (`\mathbb{}`, `\mathcal{}`, `\mathfrak{}`, etc.). Symbols that are ambiguous in the rendering are flagged with `<!-- VERIFY -->` comments in the wiki page.

### Why mathematical font faces matter

In pure mathematics, `\mathbb{E}`, `\mathcal{E}`, and `\mathfrak{e}` are completely different objects. Codex enforces a strict transcription table:

| What you see | LaTeX command | Typical meaning |
|---|---|---|
| 𝔼, ℝ, ℂ, 𝕜 (double-struck) | `\mathbb{}` | Number fields, probability spaces |
| 𝒜, ℬ, 𝒞, ℰ (curly/script) | `\mathcal{}` | Categories, sheaves, filtrations |
| 𝔤, 𝔥, 𝔪, 𝔫 (gothic) | `\mathfrak{}` | Lie algebras, ideals, p-adic |
| **A**, **v** (bold) | `\mathbf{}` | Vectors, matrices |

When ambiguous, Codex flags the location for you to verify against the original PDF.

---

## Command Reference

| Agent / Skill | Description |
|---|---|
| `registrar` / `$source-management` | Fetch, queue, or register raw sources |
| `ingester` | Process a file from `$DATA_DIR/raw_sources/` into the wiki |
| `archivist` | Archive a Lean 4 proof file: organize into semantic units, create wiki cards, cross-index with Concept pages |
| `researcher` / `$query` | Query and synthesize from the knowledge base |
| `maintainer` / `$wiki-maintenance` | Run wiki lint or semantic reorganization |

---

## Ground Rules

- **Do not modify or delete existing files in `$DATA_DIR/raw_sources/`** — they are the immutable source of truth. New files are added there by `$source-management`; never place files directly into `$DATA_DIR/raw_sources/` by hand (the hash directory structure is managed automatically).
- **Feel free to edit any page in `$DATA_DIR/wiki/`** — Codex will read your changes and treat them as the new ground truth on its next operation.
- **`$DATA_DIR/download_queue.md` can be edited by hand** — modify or delete entries directly as needed.
- Git commits are made automatically by Codex after each ingest and wiki-maintenance operation that changes the wiki.
