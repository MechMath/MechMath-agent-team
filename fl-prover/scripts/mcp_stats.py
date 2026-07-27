"""
MCP log analysis utilities.
"""

import re
import json
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Optional


def analyze_mcp_log(log_path: str | Path, out_dir: str | Path) -> dict:
    """
    Count tool calls in the MCP log and save results.

    Args:
        log_path: Path to mcp_lean_lsp.log
        out_dir: Output directory for results

    Returns:
        Summary dictionary with tool call statistics
    """
    log_path = Path(log_path).expanduser().resolve()
    out_path = Path(out_dir).expanduser().resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    # Backup original log
    raw_backup = out_path / "mcp_stats_raw.log"
    if log_path.exists():
        shutil.copy2(log_path, raw_backup)

    # Regex patterns
    tool_pat = re.compile(r"🔧 Tool:")
    tool_name_same_line = re.compile(r"🔧 Tool:\s*([a-zA-Z_]\w*)\(")
    tool_name_next_line = re.compile(r"^\s*([a-zA-Z_]\w*)\(")
    result_pat = re.compile(r"^\s*(✅|❌)")
    warn_pat = re.compile(r"⚠️|❌")

    stats = defaultdict(lambda: {"total": 0, "ok": 0, "fail": 0})

    if not log_path.exists():
        print(f"[warn] Log file does not exist: {log_path}")
        return {"by_tool": {}, "total": {"total": 0, "ok": 0, "fail": 0}}

    with open(log_path, encoding="utf-8") as f:
        lines = f.readlines()

    i, n = 0, len(lines)
    while i < n:
        m = tool_pat.search(lines[i])
        if not m:
            i += 1
            continue

        tool = None
        # Try matching tool name on the same line
        m = tool_name_same_line.search(lines[i])
        if m:
            tool = m.group(1)
        # If not found, try the next line
        elif i + 1 < n:
            m = tool_name_next_line.search(lines[i + 1])
            if m:
                tool = m.group(1)

        if not tool:
            i += 1
            continue

        stats[tool]["total"] += 1

        j = i + 1
        while j < n and not result_pat.match(lines[j]):
            j += 1
        if j < n and warn_pat.search(lines[j]):
            stats[tool]["fail"] += 1
        else:
            stats[tool]["ok"] += 1
        i = j if j < n else i + 1

    # Print results
    total_ok = total_fail = 0
    for t, s in stats.items():
        total_ok += s["ok"]
        total_fail += s["fail"]
        print(f'{t:25}  total={s["total"]:3}  ok={s["ok"]:3}  fail={s["fail"]:3}')
    print("-" * 60)
    print(
        f'{"TOTAL":25}  total={total_ok + total_fail:3}  ok={total_ok:3}  fail={total_fail:3}'
    )

    # Save as JSON
    summary = {
        "by_tool": {k: dict(v) for k, v in stats.items()},
        "total": {"total": total_ok + total_fail, "ok": total_ok, "fail": total_fail},
    }
    json_file = out_path / "mcp_stats.json"
    with json_file.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\nMCP tool call stats saved to {json_file}")

    return summary


def get_mcp_log_path(
    mcp_log_name: Optional[str] = None,
    mcp_log_dir: Optional[str | Path] = None,
) -> Optional[Path]:
    """
    Get the MCP log file path.

    Args:
        mcp_log_name: Optional log name (used with MCP_LOG_NAME env var)
        mcp_log_dir: Optional log directory (used with MCP_LOG_DIR env var)

    Returns:
        Path to the log file, or None if mcp_log_dir is not specified
    """
    base_path = Path(mcp_log_dir) if mcp_log_dir else Path("~/.lean_lsp_mcp").expanduser()
    log_name = f"{mcp_log_name}.log" if mcp_log_name else "mcp_lean_lsp.log"
    return base_path / log_name

