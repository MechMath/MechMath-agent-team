#!/usr/bin/env python3
"""search — find external results (the single entry for literature/query tools).

    search arxiv          <query> [--max-results N] [--cache-dir DIR]
    search matlas         <query> [--num-results N] [--cache-dir DIR]
    search index          summarize|refresh|latest <workspace> ...   (index existing query outputs)
    search frontier       init|push|next|mark|status <workspace> ... (deep-search frontier, ADR 0018 O3)
    search citation-graph <seed> --obligation "<statement>" [--hops N] (ADR 0018 O1, OpenAlex)
"""
import sys
from _search import arxiv, citation_graph, frontier, matlas, query_index

DISPATCH = {
    "arxiv": arxiv.main,
    "matlas": matlas.main,
    "index": query_index.main,
    "frontier": frontier.main,
    "citation-graph": citation_graph.main,
}
USAGE = "usage: search {arxiv|matlas|index|frontier|citation-graph} [args...]"


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
