"""Internal memory-tier modules behind the single `memory.py` entry point.

These are NOT model-facing tools. The only exposed memory interface is
`cli_tools/memory.py`; everything here is a script it calls:

- local.py       local tier (workspace JSONL ledger; former workspace_memory.py)
- kb.py          KB tier read (wiki index summary; former kb_manager_summary.py)
- experience.py  long-term Experience_* card model (former _experience.py)
"""
