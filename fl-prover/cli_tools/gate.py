#!/usr/bin/env python3
"""gate — mechanical accept/complete checks (the single entry for lints + completion).

    gate complete        <workspace> [--packet P ...] [--json]
    gate stop            <workspace> [--verified-proof] [--json]   (run-end write-back, ADR 0022)
    gate proof-review    <proof_review_file> [--json]
    gate review-packet   <packet_file> [--json]
    gate result-contract <workspace> [--json]

These are structural, non-mathematical checks.

`proof-attempt` and `citation-audit` were removed 2026-09-09: zero prose invocations
anywhere in the repo, reached only from this dispatch table and their own tests, and
`citation-audit` lints a final-article `.tex` this harness does not produce.

**CORRECTION, same day, after review.** The first version of this note claimed the FIVE
remaining modules were load-bearing because `memory.py`, `_memory/local.py` and
`_workspace/presentation.py` import them. That is false, and it is the very error the
deletion note was congratulating itself on avoiding: `memory.py` has no `_gate` import at
all, and what `_memory/local.py:157` and `_workspace/presentation.py:78` contain are
**markdown filename globs** — `"**/review_packet*.md"`, `"routes/proof_review*.md"` —
not module imports. The dependency in fact runs the other way (`_gate/completion.py:366`
imports `_memory.local`).

The real graph is: `stop` imports `completion`; `completion` imports `review_packet`,
`proof_review`, `result_contract`; `result_contract` imports `review_packet`. Nothing
outside `_gate/` imports any of them. So the honest licence for the five to stay is that
`gate stop` IS invoked in prose — `stop-conditions.md:26`, `orchestration.md:70`,
`normative.md:123` — and `stop` needs `completion`, which needs the other three.

Which leaves an open question this note previously pretended to have closed: `complete`,
`proof-review`, `review-packet` and `result-contract` have zero prose invocations and zero
external imports. They are reachable only from this table, each other, and their tests —
the identical criterion by which the two above were deleted. Deleting them is a proposal,
not a footnote.
"""
import sys
from _gate import completion, proof_review, review_packet, result_contract, stop

DISPATCH = {
    "complete": completion.main,
    "stop": stop.main,
    "proof-review": proof_review.main,
    "review-packet": review_packet.main,
    "result-contract": result_contract.main,
}
USAGE = "usage: gate {complete|stop|proof-review|review-packet|result-contract} [args...]"


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(USAGE)
        sys.exit(0 if len(sys.argv) >= 2 else 2)
    cmd = sys.argv[1]
    if cmd not in DISPATCH:
        print(f"unknown subcommand {cmd!r}\n{USAGE}", file=sys.stderr)
        sys.exit(2)
    rc = DISPATCH[cmd](sys.argv[2:])
    if isinstance(rc, int):
        sys.exit(rc)


if __name__ == "__main__":
    main()
