#!/usr/bin/env python3
"""Deep-search frontier state store (ADR 0018, option O3).

This tool is deliberately *mechanical*: it persists and queues candidate nodes.
It does not search, and it does not judge relevance. Retrieval is done by the
Searcher via `search.py {arxiv,matlas}` / harness web search; the relevance
score and the `why` note are supplied by the model. Ranking here only orders a
work queue -- it never decides truth.

    search.py frontier init   <workspace> --obligation "<statement being sought>"
    search.py frontier push   <workspace> --id ... --title ... [--source ...] ...
    search.py frontier next   <workspace> [--n 3] [--max-depth 1] [--claim]
    search.py frontier mark   <workspace> --id ... --status expanded|skipped
    search.py frontier status <workspace>

State lives in the workspace (ADR 0018, Q-cache = workspace), so it is born and
dies with the problem:

    <workspace>/knowledge/frontier.jsonl      one JSON node per line
    <workspace>/knowledge/frontier.meta.json  obligation + budget metadata
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from _common.paths import configure_cli_logging

configure_cli_logging()
logger = logging.getLogger(__name__)

STATUSES = ("queued", "expanded", "skipped")
SOURCES = ("arxiv", "matlas", "web", "citation-graph", "kb", "manual")

KNOWLEDGE_DIRNAME = "knowledge"
NODES_FILENAME = "frontier.jsonl"
META_FILENAME = "frontier.meta.json"


# --------------------------------------------------------------------------
# paths / io
# --------------------------------------------------------------------------

def knowledge_dir(workspace: str | Path) -> Path:
    return Path(workspace) / KNOWLEDGE_DIRNAME


def nodes_path(workspace: str | Path) -> Path:
    return knowledge_dir(workspace) / NODES_FILENAME


def meta_path(workspace: str | Path) -> Path:
    return knowledge_dir(workspace) / META_FILENAME


def load_meta(workspace: str | Path) -> dict:
    path = meta_path(workspace)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("frontier: unreadable meta at %s; treating as empty", path)
        return {}


def save_meta(workspace: str | Path, meta: dict) -> None:
    path = meta_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_nodes(workspace: str | Path) -> list[dict]:
    path = nodes_path(workspace)
    if not path.exists():
        return []
    nodes: list[dict] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            nodes.append(json.loads(line))
        except json.JSONDecodeError:
            logger.warning("frontier: skipping malformed line %d in %s", lineno, path)
    return nodes


def save_nodes(workspace: str | Path, nodes: list[dict]) -> None:
    path = nodes_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(n, ensure_ascii=False) + "\n" for n in nodes)
    path.write_text(body, encoding="utf-8")


# --------------------------------------------------------------------------
# operations
# --------------------------------------------------------------------------

def init(workspace: str | Path, obligation: str, max_depth: int = 1, force: bool = False) -> dict:
    """Create (or reset) the frontier for one problem."""
    existing = load_meta(workspace)
    if existing and not force:
        return {
            "ok": False,
            "error": "frontier already initialized; pass --force to reset",
            "obligation": existing.get("obligation", ""),
            "nodes": len(load_nodes(workspace)),
        }
    meta = {"obligation": obligation, "max_depth": max_depth}
    save_meta(workspace, meta)
    save_nodes(workspace, [])
    logger.info("frontier.init workspace=%s max_depth=%d", workspace, max_depth)
    return {"ok": True, "obligation": obligation, "max_depth": max_depth, "nodes": 0}


def push(
    workspace: str | Path,
    node_id: str,
    title: str = "",
    source: str = "manual",
    depth: int = 0,
    parent: str = "",
    score: float = 0.0,
    why: str = "",
) -> dict:
    """Insert or update one candidate node. Idempotent on `id`.

    Re-pushing a known id updates its metadata but never resurrects a node that
    has already been expanded or skipped -- otherwise a cycle in the citation
    graph would make the loop non-terminating.
    """
    nodes = load_nodes(workspace)
    by_id = {n.get("id"): n for n in nodes}
    created = node_id not in by_id
    if created:
        node = {
            "id": node_id,
            "title": title,
            "source": source,
            "depth": depth,
            "parent": parent,
            "score": score,
            "status": "queued",
            "why": why,
        }
        nodes.append(node)
    else:
        node = by_id[node_id]
        if title:
            node["title"] = title
        if why:
            node["why"] = why
        if score:
            node["score"] = score
        # keep the shallowest known route to this node
        node["depth"] = min(node.get("depth", depth), depth)
    save_nodes(workspace, nodes)
    logger.info("frontier.push id=%s created=%s", node_id, created)
    return {"ok": True, "created": created, "id": node_id, "node": node, "total": len(nodes)}


def next_batch(
    workspace: str | Path,
    n: int = 3,
    max_depth: int | None = None,
    claim: bool = False,
) -> dict:
    """Return the top-n queued nodes by score, respecting the hop budget.

    The hop budget (ADR 0018, Q-stop = hop budget) is the only stop condition:
    nodes deeper than `max_depth` are never handed out.
    """
    meta = load_meta(workspace)
    if max_depth is None:
        max_depth = int(meta.get("max_depth", 1))
    nodes = load_nodes(workspace)
    eligible = [
        node for node in nodes
        if node.get("status") == "queued" and int(node.get("depth", 0)) <= max_depth
    ]
    eligible.sort(key=lambda node: (-float(node.get("score", 0.0)), int(node.get("depth", 0)), node.get("id", "")))
    batch = eligible[:n]
    if claim:
        claimed = {node.get("id") for node in batch}
        for node in nodes:
            if node.get("id") in claimed:
                node["status"] = "expanded"
        save_nodes(workspace, nodes)
    logger.info("frontier.next workspace=%s n=%d returned=%d claim=%s", workspace, n, len(batch), claim)
    return {
        "ok": True,
        "obligation": meta.get("obligation", ""),
        "max_depth": max_depth,
        "returned": len(batch),
        "remaining_queued": len(eligible) - len(batch),
        "claimed": claim,
        "batch": batch,
    }


def mark(workspace: str | Path, node_id: str, status: str) -> dict:
    """Set a node's status.

    `skipped` means only "not expanded this round" -- it is NOT a judgement that
    the result is useless (ADR 0018: the same principle as `map.md` never
    recording "dead ends").
    """
    if status not in STATUSES:
        return {"ok": False, "error": f"status must be one of {list(STATUSES)}"}
    nodes = load_nodes(workspace)
    for node in nodes:
        if node.get("id") == node_id:
            node["status"] = status
            save_nodes(workspace, nodes)
            logger.info("frontier.mark id=%s status=%s", node_id, status)
            return {"ok": True, "id": node_id, "status": status}
    return {"ok": False, "error": f"unknown node id {node_id!r}"}


def status(workspace: str | Path) -> dict:
    """Budget-visible summary for the Orchestrator."""
    meta = load_meta(workspace)
    nodes = load_nodes(workspace)
    by_status = {name: 0 for name in STATUSES}
    by_depth: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for node in nodes:
        by_status[node.get("status", "queued")] = by_status.get(node.get("status", "queued"), 0) + 1
        depth_key = str(node.get("depth", 0))
        by_depth[depth_key] = by_depth.get(depth_key, 0) + 1
        source_key = str(node.get("source", "manual"))
        by_source[source_key] = by_source.get(source_key, 0) + 1
    max_depth = int(meta.get("max_depth", 1))
    reached = max((int(n.get("depth", 0)) for n in nodes), default=0)
    return {
        "ok": True,
        "initialized": bool(meta),
        "obligation": meta.get("obligation", ""),
        "max_depth": max_depth,
        "depth_reached": reached,
        "hop_budget_exhausted": reached >= max_depth and by_status.get("queued", 0) == 0,
        "total": len(nodes),
        "by_status": by_status,
        "by_depth": by_depth,
        "by_source": by_source,
    }


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description="Deep-search frontier state store (ADR 0018 O3)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="create or reset the frontier")
    p_init.add_argument("workspace")
    p_init.add_argument("--obligation", required=True, help="the statement being sought")
    p_init.add_argument("--max-depth", type=int, default=1, help="hop budget (default: 1)")
    p_init.add_argument("--force", action="store_true", help="reset an existing frontier")

    p_push = sub.add_parser("push", help="insert or update a candidate node")
    p_push.add_argument("workspace")
    p_push.add_argument("--id", required=True, dest="node_id")
    p_push.add_argument("--title", default="")
    p_push.add_argument("--source", default="manual", choices=SOURCES)
    p_push.add_argument("--depth", type=int, default=0)
    p_push.add_argument("--parent", default="")
    p_push.add_argument("--score", type=float, default=0.0)
    p_push.add_argument("--why", default="")

    p_next = sub.add_parser("next", help="peek the top-n queued nodes")
    p_next.add_argument("workspace")
    p_next.add_argument("--n", type=int, default=3)
    p_next.add_argument("--max-depth", type=int, default=None, help="override the stored hop budget")
    p_next.add_argument("--claim", action="store_true", help="also mark the returned nodes expanded")

    p_mark = sub.add_parser("mark", help="set a node's status")
    p_mark.add_argument("workspace")
    p_mark.add_argument("--id", required=True, dest="node_id")
    p_mark.add_argument("--status", required=True, choices=STATUSES)

    p_status = sub.add_parser("status", help="counts, depth histogram, budget usage")
    p_status.add_argument("workspace")

    args = parser.parse_args(argv)

    if args.command == "init":
        result = init(args.workspace, args.obligation, args.max_depth, args.force)
    elif args.command == "push":
        result = push(
            args.workspace, args.node_id, args.title, args.source,
            args.depth, args.parent, args.score, args.why,
        )
    elif args.command == "next":
        result = next_batch(args.workspace, args.n, args.max_depth, args.claim)
    elif args.command == "mark":
        result = mark(args.workspace, args.node_id, args.status)
    else:
        result = status(args.workspace)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("ok", True):
        sys.exit(1)


if __name__ == "__main__":
    main()
