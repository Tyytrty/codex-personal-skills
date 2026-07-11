---
name: markdown-docx-report-pipeline
description: Generate Markdown reports or convert Markdown/rough DOCX sources into formatted Word .docx reports using a reference document or existing document style, with optional MathType equation handling, right-numbered equation references, PDF preview validation, and fallback dependency installation. Use when the user asks to create a Markdown document, turn .md into Word, preserve a document's format, apply a Word template, handle MathType formulas, or produce a QA-checked report manuscript.
---

# Markdown DOCX Report Pipeline

Use this skill to create a Markdown report or convert Markdown into a formatted Word document. Default to the format of the provided template/reference/current target document; only customize formatting when the user asks.

This skill orchestrates these dependencies:

- `legalrabbit-docx:legalrabbit-docx` for reading, creating, editing, and inspecting `.docx` files whenever its MCP tools are available.
- `docx-template-translator` for template inspection, adaptive Markdown/PDF/LaTeX-to-DOCX conversion, Word finalization, PDF export, and visual QA.
- `MathType-Word/WPS` for editable MathType OLE equations and right-numbered equation paragraphs.

If any dependency is not available, follow [Dependency Workflow](references/dependency-workflow.md) before continuing.

## Decision Tree

1. If the user asks for a Markdown document only, generate clean Markdown first. Preserve source structure, image references, LaTeX math delimiters, and citation text. Do not create DOCX unless requested.
2. If the user asks to convert `.md` to Word, identify the source `.md`, image asset folder, output path, and formatting source.
3. If a template/reference `.docx` exists or the user says "use this document's format", inspect that document before formatting. Prefer its page size, margins, heading alignment, fonts, line spacing, captions, figure sizing, and equation numbering style.
4. If formulas are present, default to preserving all formulas as visible LaTeX text in Word. Keep inline formulas with `$...$` delimiters and display formulas with `$$...$$` delimiters unless the user explicitly requests OMML, MathType, or editable equations.
5. If the user requests MathType right numbering, create right-numbered display equation paragraphs with the number as Word text, not inside MathType, and add bookmarks such as `eq_2_1` for later cross-reference.
6. Always finalize DOCX through Word/WPS when available, export a PDF beside the DOCX, render a preview/contact sheet, and inspect representative pages before reporting success.

## Markdown Creation

When generating Markdown:

- Use normal Markdown headings, paragraphs, numbered lists, image syntax, and fenced code where needed.
- Use `$...$` for inline formulas and `$$...$$` for display formulas.
- Keep image paths relative to the Markdown file when possible.
- Preserve user-provided wording unless asked to rewrite.
- If the user provides formatting requirements for a later Word conversion, record them in the Markdown-adjacent notes or in a run report, but do not pollute the manuscript text.

## Markdown To Word Workflow

1. Preflight inputs:
   - Source `.md`
   - Image asset directory
   - Template/reference `.docx` if provided
   - Output `.docx` and `.pdf`
   - Formula policy: visible LaTeX text, inline MathType, display OMML, or display MathType
2. Read any `.docx` template/reference through `legalrabbit-docx` when the MCP tools are available. If unavailable, use deterministic OOXML inspection and note the fallback.
3. Use `docx-template-translator` for template-driven conversion. Copy any bundled starter pipeline into the project/output directory before patching; do not modify bundled skill scripts in place.
4. Preserve the template's default formatting unless the user gives overrides. Common defaults from a reference document include:
   - Heading 1/2/3 alignment and spacing
   - Body font, body line spacing, and first-line indent
   - Figure width and image paragraph line spacing
   - Caption style
   - Equation paragraph tab stops and numbering
5. When the user requests the report-house style used for Chinese technical reports, enforce these defaults unless a template overrides them:
   - Heading 2 paragraphs are left aligned.
   - Formulas remain as visible LaTeX text; do not convert them to OMML or MathType.
   - Image paragraphs are centered with single line spacing (`line=240`, `lineRule=auto`).
   - Figure names/captions are separate paragraphs immediately below the image, centered, SimSun/宋体 10.5 pt, with 0.5-line space after the paragraph.
5. For images, embed actual image files and set image paragraphs to the template's expected line spacing. If the user says "图片单倍行距", enforce `line=240` and `lineRule=auto`.
6. For display equations requiring MathType, use `MathType-Word/WPS`:
   - Generate MathML or LaTeX source for each display equation.
   - Insert real `Equation.DSMT4` OLE objects.
   - Put the equation number as Word text at the right tab.
   - Add a bookmark around the number text for cross-reference.
   - Inspect each equation paragraph for `ole_objects=1`, `ole_progids=['Equation.DSMT4']`, `omath=0`, `Equation Native` present, and clean preview cache.
7. For inline formulas, prefer LaTeX text unless the user explicitly requests inline MathType and accepts the rendering risk. If inline MathType displays clipped or incomplete, revert inline formulas to `$...$` LaTeX text and keep display equations as MathType.
8. Finalize with Word/WPS, export PDF, render preview, and verify:
   - DOCX opens and saves cleanly.
   - PDF is nonempty.
   - Headings match requested alignment.
   - Images are visible and correctly spaced.
   - Display equations and right numbers are visible.
   - MathType audit passes for MathType equation paragraphs.

## Quality Gates

Do not report completion until these are true or explicitly waived:

- No unresolved placeholders such as `MTINLINE001`, `MTDISPLAY001`, template sample names, or red instruction text remain.
- Formula policy matches the user's latest instruction.
- When LaTeX formula policy is requested, no OMML, MathType OLE objects, or formula placeholders replace the visible LaTeX source.
- Right-numbered MathType display equations have bookmarks on the number text, not on the MathType object.
- The final DOCX and PDF are both present.
- A PDF preview/contact sheet has been visually checked.
- Any fallback, skipped validation, or dependency limitation is stated clearly.
