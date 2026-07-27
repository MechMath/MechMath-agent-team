#!/usr/bin/env python3
"""List available KB-Manager knowledge-base index entries (zero cost, local read)."""
import argparse
import json
import logging
import os
import sys
from pathlib import Path

from _common.paths import configure_cli_logging, data_dir as resolve_data_dir

configure_cli_logging()
logger = logging.getLogger(__name__)


def _section_entries(lines: list[str], heading: str) -> list[str]:
    entries: list[str] = []
    in_section = False
    for line in lines:
        stripped = line.strip()
        if stripped == heading:
            in_section = True
            continue
        if in_section:
            if stripped.startswith("## ") or stripped == "---":
                break
            if stripped.startswith("- "):
                entries.append(stripped[2:])
    return entries


def build_summary(data_dir: str | None = None) -> dict:
    """Return the KB wiki index summary as a dict (so the memory.py facade can
    consume it without shelling out). ADR 0017 §3 adds the Experience section."""
    logger.info("kb_manager_summary.build_summary called")
    d = resolve_data_dir(data_dir)

    index_path = d / "wiki" / "index.md"
    if not index_path.exists():
        return {"ok": False, "error": f"Index not found: {index_path}"}

    lines = index_path.read_text(encoding="utf-8").splitlines()

    concepts = _section_entries(lines, "## Concepts")
    analyses = _section_entries(lines, "## Analyses & Comparisons")
    experience = _section_entries(lines, "## Experience")

    logger.info(
        "kb_manager_summary.build_summary succeeded: %d concepts, %d analyses, %d experience",
        len(concepts),
        len(analyses),
        len(experience),
    )
    return {
        "ok": True,
        "count": len(concepts),
        "concept_count": len(concepts),
        "analysis_count": len(analyses),
        "experience_count": len(experience),
        "total_count": len(concepts) + len(analyses) + len(experience),
        "concepts": concepts,
        "analyses": analyses,
        "experience": experience,
    }


def summary(data_dir: str | None = None) -> None:
    payload = build_summary(data_dir)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if not payload.get("ok"):
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="List available KB-Manager knowledge-base index entries")
    parser.add_argument("--data-dir", default=None, help="Path to data directory (overrides DATA_DIR env var)")
    args = parser.parse_args()
    summary(args.data_dir)
