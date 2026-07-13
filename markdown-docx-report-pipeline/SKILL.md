---
name: markdown-docx-report-pipeline
description: Generate Markdown reports or convert Markdown/rough DOCX sources into formatted Word .docx reports using a reference document or existing document style, including Chinese thesis formatting, three-line academic tables, optional MathType equations, and internal PDF/PNG visual QA. Use when the user asks to create Markdown, turn .md into Word, match a thesis or Word template, preserve document formatting, standardize academic tables, handle formulas, or produce a QA-checked report manuscript.
---

# Markdown DOCX Report Pipeline

Create Markdown reports or convert Markdown/rough DOCX content into formatted Word documents. Treat the supplied reference or current target DOCX as the design authority. Customize formatting only when the user asks.

This skill orchestrates:

- `legalrabbit-docx:legalrabbit-docx` for DOCX reading and inspection when available.
- `docx-template-translator` for template inspection and adaptive conversion.
- `MathType-Word/WPS` for editable MathType OLE equations and right-numbered equation paragraphs.

If a dependency is unavailable, follow [Dependency Workflow](references/dependency-workflow.md).

## Decision Tree

1. For Markdown-only requests, produce clean Markdown and preserve headings, image references, LaTeX delimiters, and citation text. Do not create DOCX unless requested.
2. For Word output, identify the source Markdown/DOCX, image assets, final DOCX path, reference DOCX, and formula policy.
3. If a reference DOCX exists or the user says to match a document, inspect its page system, typography, headings, captions, equations, figures, tables, headers, and footers before formatting.
4. If the user asks for a Chinese thesis/dissertation format, read [Chinese Thesis Format](references/chinese-thesis-format.md). Use measured reference values when they differ from its fallback contract.
5. Preserve formulas as visible LaTeX by default. Keep `$...$` inline and `$$...$$` display formulas unless the user explicitly requests OMML, MathType, or editable equations.
6. Finalize DOCX through Word/WPS when available. Export PDF and render page PNGs into a task-local QA directory, inspect every page, and keep those QA artifacts internal unless explicitly requested.

## First-Pass Reliability Guardrails

Apply these rules before the first Word/WPS open. They prevent common OOXML files that are structurally readable but slow or incorrect in desktop Word.

1. Prefer a newly created DOCX package or a verified template-copy workflow. Do not copy a complex reference DOCX and delete its body unless retained relationships, numbering, headers, footers, comments, and section properties have been audited.
2. Leave `w:updateFields` absent or false by default. Update fields explicitly after Word opens cleanly. An automatic update-on-open flag combined with generated PAGE fields can make Word appear to hang.
3. Set the intended heading color at both style and run level. For black thesis headings, write `w:color w:val="000000"` and remove `w:themeColor`, `w:themeTint`, and `w:themeShade`; changing only the RGB value may leave a blue theme override active.
4. Use single/automatic line spacing for every paragraph that contains an inline image (`line=240`, `lineRule=auto`). Never use exact line spacing on image paragraphs because Word clips the image to a narrow horizontal strip.
5. Restart ordered lists explicitly between independent sections. Built-in `List Number` styles can continue numbering across headings. Verify the rendered first number; use a new numbering instance with a tested restart or stable explicit number text when editable numbering is not required.
6. For a short table that should remain on one page, keep the caption with the table, mark rows `cantSplit`, and apply `keep_with_next` through the penultimate row. Do not force a large table to remain together.
7. Use ASCII-only task-local QA filenames such as `input.docx` and `final-check.pdf` when Windows PowerShell 5 or COM is involved. Avoid non-ASCII literals in BOM-free `.ps1` files.
8. Run `scripts/audit_docx_first_pass.py` before Word/WPS finalization. For thesis output, add `--require-black-headings`.
9. Before exporting the full manuscript, smoke-test Word COM with a one-paragraph ASCII-named DOCX. If an isolated hidden Word instance stalls, use an already initialized Word session without closing or changing user documents. Open only the task QA copy, restore application settings, and close only task-created documents.

## Markdown Creation

- Use normal Markdown headings, paragraphs, lists, image syntax, and fenced code.
- Use `$...$` for inline formulas and `$$...$$` for display formulas.
- Keep image paths relative to the Markdown file when possible.
- Preserve user wording unless asked to rewrite.
- Record formatting requirements outside manuscript prose when they are only conversion instructions.

## Markdown to Word Workflow

1. Preflight:
   - Source Markdown or rough DOCX
   - Image asset directory
   - Template/reference DOCX
   - Requested final deliverable path, normally DOCX
   - Task-local QA directory for PDF and PNG files
   - Formula policy: visible LaTeX, inline MathType, display OMML, or display MathType
