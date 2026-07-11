# Dependency Workflow

Use this reference when `markdown-docx-report-pipeline` needs to ensure its companion skills and tools are available.

## Required Companion Skills

This skill depends on:

- `legalrabbit-docx:legalrabbit-docx`
- `MathType-Word/WPS`
- `docx-template-translator`

When any companion skill is named by the user or required by the task, read that companion skill's `SKILL.md` before using it.

## Installing Missing Skills

If `docx-template-translator` is missing, use `skill-installer` and install from:

```powershell
python "$env:CODEX_HOME/skills/.system/skill-installer/scripts/install-skill-from-github.py" --repo zouchenzhen/docx-template-translator-skill --path skills/docx-template-translator
```

If `legalrabbit-docx` is missing, search for the `legalrabbit-tools` / `legalrabbit-docx` plugin and request plugin installation when a matching install candidate is available. If plugin install tools are unavailable, tell the user that `legalrabbit-docx` is not callable and continue with deterministic OOXML fallback only when the user accepts that fallback.

If `MathType-Word/WPS` is missing, first search the local `$CODEX_HOME/skills` and known skill repositories if the user supplied a URL. If no source is known, ask the user for the skill repository or install source. Do not pretend MathType conversion is possible without the skill instructions.

After installing skills, tell the user to restart Codex to pick up newly installed skills when required by the installer.

## Runtime Checks

For MathType work:

1. Run:

```powershell
python "<MathType-Word/WPS>/scripts/mathtype_word_wps.py" check-env
```

2. If activation/runtime is uncertain, run:

```powershell
python "<MathType-Word/WPS>/scripts/mathtype_word_wps.py" check-env --probe-mathtype
```

3. Stop and report if `Equation.DSMT4` is not registered, MathType is missing, or MathType appears unlicensed/not activated.

## Preferred Equation Policy

Default formula policy for Markdown-to-Word reports:

- Keep inline formulas as `$...$` LaTeX text unless the user explicitly requests inline MathType.
- Convert display equations to MathType only when the user asks for editable MathType or right-numbered equations.
- Put right equation numbers in Word text and bookmark the number text. Do not put the number inside the MathType object.

If inline MathType displays incomplete or clipped in the PDF preview, revert inline formulas to LaTeX text and keep display equations as MathType.

## Validation Commands

Use `docx-template-translator` scripts when available:

```powershell
python "<docx-template-translator>/scripts/finalize_word_docx.py" "<final.docx>" --pdf --pdf-out "<final.pdf>"
python "<docx-template-translator>/scripts/render_pdf_preview.py" "<final.pdf>" --pages 1-4 --dpi 120 --columns 2 --out "<preview.png>"
```

For MathType equation paragraphs, inspect representative paragraphs:

```powershell
python "<MathType-Word/WPS>/scripts/mathtype_word_wps.py" inspect-docx --docx "<final.docx>" --paragraph-index <index>
```

Expected display-equation result:

- `ole_objects=1`
- `ole_progids=['Equation.DSMT4']`
- `omath=0`
- `Equation Native` present
- right-number text visible in the paragraph
- bookmark exists around the number text

## Fallback Rules

- Prefer companion skills over ad hoc implementations.
- If a companion skill is unavailable and cannot be installed, use deterministic OOXML operations only for narrow, inspectable edits.
- Always disclose fallback use in the final response.
