# Style Profile

Create or reuse `writer/style_profile.md` before drafting substantial prose or
local rewrites.

## What To Read

Prefer reliable reader-facing style sources:

1. human style, audience, venue, or language instructions;
2. an existing polished article or accepted proof summary;
3. surrounding context for a local rewrite;
4. accepted `proof.tex`, only when it reads like a coherent proof rather than a
   mechanically merged run artifact.

If style sources conflict, follow the human instruction first. If no reliable
style source exists, use the default research-note/paper profile below.

## Default Profile

Record this when no better profile is available:

```markdown
# Style Profile

Language: English
Register: research note / paper
Format: LaTeX
Audience: mathematician familiar with the general area, not with the run history
Structure: theorem/proof centered, with short motivation only when useful
Notation: introduce before use; preserve accepted symbols and hypotheses
Citations: preserve known citations; mark missing citations as TODO
Exposition: separate intuition from formal proof
Forbidden: agent history, scheduling details, long internal path lists, blog tone
```

## Mechanical-Merge Guard

Do not blindly imitate `proof.tex` merely because it exists. Treat `proof.tex`
as a content source, not a style source, when it contains:

- repeated lemma-generator phrasing;
- verifier or route-history language;
- inconsistent theorem/proof environments;
- file-path-heavy explanations;
- abrupt assembly transitions;
- progress/restart state written as prose.

In that case, keep the mathematical content and use the default profile.
