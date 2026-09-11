#!/usr/bin/env python3
"""gate — mechanical accept/complete checks (the single entry for lints + completion).

    gate complete        <workspace> [--packet P ...] [--json]
    gate stop            <workspace> [--verified-proof] [--json]   (run-end write-back, ADR 0022)
    gate proof-attempt   <proof_file> [--status F] [--ledger WS] [--json]
    gate proof-review    <proof_review_file> [--json]
    gate review-packet   <packet_file> [--json]
    gate result-contract <workspace> [--json]
    gate citation-audit  <workspace> --tex F [--json]   (final-article citation lint, ADR 0019)
    gate discovery       <workspace> [--json]   (discovery-region schema lint, ADR 0023)
    gate speed           <workspace> [--json] [--strict]   (run cost telemetry, ADR 0024)
    gate dag             <workspace> [--json] [--strict]   (lemma dependency graph, advisory)

These are structural, non-mathematical checks.

Every subcommand takes --waive REASON: it records the violations and continues
instead of blocking, and `gate stop` summarises what was waived. Each also
prints, on --help and on failure alike, what it checks, what the legal values
are, and the smallest fix.
"""
import sys
from _gate import completion, proof_attempt, proof_review, review_packet, result_contract, citation_audit, stop, discovery, speed, dag, summary, contracts

DISPATCH = {
    "complete": completion.main,
    "stop": stop.main,
    "proof-attempt": proof_attempt.main,
    "proof-review": proof_review.main,
    "review-packet": review_packet.main,
    "result-contract": result_contract.main,
    "citation-audit": citation_audit.main,
    "discovery": discovery.main,
    "speed": speed.main,
    "dag": dag.main,
    "summary": summary.main,
    "contracts": contracts.main,
}
USAGE = (
    "usage: gate {complete|stop|proof-attempt|proof-review|review-packet|"
    "result-contract|citation-audit|discovery|speed|dag|summary|contracts} [args...]\n"
    "       gate <subcommand> --help   for what it checks, the legal values, and the fix\n"
    "       every subcommand takes --waive REASON to record and continue"
)


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
