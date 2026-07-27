# Math Notation Rules

Use these rules when transcribing mathematical sources, especially PDFs.

## Delimiters

- Inline math: `$...$`
- Display math:
  ```latex
  $$
  ...
  $$
  ```
- Preserve equation numbers using `\tag{n}` inside the display block.

## Font Faces

Font faces are semantically significant. Do not conflate them.

| Visual appearance | LaTeX command | Common use |
|---|---|---|
| Blackboard bold | `\mathbb{}` | number fields, probability spaces |
| Calligraphic/script | `\mathcal{}` | categories, sheaves, filtrations |
| Fraktur | `\mathfrak{}` | Lie algebras, ideals, p-adic valuations |
| Bold roman | `\mathbf{}` | vectors, matrices |
| Sans-serif | `\mathsf{}` | categories or named structures |

Never substitute Unicode math characters for LaTeX commands in wiki pages.

If genuinely uncertain, write the best transcription and add:

```markdown
<!-- VERIFY: \mathcal{O} — could be \mathscr{O} -->
```

## Source Language

Translate prose to English while writing wiki pages. Do not translate
mathematical notation.
