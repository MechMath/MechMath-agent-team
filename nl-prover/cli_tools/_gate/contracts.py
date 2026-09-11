"""Cross-module contracts: facts stated in more than one file, checked against
the implementation rather than against each other.

The seam this replaces was going to be a table in an ARCHITECTURE.md, one row
per place two modules meet, with the rule "if a change touches a row, update
both ends". That is a list inside a document, and a list inside a document is
the thing that rots — it needs somebody to remember to read it, and the failure
mode is silence.

Five of the eight duplicated facts in this repo have an executable ground truth
already sitting in the code:

    the facade list          <- cli_tools/*.py
    the gate subcommand list <- cli_tools/gate.py DISPATCH
    the skill roster         <- .agents/skills/*/
    the concurrency ceiling  <- _gate/speed.py DECLARED_CONCURRENCY
    the long-term read form  <- cli_tools/memory.py (stamps only with a workspace)

So this reads the code and checks the prose against it. Two of the three that
had no executable form -- who may set `blocked`, and the Codex allowlist -- are
still deliberately NOT in here. Inventing a machine-readable shape for them
before anything is written against one would be guessing, and a lint that
guesses is worse than a document that rots.

The third, the pre-stop sequence, acquired a ground truth when
`stop-conditions.md` was named as its SSOT, so it is checked now. The truth is a
designated file rather than executable code, which is weaker -- but "the four
copies agree with the one that decides" is still a fact, and it existed in three
mutually inconsistent versions until somebody read all four by hand.

Every finding names both ends. A drift report that names only the wrong copy
sends someone to fix the file that was already right half the time.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _gate import waiver  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[2]

# Files that state facts about the system. Read-only, every one of them.
PROSE = (
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "prompts/orchestration.md",
    "prompts/references/verification-gates.md",
    ".agents/skills/nl-prover/SKILL.md",
    ".agents/skills/nl-prover/references/orchestrator-cookbook.md",
    ".agents/skills/nl-prover/references/workspace-index-tools.md",
    ".agents/skills/compute-budget/SKILL.md",
)

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
}

REQUIREMENT = """
If it fails:
  Fix the prose, not the code -- unless the code is what is wrong, in which case
  say so in the same change. Every finding below names both ends on purpose: the
  file that disagrees is not always the file that is wrong.
