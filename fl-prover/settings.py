"""Central configuration — loads from .env if present."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# `COLLECTOR_DIR` is the pre-rename variable; still honoured so an existing
# .env keeps working.
KB_MANAGER_DIR: str | None = os.environ.get("KB_MANAGER_DIR") or os.environ.get("COLLECTOR_DIR")
COLLECTOR_DIR = KB_MANAGER_DIR  # deprecated alias
DATA_DIR: str = os.environ.get("DATA_DIR") or str(Path(__file__).parent.parent / "data")
ANTHROPIC_API_KEY: str | None = os.environ.get("ANTHROPIC_API_KEY")
GEMINI_API_KEY: str | None = os.environ.get("GEMINI_API_KEY")
OPENAI_API_KEY: str | None = os.environ.get("OPENAI_API_KEY")
OPENROUTER_API_KEY: str | None = os.environ.get("OPENROUTER_API_KEY")

# Lean-specific search backend (Leandex semantic search).
LEANDEX_API_KEY: str | None = os.environ.get("LEANDEX_API_KEY")