2. Inspect a reference DOCX through `legalrabbit-docx` when available. Otherwise use deterministic OOXML inspection and record the fallback.
3. Use `docx-template-translator` for template-driven conversion. Copy starter scripts into a writable task directory before patching; do not modify managed skill scripts.
4. Preserve reference formatting unless the user overrides it, including page geometry, body rhythm, heading ladder, caption style, image treatment, table geometry, and equation numbering.
5. For a Chinese thesis/dissertation request, apply [Chinese Thesis Format](references/chinese-thesis-format.md). Measure the retained reference first.
6. For the Chinese technical-report house style, unless a template overrides it:
   - Left-align Heading 2 paragraphs.
   - Keep formulas as visible LaTeX.
   - Center image paragraphs with single line spacing (`line=240`, `lineRule=auto`).
   - Put figure captions in separate centered SimSun 10.5 pt paragraphs below images.
7. Embed actual image files. Keep image paragraphs and captions together when pagination allows.
8. When thesis formatting or three-line tables are requested:
   - Preserve exact DXA geometry.
   - Remove vertical and internal grid lines.
   - Apply measured reference line weights or the fallback values in [Chinese Thesis Format](references/chinese-thesis-format.md).
   - Repeat header rows when needed.
   - Audit border structure and `tblW`/`tblInd`/`tblGrid`/`tcW` consistency for every table.
9. For display MathType equations:
   - Use `MathType-Word/WPS` to insert real `Equation.DSMT4` OLE objects.
   - Keep the equation number as Word text at the right tab.
   - Bookmark the number text for cross-reference.
   - Audit `ole_objects=1`, `ole_progids=['Equation.DSMT4']`, `omath=0`, Equation Native data, and preview cache.
10. Prefer visible LaTeX for inline formulas. If inline MathType clips or renders incompletely, revert inline formulas to LaTeX while retaining display MathType.
11. Finalize and verify:
   - Run `python scripts/audit_docx_first_pass.py <final.docx> --require-black-headings` for black-heading thesis output.
   - On Windows, export an ASCII-named QA copy through Word. Prefer `SaveAs2(<pdf>, 17)` when `ExportAsFixedFormat` stalls.
   - DOCX opens and saves cleanly.
   - Internal QA PDF is nonempty.
   - Every rendered page is inspected at 100% zoom.
   - Headings, margins, headers, footers, images, captions, tables, equations, and page breaks match the requested format.
   - Three-line tables contain only top, header-separator, and bottom rules.
   - No clipping, overlap, missing glyphs, orphan captions, broken tables, or avoidable blank pages remain.
12. Deliver only the requested artifact. Do not place or link QA PDFs, PNGs, contact sheets, or render directories beside the final DOCX unless explicitly requested.

## Fast Failure Triage

- Word hangs while opening: inspect `word/settings.xml` for `w:updateFields` before rebuilding the document or blaming package corruption.
- A figure renders as a thin strip: inspect the image paragraph and its style for `lineRule="exact"`; switch it to automatic/single spacing.
- Headings remain blue after setting RGB: remove theme-color attributes from heading styles and heading runs.
- A new list begins at 6 or another carried value: do not reuse the built-in list instance; restart or use explicit number text.
- A three-line table splits despite fitting on one page: keep its caption and rows together, but retain `cantSplit` rather than fixed row heights.
- PowerShell reports garbled Chinese paths: pass paths as parameters or use an ASCII QA copy; do not embed Chinese literals in a BOM-free Windows PowerShell script.
- `ExportAsFixedFormat` stalls: close only task-opened QA documents and retry through `SaveAs2(..., 17)`; do not accumulate hidden Word instances.

## Quality Gates

Do not report completion until all applicable gates pass or a limitation is disclosed:

- No unresolved placeholders, template sample names, or red instruction text remain.
- Formula policy matches the user's latest instruction.
- Visible-LaTeX requests contain no substituted OMML, MathType OLE, or formula placeholders.
- Right-numbered MathType equations bookmark the number text, not the OLE object.
- The requested final DOCX exists.
- Internal QA PDF and page PNGs were generated and visually checked, or the rendering fallback was disclosed.
- Required three-line tables pass border and exact-geometry audits.
- Image paragraphs use automatic/single spacing and render at their intended full height.
- Heading colors match the reference after theme attributes are considered, not only direct RGB values.
- Independent ordered lists begin with the intended number in the rendered PDF.
- `w:updateFields` is absent/false unless automatic opening-time field updates are explicitly required and tested.
- QA PDF/PNG artifacts remain outside the deliverable location and are not linked or returned unless requested.
- Any fallback, skipped validation, or dependency limitation is stated clearly.
