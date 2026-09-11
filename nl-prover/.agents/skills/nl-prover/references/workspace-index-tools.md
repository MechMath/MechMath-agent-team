# Workspace Index Tools

These tools provide compact, mechanical views of a proof workspace. They do not
prove, verify, or replace source artifacts.

## Local References

```bash
uv run python cli_tools/workspace.py references scan <workspace> --view compact
uv run python cli_tools/workspace.py references extract <workspace> --view summary
uv run python cli_tools/workspace.py references show <workspace> --ref paper.pdf --page 3 --context-lines 20
uv run python cli_tools/workspace.py references search <workspace> --query "spectral gap" --limit 5
```

Use before source-theorem, definition, and literature work. The tool writes
`references/index.json`, `references/index.md`, and cached text under
`references/.extracted/`.

## Query Index

```bash
uv run python cli_tools/search.py index summarize <workspace> --query-id <id> --view compact
uv run python cli_tools/search.py index refresh <workspace> --source arxiv --source matlas --source kb-manager
uv run python cli_tools/search.py index latest <workspace> --source matlas --limit 5 --view summary
```

Use after existing arXiv, Matlas, or KB-Manager query outputs exist. This tool
does not run the searches; it indexes their outputs and appends source findings
to workspace memory.

## Deep-Search Frontier (ADR 0018)

```bash
uv run python cli_tools/search.py frontier init <workspace> --obligation <id>
uv run python cli_tools/search.py frontier push <workspace> --lead "<candidate>" --from <seed>
uv run python cli_tools/search.py frontier next <workspace>
uv run python cli_tools/search.py frontier mark <workspace> --lead <id> --state read
uv run python cli_tools/search.py frontier status <workspace> --max-depth 1
uv run python cli_tools/search.py citation-graph <seed> --obligation <id> --hops 1
```

`frontier` is the deep-search candidate queue (state in `knowledge/frontier.jsonl`;
`status` carries the hop-budget view). `citation-graph` walks multi-hop
references/cited-by via OpenAlex. Both are Searcher tools, not gatekeepers.

## Provenance Ledger and Bibliography (ADR 0019)

```bash
uv run python cli_tools/workspace.py ledger add <workspace> --claim-id <id> --source <ref> ...
uv run python cli_tools/workspace.py ledger set-trust <workspace> --claim-id <id> --trust cite-as-existing
uv run python cli_tools/workspace.py ledger list <workspace>
uv run python cli_tools/workspace.py ledger status <workspace>
uv run python cli_tools/workspace.py ledger validate <workspace>
uv run python cli_tools/workspace.py refs-bib <workspace> --mailto you@example.org
```

The ledger (`references/ledger.jsonl`) is a mechanical index of external-result
provenance and trust: Searcher writes provenance fields (`ledger add`), a fresh
Verifier writes the trust verdict (`ledger set-trust`). `refs-bib` renders
`references/refs.bib` from the ledger. See `prompts/searcher.md`, `prompts/verifier.md`,
and the `article-writing` skill for ownership; the gate side is
`gate.py proof-attempt --ledger` and `gate.py citation-audit` (see
`verification-gates.md`).

`ledger status` reports the trust breakdown of *that ledger* — how many claims
sit at each trust level, and which are still `pending-audit` or `borrowed`. It
is not the run dashboard. The run dashboard is `workspace.py status`, one word shorter and a
different tool; grepping this file for "status" returns both, so read which noun
precedes it before copying a line.

## Run Status

```bash
uv run python cli_tools/workspace.py status <run-root>
uv run python cli_tools/workspace.py status <run-root> --json
uv run python cli_tools/workspace.py status <tree> --index
```

Where one run stands, on one page: liveness from the newest artifact under
`lemmas/`, `verification/`, `sketch/` and `recovery/`; the proof graph (`gate
dag`); what the round cost (`gate speed`); the memory channels and how many
candidate cards are pending; and which of `proof.pdf`, `progress_notes.pdf` and
`progress_summary.pdf` exist. `--index` walks every directory holding a
`STATUS.md` below `<tree>` and prints one line each, newest first — a run root is
wherever a `STATUS.md` is, not a top-level directory, since `ESConjecture/` alone
holds fifteen of them.

Two properties are worth knowing before you read the output.

**Every absent field says why it is absent.** Nothing prints `0` for something it
could not measure. This harness lost months to a metric reading `0.0` because a
parser silently decoded nothing, and a dashboard is the point where that lie
reaches a person rather than a log. `logs/dispatch.jsonl` is deliberately not a
source: it exists in 6 of 54 run roots, in four mutually incompatible
hand-written schemas.

