#!/usr/bin/env python3
"""external — independent external-LLM checks (the single entry for verify/discuss).

    external gemini  <proof_file> [--problem F] [--lemma F] [--model M]
    external gpt     <proof_file> [--problem F] [--lemma F] [--model M]
    external discuss <question|-> [--backend gemini|gpt] [--context F]
"""
import sys
from pathlib import Path

# The external LLM tools read keys from repo-root settings.py; put the repo root
# on the path so `import settings` resolves regardless of CWD.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _external import gemini, cross, discuss

DISPATCH = {"gemini": gemini.main, "gpt": cross.main, "discuss": discuss.main}
USAGE = "usage: external {gemini|gpt|discuss} [args...]"


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
