"""Shared path helpers for NL-Prover CLI tools."""

from __future__ import annotations

import logging
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT.parent / "data"


def data_dir(override: str | None = None) -> Path:
    return Path(override or os.environ.get("DATA_DIR") or DEFAULT_DATA_DIR)


def cli_log_path() -> Path:
    return data_dir() / "logs" / "cli.log"


def configure_cli_logging() -> None:
    path = cli_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(path)],
    )