""".strip()


class ContractResult:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.contracts: dict = {}

    @property
    def ok(self) -> bool:
        return not self.errors


def _read(root: Path, name: str) -> str | None:
    path = root / name
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _find_counts(text: str, noun: str) -> list[tuple[int, str]]:
    """(line number, phrase) for every "<number> <noun>" in the text.

    Scanned over the whole text, not line by line: prose wraps, and a check that
    reads one line at a time reports a correct statement as drift because the
    sentence broke in the middle. That is exactly what the first version of this
    gate did to CLAUDE.md's long-term-read line.
    """
    words = "|".join(NUMBER_WORDS)
    # A count is never written with a leading zero, and an ADR number always is:
    # "see ADR 0016 facades" matched `0016 facades` and raised a blocking error
    # claiming the repo has sixteen facades. The identifier is also excluded by
    # name, because `ADR 16` would be legal too. `one`/`two` are in the word list
    # because prose states small counts as words and the list began at `three`.
    pattern = re.compile(
        rf"(?<!ADR )(?<!adr )\*{{0,2}}({words}|\b[1-9]\d*)\*{{0,2}}\s+{noun}",
        re.IGNORECASE,
    )
    return [
        (_line_of(text, match.start()), re.sub(r"\s+", " ", match.group(0)))
        for match in pattern.finditer(text)
    ]


def _as_int(token: str) -> int | None:
    token = token.strip("*").lower()
    if token.isdigit():
        return int(token)
    return NUMBER_WORDS.get(token)


# --- ground truths -------------------------------------------------------


def facades(root: Path) -> list[str]:
    """Model-facing facades: top-level cli_tools/*.py that are not private."""
    directory = root / "cli_tools"
    if not directory.is_dir():
        return []
    return sorted(
        path.stem
        for path in directory.glob("*.py")
        if not path.name.startswith("_") and path.stem != "migrate_memory_md"
    )


def gate_subcommands(root: Path) -> list[str]:
    text = _read(root, "cli_tools/gate.py")
    if text is None:
        return []
    # To the closing brace at column 0, not to the first `}` anywhere: a
    # trailing comment or a nested brace truncated the list silently, and a
    # partial truth set then accuses every catalogue of omitting the rest.
    block = re.search(r"^DISPATCH\s*=\s*\{\n(.*?)^\}", text, re.DOTALL | re.MULTILINE)
    if not block:
        return []
    return sorted(re.findall(r'^\s*"([a-z-]+)"\s*:', block.group(1), re.MULTILINE))


def skills(root: Path) -> list[str]:
    directory = root / ".agents" / "skills"
    if not directory.is_dir():
        return []
    return sorted(
        path.name for path in directory.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    )


def declared_concurrency(root: Path) -> int | None:
    text = _read(root, "cli_tools/_gate/speed.py")
    if text is None:
        return None
    match = re.search(r"^DECLARED_CONCURRENCY\s*=\s*(\d+)", text, re.MULTILINE)
    return int(match.group(1)) if match else None


def codex_threads(root: Path) -> int | None:
    text = _read(root, ".codex/config.toml")
    if text is None:
        return None
    match = re.search(r"^\s*max_threads\s*=\s*(\d+)", text, re.MULTILINE)
    return int(match.group(1)) if match else None


def check_nesting_enforcement(result: ContractResult, root: Path) -> None:
    """Invariant 2 has an enforcement point on each platform. Check both exist.

    `max_threads` is the fan-out limit and `max_depth` is the nesting limit;
    both platform files cited the first for a rule the second enforces, and only
    `max_threads` was parsed here — so deleting `max_depth = 1` fired nothing.
    """
    codex = _read(root, ".codex/config.toml")
    depth = None
    if codex is not None:
        match = re.search(r"^\s*max_depth\s*=\s*(\d+)", codex, re.MULTILINE)
        depth = int(match.group(1)) if match else None
    guard_path = root / ".claude" / "hooks" / "nesting_guard.py"
    guard = guard_path.is_file()
    # Presence and registration are necessary and nowhere near sufficient. The
    # first version of this check asserted exactly those two things about a hook
    # that read the wrong payload field and could not fire on any real dispatch
    # -- and reported the enforcement healthy. So run its own self-test, which
    # now builds its cases from the payload shape the runtime documents.
    guard_works: bool | None = None
    if guard:
        try:
            import subprocess

            guard_works = subprocess.run(
                [sys.executable, str(guard_path), "--self-test"],
                capture_output=True, timeout=30,
            ).returncode == 0
        except Exception:
            guard_works = None
    settings = _read(root, ".claude/settings.json") or ""
    registered = "nesting_guard" in settings
    result.contracts["nesting"] = {
        "codex_max_depth": depth,
        "claude_guard_present": guard,
        "claude_guard_registered": registered,
        "claude_guard_self_test": guard_works,
    }
    if depth is None:
        result.errors.append(
            ".codex/config.toml sets no max_depth; invariant 2 (a specialist may "
            "not dispatch) is then unenforced on Codex"
        )
    elif depth != 1:
        result.errors.append(
            f".codex/config.toml sets max_depth = {depth}; invariant 2 needs 1"
        )
    if not guard:
        result.errors.append(
            "no .claude/hooks/nesting_guard.py; invariant 2 is then prose only on "
            "Claude Code, where a subagent with no `tools:` inherits Agent"
        )
    elif not registered:
        result.errors.append(
            ".claude/hooks/nesting_guard.py exists but .claude/settings.json does "
            "not register it — a guard nobody runs"
        )
    elif guard_works is False:
        result.errors.append(
            ".claude/hooks/nesting_guard.py fails its own --self-test. It is "
            "present and registered, which is what a working guard also looks "
            "like; run it and read the failures"
        )
    elif guard_works is None:
        result.warnings.append(
            "could not run .claude/hooks/nesting_guard.py --self-test, so the "
            "nesting enforcement is reported present but unverified"
        )


def longterm_read_needs_workspace(root: Path) -> bool:
    """memory.py stamps the read trace only when a workspace is passed."""
    text = _read(root, "cli_tools/memory.py")
    if text is None:
        return False
    return "if args.workspace" in text and "_stamp_longterm_read" in text


def rendered_cards(root: Path) -> tuple[int, int]:
    """(cards on disk, cards rendered into memory.md)."""
    directory = root / "memory" / "experience"
    on_disk = len(list(directory.glob("*.md"))) if directory.is_dir() else 0
    text = _read(root, "memory.md")
    rendered = len(re.findall(r"^- ", text, re.MULTILINE)) if text else 0
    return on_disk, rendered


# --- checks --------------------------------------------------------------


def check_counted_list(
    result: ContractResult,
    root: Path,
    *,
    key: str,
    truth: list[str],
    noun: str,
    where: str,
) -> None:
    result.contracts[key] = {"truth": truth, "count": len(truth), "source": where}
    if not truth:
        result.warnings.append(f"{key}: could not read the ground truth from {where}")
        return
    for name in PROSE:
        text = _read(root, name)
        if text is None:
            continue
        for line_number, phrase in _find_counts(text, noun):
            stated = _as_int(phrase.split()[0])
            if stated is None or stated == len(truth):
                continue
            result.errors.append(
                f"{key}: {name}:{line_number} says {phrase!r}; {where} has "
                f"{len(truth)} ({', '.join(truth)})"
            )


# A subcommand a prompt still orders and the code no longer has. This is the
# drift direction that actually stops a run, and the one the first version of
# this gate could not see: it computed `truth - named` only.
_INVOCATION = re.compile(
    r"cli_tools/(gate|memory|workspace|search|external|verify)\.py\s+([a-z][a-z-]*)"
)


def check_invocations_exist(
    result: ContractResult, root: Path, *, subcommands: dict[str, list[str]]
) -> None:
    """Every `<facade>.py <subcommand>` written anywhere must still exist."""
    gone: dict[str, list[str]] = {}
    for name in PROSE + (
        "prompts/writer.md",
        "prompts/generator.md",
        "prompts/sketcher.md",
        ".agents/skills/nl-prover/references/stop-conditions.md",
        ".agents/skills/memory-routing/SKILL.md",
        "prompts/references/verification-gates.md",
    ):
        text = _read(root, name)
        if text is None:
            continue
        for facade, sub in _INVOCATION.findall(text):
            known = subcommands.get(facade)
            if known is None or sub in known:
                continue
            gone.setdefault(f"{facade} {sub}", []).append(name)
    result.contracts["invocations_checked"] = sorted(subcommands)
    # A facade whose subcommands could not be read is a hole in this check, and a hole
    # in a check reads exactly like a clean result. Name it rather than skip it.
    unreadable = sorted(set(facades(root)) - set(subcommands))
    result.contracts["invocations_unreadable"] = unreadable
    for facade in unreadable:
        result.warnings.append(
            f"cli_tools/{facade}.py declares its subcommands in a shape this gate "
            "cannot read, so every prose invocation of it went unchecked"
        )
    for invocation, files in sorted(gone.items()):
        result.errors.append(
            f"`{invocation}` is written in {', '.join(sorted(set(files))[:4])} and "
            f"cli_tools/{invocation.split()[0]}.py has no such subcommand. A "
            "prompt naming a command that does not exist is the drift that stops "
            "a run, not the one that confuses a reader"
        )


def facade_subcommands(root: Path) -> dict[str, list[str]]:
    """`{facade: [subcommand, ...]}` — however that facade happens to declare them.

    This used to read one shape only: a `DISPATCH` literal written over several lines.
    `external.py` writes its on one line and `memory.py` and `verify.py` use argparse
    subparsers, so three of the six facades produced no entry — and a facade with no
    entry was silently skipped by the caller rather than reported. The gate's own
    `invocations_checked` said so, honestly, and nothing read it. `memory.py` is the
    most-invoked facade in the prompts, so the half that was unchecked was the half
    that mattered.
    """
    out: dict[str, list[str]] = {}
    for facade in facades(root):
        text = _read(root, f"cli_tools/{facade}.py")
        if text is None:
            continue
        found: set[str] = set()
        # A DISPATCH literal, over one line or many.
        block = re.search(r"^DISPATCH\s*=\s*\{(.*?)\}", text, re.DOTALL | re.MULTILINE)
        if block:
            found.update(re.findall(r'"([a-z][a-z-]*)"\s*:', block.group(1)))
        # argparse subparsers.
        found.update(re.findall(r'add_parser\(\s*"([a-z][a-z-]*)"', text))
        # Subcommands forwarded before argparse sees them, because they bring an
        # argparse of their own: `if sys.argv[1] == "card-lint": ...`.
        found.update(re.findall(r'sys\.argv\[1\]\s*==\s*"([a-z][a-z-]*)"', text))
        if found:
            out[facade] = sorted(found)
    return out


def check_named_members(
    result: ContractResult,
    root: Path,
    *,
    key: str,
    truth: list[str],
    catalogues: tuple[str, ...],
    where: str,
) -> None:
    """A catalogue that names members must name all of them."""
    for name in catalogues:
        text = _read(root, name)
        if text is None:
            continue
        named = [member for member in truth if re.search(rf"\b{re.escape(member)}\b", text)]
        if not named:
            continue  # not a catalogue of this thing at all
        missing = [member for member in truth if member not in named]
        if missing and len(named) >= max(3, len(truth) // 2):
            result.errors.append(
                f"{key}: {name} names {len(named)} of {len(truth)} and omits "
                f"{', '.join(missing)} ({where})"
            )


def check_concurrency(result: ContractResult, root: Path) -> None:
    speed = declared_concurrency(root)
    codex = codex_threads(root)
    cookbook = _read(root, ".agents/skills/nl-prover/references/orchestrator-cookbook.md")
    stated = None
    if cookbook:
        match = re.search(r"[Uu]p to \*?\*?(\d+)\*?\*? at once", cookbook)
        stated = int(match.group(1)) if match else None
    result.contracts["concurrency"] = {
        "speed.py DECLARED_CONCURRENCY": speed,
        ".codex/config.toml max_threads": codex,
        "orchestrator-cookbook.md": stated,
    }
    # The cookbook decides the policy ceiling; speed.py must carry the same
    # number, because it warns and calls concurrency *unmeasured* whenever the
    # observed value exceeds its own constant -- so a stale copy silently
    # discards the measurement of every run that obeys the policy.
    for label, value in (("speed.py DECLARED_CONCURRENCY", speed),
                         ("orchestrator-cookbook.md", stated)):
        if value is None:
            result.warnings.append(
                f"concurrency: could not read the ceiling from {label}; the "
                "comparison below is running on fewer sources than it thinks. "
                "Every other extractor in this file warns when it reads nothing "
                "-- a check that goes quiet is indistinguishable from one that "
                "passed"
            )
    policy = {
        k: v for k, v in (
            ("speed.py DECLARED_CONCURRENCY", speed),
            ("orchestrator-cookbook.md", stated),
        ) if v is not None
    }
    if len(set(policy.values())) > 1:
        result.errors.append(
            "concurrency ceiling disagrees across its declaration points: "
            + "; ".join(f"{k} = {v}" for k, v in policy.items())
            + ". `gate speed` calls concurrency unmeasured whenever the observed "
            "value exceeds its own constant, so a run obeying the cookbook loses "
            "its own measurement"
        )
    # A platform limit that is actually enforced is a floor under the ceiling,
    # not a competing declaration of it. Only a floor ABOVE the ceiling is a
    # contradiction -- it would promise a concurrency the policy forbids.
    if codex is not None and stated is not None:
        if codex > stated:
            result.errors.append(
                f".codex/config.toml enforces max_threads = {codex} above the "
                f"policy ceiling of {stated} in orchestrator-cookbook.md"
            )
        elif codex < stated:
            result.warnings.append(
                f".codex/config.toml enforces max_threads = {codex} under the "
                f"policy ceiling of {stated}: on Codex the real limit is {codex}. "
                "A platform floor is not drift, but a metric compared across "
                "platforms is comparing two different limits"
            )
    for name in ("CLAUDE.md", "AGENTS.md", ".agents/skills/compute-budget/SKILL.md"):
        text = _read(root, name)
        if text is None or stated is None:
            continue
        for line_number, phrase in _find_counts(text, r"(?:at once|in one batch|in parallel)"):
            value = _as_int(phrase.split()[0])
            if value is not None and value != stated:
                result.errors.append(
                    f"concurrency: {name}:{line_number} says {phrase!r}; the "
                    f"cookbook says {stated}"
                )


def _looks_like_a_workspace(token: str) -> bool:
    """Positively: a path, a placeholder, or a variable. Never a bare word."""
    if token.startswith("-"):
        return False
    return bool(
        "/" in token
        or token.startswith(("<", "{", "$", ".", "~"))
        or re.fullmatch(r"[A-Z_][A-Z0-9_]*", token)
    )


def check_longterm_read(result: ContractResult, root: Path) -> None:
    if not longterm_read_needs_workspace(root):
        result.warnings.append(
            "long-term read: could not confirm from memory.py that the stamp "
            "requires a workspace; check skipped"
        )
        return
    result.contracts["longterm_read"] = "read --tier long-term ... <workspace>"
    # Newlines allowed inside the invocation: these lines wrap in prose, and the
    # only correct site in the repo happens to wrap right before its workspace
    # argument. A line-at-a-time scan calls the correct copy the broken one.
    # Continue onto the next line only when it continues the COMMAND. Allowing
    # any next line made a comment line the workspace argument: in
    # workspace-index-tools.md the invocation is followed by
    # `# local workspace tier`, whose last token is "tier", and the check that
    # had just been fixed for a false positive went silently blind to a real
    # site. A fix that trades a false positive for a false negative is not a fix.
    pattern = re.compile(
        r"memory\.py\s+read\s+--tier\s+long-term[^`\n#]*(?:\n(?![ \t]*[#`])[^`\n#]*)?"
    )
    for name in PROSE:
        text = _read(root, name)
        if text is None:
            continue
        for match in pattern.finditer(text):
            invocation = re.sub(r"\s+", " ", match.group(0)).rstrip("` .—-")
            if re.search(r"(<workspace>|\{workspace[^}]*\}|\$\w*WORKSPACE)", invocation):
                continue
            tail = invocation.split()
            # A workspace argument LOOKS like one: a path, a placeholder, or a
            # variable. "any trailing token that is not a flag" accepted `tier`,
            # `compact` and every other bare word that happened to end the line.
            if tail and _looks_like_a_workspace(tail[-1]):
                continue
            result.errors.append(
                f"long-term read: {name}:{_line_of(text, match.start())} gives "
                f"{invocation!r} with no workspace. memory.py stamps "
                "memory/.longterm_read.json only when a workspace is passed, "
                "and gate stop escalates a missing stamp to an error — so an "
                "orchestrator following this line cannot pass its own stop gate"
            )


def check_memory_render(result: ContractResult, root: Path) -> None:
    on_disk, rendered = rendered_cards(root)
    result.contracts["memory"] = {"cards": on_disk, "rendered": rendered}
    if on_disk and rendered and rendered < on_disk:
        result.warnings.append(
            f"memory.md renders {rendered} of {on_disk} cards in "
            "memory/experience/ — run `memory.py render-longterm`. (Counted by "
            "top-level list items, so a card rendered over several lines can "
            "undercount; treat a small gap as a question)"
        )


# --- the two platform files -----------------------------------------------

# CLAUDE.md's own dual-harness note names exactly these four sections as
# "identical to AGENTS.md and must stay in sync with it". That requirement has
# been stated in prose since the harness shipped and enforced by nothing.
SYNCED_SECTIONS = ("Core Invariants", "Routing", "Tool Rules", "Rules for All Agents")

# Tokens that are SUPPOSED to differ between the two files. Both sides are
# rewritten to the same placeholder before comparing, so a line that differs
# only in dispatch mechanics is not drift.
PLATFORM_TOKENS = (
    (r"\.codex/agents/\*\.toml|\.claude/agents/\*\.md", "<AGENT_REGISTRY>"),
    (r"\.codex/agents|\.claude/agents", "<AGENT_REGISTRY>"),
    (r"\.agents/skills|\.claude/skills", "<SKILLS>"),
    (r"\.codex/settings\.json|\.claude/settings\.json", "<SETTINGS>"),
    (r"\.codex|\.claude", "<PLATFORM_DIR>"),
    (r"Codex custom agents?|Claude Code subagents?", "<AGENT_KIND>"),
    # Numbered, not collapsed. Mapping both names to one placeholder made a
    # line and its logical inverse normalise identically -- "may dispatch on
    # Claude Code but not on Codex" and the reverse both became "may dispatch on
    # <PLATFORM> but not on <PLATFORM>". Every sentence naming both platforms,
    # which the dual-harness note does by construction, was unfalsifiable.
    (r"Claude Code", "<PLATFORM_A>"),
    (r"Codex", "<PLATFORM_B>"),
    (r"subagent_type", "<AGENT_TYPE>"),
)


def _normalise_platform(line: str) -> str:
    for pattern, placeholder in PLATFORM_TOKENS:
        line = re.sub(pattern, placeholder, line)
    return re.sub(r"\s+", " ", line).strip()


def _sections_of(text: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            current = match.group(1).strip()
            out.setdefault(current, [])
            continue
        if current is not None:
            out[current].append(line)
    return out


def check_platform_parity(result: ContractResult, root: Path) -> None:
    """The four sections both platform files promise to keep identical.

    A line that differs only in dispatch mechanics is normalised away. What is
    left is classified two ways, because the two kinds are not equally bad:

      * the same line, said differently on the two sides -> ERROR. That is
        drift: one side was updated and the other was not, and a reader of
        either file cannot tell which one is current.
      * a line one side has and the other does not -> WARNING. It may be a
        legitimate platform-only addition (Codex has no settings.json, so no
        allowlist sentence), and erroring on it would build a list of
        exceptions, which is the rot this gate exists to avoid.
    """
    import difflib

    agents = _read(root, "AGENTS.md")
    claude = _read(root, "CLAUDE.md")
    if agents is None or claude is None:
        result.warnings.append(
            "platform parity: AGENTS.md or CLAUDE.md missing; check skipped"
        )
        return
    left, right = _sections_of(agents), _sections_of(claude)
    parity: dict[str, dict] = {}
    for name in SYNCED_SECTIONS:
        in_left, in_right = name in left, name in right
        if not in_left and not in_right:
            # Neither file organises its content under this heading. That is a
            # different repo, not a drifted one; the first version of this check
            # reported all four as missing "from CLAUDE.md only" on a tree that
            # had neither, which is the check accusing a side at random.
            continue
        if in_left != in_right:
            result.errors.append(
                f"platform parity: section '## {name}' is present in "
                f"{'AGENTS.md' if in_left else 'CLAUDE.md'} only, and the "
                "dual-harness note names it as one that must be identical"
            )
            continue
        a = [_normalise_platform(x) for x in left[name] if x.strip()]
        b = [_normalise_platform(x) for x in right[name] if x.strip()]
        drift, only_a, only_b = [], [], []
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
            None, a, b, autojunk=False
        ).get_opcodes():
            if tag == "replace":
                drift.append((a[i1:i2], b[j1:j2]))
            elif tag == "delete":
                only_a.extend(a[i1:i2])
            elif tag == "insert":
                only_b.extend(b[j1:j2])
        parity[name] = {
            "drift": len(drift), "agents_only": len(only_a), "claude_only": len(only_b)
        }
        for side_a, side_b in drift[:6]:
            result.errors.append(
                f"platform parity: '## {name}' says it differently on the two "
                f"sides. AGENTS.md: {' / '.join(x[:90] for x in side_a[:2])!r} — "
                f"CLAUDE.md: {' / '.join(x[:90] for x in side_b[:2])!r}"
            )
        if len(drift) > 6:
            result.errors.append(
                f"platform parity: '## {name}' has {len(drift) - 6} further "
                "divergences not listed"
            )
        for line in only_a[:4]:
            result.warnings.append(
                f"platform parity: '## {name}' — AGENTS.md only: {line[:120]!r}"
            )
        for line in only_b[:4]:
            result.warnings.append(
                f"platform parity: '## {name}' — CLAUDE.md only: {line[:120]!r}"
            )
    result.contracts["platform_parity"] = parity


def check_hook_claims(result: ContractResult, root: Path) -> None:
    """What CLAUDE.md says about its hooks, against what settings.json enables."""
    settings = _read(root, ".claude/settings.json")
    claude = _read(root, "CLAUDE.md")
    if settings is None or claude is None:
        return
    try:
        hooks = json.loads(settings).get("hooks") or {}
    except json.JSONDecodeError as error:
        result.errors.append(f".claude/settings.json does not parse: {error}")
        return
    enabled = sorted(
        f"{event}:{h.get('matcher', '*')}"
        for event, entries in hooks.items()
        for h in (entries or [])
    )
    result.contracts["hooks"] = enabled
    claims_none = re.search(
        r"none is enabled by default|no hooks? (?:are|is) enabled", claude
    )
    if enabled and claims_none:
        result.errors.append(
            f"CLAUDE.md says no hook is enabled by default, but "
            f".claude/settings.json enables {len(enabled)}: {', '.join(enabled)}"
        )
    elif not enabled and not claims_none and "## Hooks" in claude:
        result.warnings.append(
            "CLAUDE.md documents hooks but .claude/settings.json enables none; "
            "say so, or a reader will assume one is running"
        )


PRESTOP_SSOT = ".agents/skills/nl-prover/references/stop-conditions.md"
PRESTOP_COPIES = (
    "AGENTS.md",
    "CLAUDE.md",
    ".agents/skills/memory-routing/SKILL.md",
    "prompts/orchestration.md",
)
# `gate.py <sub>` and `memory.py <sub>` invocations, in the order they appear.
# Not `[a-z-]+`, which swallowed `--help` and turned a legitimate
# troubleshooting block into two spurious "extra step" errors.
PRESTOP_STEP = re.compile(
    r"cli_tools/(gate|memory)\.py\s+(?!--)([a-z][a-z-]*)", re.MULTILINE
)


def _prestop_sequence(text: str) -> list[str]:
    """The ordered pre-stop steps a file states, deduplicated by first mention.

    Read from fenced blocks only. Prose names these commands constantly for
    other reasons; a sequence is a thing somebody wrote down in order, in a
    block, to be run.
    """
    steps: list[str] = []
    for block in re.findall(r"```[a-z]*\n(.*?)```", text, re.DOTALL):
        if "cli_tools/gate.py stop" not in block:
            continue  # not a stop sequence, just a block that runs something
        for facade, sub in PRESTOP_STEP.findall(block):
            step = f"{facade} {sub}"
            if step not in steps:
                steps.append(step)
    return steps


def check_prestop_sequence(result: ContractResult, root: Path) -> None:
    truth_text = _read(root, PRESTOP_SSOT)
    if truth_text is None:
        result.warnings.append(
            f"pre-stop sequence: {PRESTOP_SSOT} is missing; check skipped"
        )
        return
    truth = _prestop_sequence(truth_text)
    result.contracts["prestop"] = {"ssot": truth, "copies": {}}
    if not truth:
        result.warnings.append(
            f"pre-stop sequence: no sequence found in {PRESTOP_SSOT}; check skipped"
        )
        return
    for name in PRESTOP_COPIES:
        text = _read(root, name)
        if text is None:
            continue
        stated = _prestop_sequence(text)
        if not stated:
            continue  # this file does not restate the sequence, which is ideal
        result.contracts["prestop"]["copies"][name] = stated
        missing = [step for step in truth if step not in stated]
        extra = [step for step in stated if step not in truth]
        if missing:
            result.errors.append(
                f"pre-stop sequence: {name} omits {', '.join(missing)} — "
                f"{PRESTOP_SSOT} is the SSOT and lists {len(truth)} steps. A run "
                "following the short version fails the gate the dropped step "
                "would have satisfied"
            )
        if extra:
            result.errors.append(
                f"pre-stop sequence: {name} adds {', '.join(extra)}, which "
                f"{PRESTOP_SSOT} does not list"
            )
        if not missing and not extra and stated != truth:
            result.warnings.append(
                f"pre-stop sequence: {name} has the same steps in a different "
                f"order than {PRESTOP_SSOT}"
            )


def audit(root: Path) -> ContractResult:
    result = ContractResult()
    root = Path(root)

    check_counted_list(
        result, root,
        key="facades", truth=facades(root), noun=r"(?:tool\s+)?facades?",
        where="cli_tools/*.py",
    )
    check_named_members(
        result, root,
        key="facades", truth=facades(root),
        catalogues=("AGENTS.md", "CLAUDE.md", "README.md", "prompts/orchestration.md"),
        where="cli_tools/*.py",
    )
    check_named_members(
        result, root,
        key="gate subcommands", truth=gate_subcommands(root),
        catalogues=(
            "AGENTS.md", "CLAUDE.md", "README.md", "prompts/orchestration.md",
            "prompts/references/verification-gates.md",
        ),
        where="cli_tools/gate.py DISPATCH",
    )
    check_named_members(
        result, root,
        key="skills", truth=skills(root),
        catalogues=("AGENTS.md", "CLAUDE.md", ".agents/skills/nl-prover/SKILL.md"),
        where=".agents/skills/*/",
    )
    check_invocations_exist(result, root, subcommands=facade_subcommands(root))
    check_concurrency(result, root)
    check_longterm_read(result, root)
    check_nesting_enforcement(result, root)
    check_prestop_sequence(result, root)
    check_platform_parity(result, root)
    check_hook_claims(result, root)
    check_memory_render(result, root)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Facts stated twice, checked against the code that implements them.",
        epilog=REQUIREMENT,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "workspace", nargs="?", default=None,
        help="Ignored; accepted so this gate is invoked like the others.",
    )
    parser.add_argument(
        "--repo", type=Path, default=REPO_ROOT, help="Harness repository root."
    )
    parser.add_argument("--json", action="store_true")
    waiver.add_waiver_arg(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = audit(args.repo)
    result.errors, _waived = waiver.apply_waiver(
        result.errors, args.waive, gate="contracts", workspace=args.workspace,
    )
    if args.json:
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "contracts": result.contracts,
                },
                ensure_ascii=False, indent=2, sort_keys=True,
            )
        )
    else:
        print(f"contracts_gate: {'PASS' if result.ok else 'FAIL'} ({args.repo})")
        for error in result.errors:
            print(f"ERROR: {error}")
        for warning in result.warnings:
            print(f"WARNING: {warning}")
        waiver.print_waived(_waived, args.waive or "")
    if result.errors and not args.json:
        print()
        print(REQUIREMENT)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
