"""Shared internals used across the tool facades.

Not model-facing. These are the helpers every facade needs, kept in one place
rather than as loose top-level modules beside the facades themselves:

- paths.py       DATA_DIR resolution and CLI logging setup
- indexing.py    shared helpers for the workspace index tools (views, scoring,
                 JSONL, emit)
- openrouter.py  OpenRouter/OpenAI client helpers for the external facade
"""
