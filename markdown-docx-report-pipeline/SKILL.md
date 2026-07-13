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
   - DOCX opens and saves cleanly.
   - Internal QA PDF is nonempty.
   - Every rendered page is inspected at 100% zoom.
   - Headings, margins, headers, footers, images, captions, tables, equations, and page breaks match the requested format.
   - Three-line tables contain only top, header-separator, and bottom rules.
   - No clipping, overlap, missing glyphs, orphan captions, broken tables, or avoidable blank pages remain.
12. Deliver only the requested artifact. Do not place or link QA PDFs, PNGs, contact sheets, or render directories beside the final DOCX unless explicitly requested.

## Quality Gates

Do not report completion until all applicable gates pass or a limitation is disclosed:

- No unresolved placeholders, template sample names, or red instruction text remain.
- Formula policy matches the user's latest instruction.
- Visible-LaTeX requests contain no substituted OMML, MathType OLE, or formula placeholders.
- Right-numbered MathType equations bookmark the number text, not the OLE object.
- The requested final DOCX exists.
- Internal QA PDF and page PNGs were generated and visually checked, or the rendering fallback was disclosed.
- Required three-line tables pass border and exact-geometry audits.
- QA PDF/PNG artifacts remain outside the deliverable location and are not linked or returned unless requested.
- Any fallback, skipped validation, or dependency limitation is stated clearly.
