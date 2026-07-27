#!/usr/bin/env python3
"""workspace — navigate/index the files already in a problem's workspace.

    workspace references   scan|extract|show|search <workspace> ...   (local reference PDFs/notes)
    workspace presentation build|show|latest|sync-static <workspace> ... (Writer outputs)
    workspace ledger       add|set-trust|list|status|validate <workspace> ... (provenance ledger, ADR 0019)
    workspace refs-bib     <workspace> [--mailto ...]                 (ledger -> references/refs.bib, ADR 0019)

Not to be confused with the problem workspace directory itself; this is the tool
that reads and indexes what is inside it.
"""
import sys
from _workspace import references, presentation, ledger, refs_bib

DISPATCH = {
    "references": references.main,
    "presentation": presentation.main,
    "ledger": ledger.main,
    "refs-bib": refs_bib.main,
}
USAGE = "usage: workspace {references|presentation|ledger|refs-bib} [args...]"


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(USAGE)
        sys.exit(0 if len(sys.argv) >= 2 else 2)
    cmd = sys.argv[1]
    if cmd not in DISPATCH:
        print(f"unknown subcommand {cmd!r}\n{USAGE}", file=sys.stderr)
        sys.exit(2)
    DISPATCH[cmd](sys.argv[2:])


if __name__ == "__main__":
    main()
