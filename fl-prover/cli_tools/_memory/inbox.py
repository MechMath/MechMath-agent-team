#!/usr/bin/env python3
"""Write data to the KB-Manager knowledge base inbox."""
import argparse
import json
import logging
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from _common.paths import configure_cli_logging, data_dir as resolve_data_dir

configure_cli_logging()
logger = logging.getLogger(__name__)


CARD_TYPES = ("Concept_", "Source_", "Lean_", "Analysis_", "Conjecture_", "Experience_")


def write(
    content: str | None,
    path: str | None,
    filename: str | None,
    data_dir: str | None = None,
    card_type: str | None = None,
) -> None:
    logger.info("kb_manager_write.write called: path=%r filename=%r card_type=%r", path, filename, card_type)
    d = resolve_data_dir(data_dir)

    inbox = d / "inbox"
    if not inbox.exists():
        if d.exists():
            inbox.mkdir(parents=True, exist_ok=True)
            logger.info("created KB-Manager inbox: %s", inbox)
        else:
            print(json.dumps({"ok": False, "error": f"Data directory not found: {d}"}))
            sys.exit(1)

    date_prefix = datetime.now(timezone.utc).strftime("%Y%m%d")

    if path:
        src = Path(path)
        if not src.exists():
            print(json.dumps({"ok": False, "error": f"Source file not found: {src}"}))
            sys.exit(1)
        out_name = f"{date_prefix}_{filename}" if filename else f"{date_prefix}_{src.name}"
        dest = inbox / out_name
        shutil.copy2(src, dest)
    else:
        out_name = f"{date_prefix}_{filename}" if filename else f"{date_prefix}_note.md"
        if "." not in Path(out_name).suffix:
            out_name += ".md"
        dest = inbox / out_name
        body = content or ""
        if card_type:
            # Declare the target card family for the Ingester (ADR 0017 P1).
            body = f"<!-- card-type: {card_type} -->\n{body}"
        dest.write_text(body, encoding="utf-8")

    logger.info("kb_manager_write.write succeeded: dest=%s", dest)
    print(json.dumps({"ok": True, "file": str(dest), "filename": out_name, "card_type": card_type}, ensure_ascii=False))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Write data to KB-Manager knowledge base")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--content", help="Content body (text/Markdown)")
    group.add_argument("--path", help="Path to a file to copy into inbox")
    parser.add_argument("--filename", help="Output filename (date prefix added automatically)")
    parser.add_argument("--data-dir", default=None, help="Path to data directory (overrides DATA_DIR env var)")
    parser.add_argument(
        "--card-type",
        default=None,
        choices=CARD_TYPES,
        help="Declare the target KB card family for the Ingester (ADR 0017 P1)",
    )
    args = parser.parse_args(argv)
    write(args.content, args.path, args.filename, args.data_dir, args.card_type)


if __name__ == "__main__":
    main()
