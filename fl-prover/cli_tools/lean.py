#!/usr/bin/env python3
"""lean — the Lean toolchain entry (paper Table 2b: the five formal categories).

    lean check   <file.lean> [--compact|--summary] [--severity S] [--include-sorries]
    lean scan    <file.lean> [--token sorry|admit] [--compact|--plain]
    lean axioms  <file.lean> [--decl NAME] [--allow AXIOM] [--module MOD]
    lean guard   {snapshot|check|diff|approve-change|reset-snapshot} --workspace W --task T
    lean index   {declarations|statements|statement|imports|outline} <file.lean>
    lean search  <engine> <query> [-n N]
                 engines: leansearch, leanfinder, leandex, loogle, state, hammer

`check` + `scan` + `axioms` are the correctness gate: compiles, no `sorry`, and
no axiom outside the accepted base set. Nothing under `cli_tools/_lean/` is
called directly.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _lean import axioms, check, fileinfo, guard, scan
from _lean import hammer_premise, leandex, leanfinder, leansearch, loogle, state_search

SEARCH_ENGINES = {
    "leansearch": leansearch.main,
    "leanfinder": leanfinder.main,
    "leandex": leandex.main,
    "loogle": loogle.main,
    "state": state_search.main,
    "hammer": hammer_premise.main,
}

USAGE = (
    "usage: lean {check|scan|axioms|guard|index|search} [args...]\n"
    f"       lean search {{{'|'.join(SEARCH_ENGINES)}}} <query> [-n N]"
)


def _search(argv: list[str]) -> None:
    if not argv or argv[0] in ("-h", "--help"):
        print(USAGE)
        sys.exit(0 if argv else 2)
    engine = argv[0]
    if engine not in SEARCH_ENGINES:
        print(f"unknown search engine {engine!r}\n{USAGE}", file=sys.stderr)
        sys.exit(2)
    SEARCH_ENGINES[engine](argv[1:])


DISPATCH = {
    "check": check.main,
    "scan": scan.main,
    "axioms": axioms.main,
    "guard": guard.main,
    "index": fileinfo.main,
    "search": _search,
}


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