**Nothing is invented.** Four things a reader obviously wants — a run-level
phase, a last-progress timestamp, a machine-readable current focus, and cost —
are recorded by no file anywhere, and the page prints them as missing, by name.
Do not fill them in from inference; if you need one, the fix is a file that
records it. Liveness is likewise derived from mtimes, not from a recorded event:
an archive extraction moves it, and time the human spent away from the keyboard
reads exactly like time the run spent stuck.

## Memory (three-tier, single entry `memory.py`)

`memory.py` is the only memory tool. The tier logic lives in the internal
package `cli_tools/_memory/` (`local`, `kb`, `experience`); do not call those
directly.

```bash
# long-term memory (resident memory.md) — read every cycle, workspace included
uv run python cli_tools/memory.py read --tier long-term --view compact <workspace>
# local workspace tier
uv run python cli_tools/memory.py refresh <workspace> --view compact
uv run python cli_tools/memory.py read --tier local <workspace>
uv run python cli_tools/memory.py read --tier local <workspace> --query "missing source theorem"
uv run python cli_tools/memory.py append <workspace> --channel branch_states --source STATUS.md --kind status
# KB tier (compact index; full card bodies via the kb-manager query workflow)
uv run python cli_tools/memory.py read --tier kb --view compact
# record one lesson — the only sanctioned writer into memory/candidates/
uv run python cli_tools/memory.py candidate <workspace> --agent generator --run-id <run-id> \
    --kind negative-constraint --scope class-level \
    --statement "<what was learned, one line>" \
    --trigger "<the structural cue that should bring it back>" \
    --why "<the conditions under which it applies>" \
    --failure-modes "<when this card itself misleads>"
# ... or record explicitly that the failure taught nothing transferable
uv run python cli_tools/memory.py candidate <workspace> --agent generator --run-id <run-id> \
    --no-constraint "<why this failure carries no transferable lesson>"
# what the start-of-round re-read costs, before deciding what to read
uv run python cli_tools/memory.py budget <workspace>
```

**The workspace argument on the long-term read is not optional.** `memory.py`
stamps `memory/.longterm_read.json` only when a workspace is passed, and
`gate stop` escalates a missing stamp to an error — so the bare form cannot pass
its own stop gate, however faithfully the memory was actually read. This file
carried the bare form until `gate contracts` read `memory.py` and said so.

`candidate` is the **only** way to record a lesson: it validates the card fields
and appends to `memory/candidates/<agent>-<run-id>.jsonl`. Never hand-edit that
JSONL — a malformed line is not rejected where it is written, it is silently
skipped at aggregation weeks later, by which time the run that knew the lesson
is over. `--no-constraint REASON` goes through the same door and is the explicit
"this failure taught nothing transferable"; `gate stop` checks that one or the
other is present. `aggregate-candidates <workspace>` dedups them into the
long-term tier and re-renders `memory.md`.

`budget <workspace>` reports the bytes the Orchestrator re-reads at the start of
every round against the read budget, and names the largest contributor. It calls
the same function `gate.py speed` reports, deliberately rather than
reimplementing it — two copies of a threshold drift, and then two tools disagree
about whether a run is over budget. Check it at step 1, when you still have a
choice about what to read, not only at the gate afterwards.

`refresh` rescans known files into the local channels (`STATUS.md` →
`branch_states`, `recovery/` and `routes/proof_review*` → `failed_paths`,
review packets → `verification_reports`, `queries/` → `source_findings`,
`writer/` and `well-written-*.pdf` → `presentation`). Use `append --source
<file> --kind <label>` to index an artifact the refresh globs do not cover; the
source must be an existing file path.

Read long-term at the start of every non-trivial dispatch cycle (hard
precondition), refresh and read the local tier, and append or refresh again
after updating `STATUS.md` or the branch queue, so the ledger stays current.
Memory JSONL files are indexes only; original artifacts remain authoritative.
`memory.md` is generated by `memory.py render-longterm` from the KB
`Experience_*` cards — read it, do not hand-edit it.

## Presentation Index

```bash
uv run python cli_tools/workspace.py presentation build <workspace> --view compact
uv run python cli_tools/workspace.py presentation show <workspace> --section presentation --view summary
uv run python cli_tools/workspace.py presentation latest <workspace> --section verification --limit 5
uv run python cli_tools/workspace.py presentation sync-static <workspace> --include writer --include recovery
```

Use after Writer output or when resuming a workspace. The index is primarily for
AI/tool navigation; human-facing reports remain Writer PDFs and progress notes.
