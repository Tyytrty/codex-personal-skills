# Chinese Thesis Format

Use this contract when the user asks for a Chinese thesis/dissertation layout, says to match a retained thesis, or requests standardized three-line academic tables. A supplied reference DOCX is always authoritative: measure it first and replace any fallback value below that differs.

## Page and Running Elements

- Use A4 portrait pages.
- Fallback margins: top and bottom 35 mm; left and right 32 mm.
- Fallback header distance: 26 mm. Fallback footer distance: 24 mm.
- Reproduce the reference header rule, alignment, and font, but do not copy thesis-specific identity text into another document. Use target-appropriate running text such as the report title.
- Center page numbers in the footer using Times New Roman 10.5 pt unless the reference differs.

## Typography and Paragraph Rhythm

- Body: SimSun for Chinese, Times New Roman for Latin text and numbers, 12 pt; justified; first-line indent 24 pt; exact 20 pt line spacing; 0 pt before and after.
- Chapter title: SimHei/Times New Roman, 18 pt, not bold; centered; exact 20 pt line spacing; 24 pt before and after.
- Section heading such as `3.1`: SimHei/Times New Roman, 16 pt, not bold; left aligned; exact 20 pt line spacing; 18 pt before and after.
- Subsection heading such as `3.1.1`: SimHei/Times New Roman, 14 pt, not bold; left aligned; exact 20 pt line spacing; 12 pt before and after.
- Use black headings unless the measured reference explicitly uses another color. Set black at style and run level, and remove `w:themeColor`, `w:themeTint`, and `w:themeShade` so Word does not retain the default blue heading theme.
- Figure caption: SimSun/Times New Roman, 10.5 pt; centered; no first-line indent; 2.5 pt after.
- Table caption: SimSun/Times New Roman, 10.5 pt; centered; exact 20 pt line spacing; 7.8 pt before; keep with the table.
- Image paragraph: centered; 5 pt before; automatic/single line spacing (`line=240`, `lineRule=auto`); keep the image and its caption together when pagination allows. Never apply exact line spacing to a paragraph containing an inline image.
- Preserve the selected formula policy. Matching thesis typography does not authorize conversion from visible LaTeX to OMML or MathType.

## Three-Line Academic Tables

Apply these rules to every requested three-line table:

- Remove left, right, vertical, and internal horizontal grid lines.
- Use a 1.5 pt single top rule and 1.5 pt single bottom rule (`w:sz=12`).
- Use a 0.5 pt single separator below the header row (`w:sz=4`).
- Apply the top and header separator rules to first-row cells and the bottom rule to final-row cells so the structure survives Word rendering.
- Use no header shading unless the reference explicitly has it.
- Use SimSun/Times New Roman 10.5 pt by default. Center short values and headers; left-align narrative cells when needed.
- Vertically center cell content. Do not use fixed row heights; allow wrapping.
- Preserve or calculate exact DXA widths so `tblW`, `tblInd`, `tblGrid`, every `tcW`, and the start cell margin agree. Keep the table within the measured text block.
- Repeat the header row when a table spans pages.
- Keep each table caption attached to its table. Remove stale forced page breaks that create avoidable blank areas.
- For a table that fits on one page, mark rows `cantSplit` and keep rows together through the penultimate row. Allow long tables to paginate naturally.

Audit every table structurally and visually. Fail the QA gate if any vertical line, internal grid, mismatched width, clipped cell, or orphan caption remains.

## Internal QA and Delivery

1. Finalize the DOCX through Word or WPS when available.
2. Before opening Word, run `scripts/audit_docx_first_pass.py` with `--require-black-headings`. Leave `w:updateFields` absent/false unless opening-time field updates are explicitly required and tested.
3. Export a PDF into a task-local hidden or temporary QA directory, not beside the final DOCX. On Windows, use an ASCII-named QA copy, smoke-test COM first, and use `SaveAs2(..., 17)` if `ExportAsFixedFormat` stalls.
4. Render all PDF pages to PNG and inspect every page at 100% zoom.
5. Check fonts, heading colors after theme resolution, margins, headers, footers, page numbers, full image height, captions, list restarts, three-line tables, clipping, overlaps, and avoidable blank pages.
6. Iterate and regenerate QA artifacts after every layout-sensitive change.
7. Deliver only the requested DOCX. Do not link or separately output the QA PDF, page PNGs, or contact sheets unless the user explicitly requests them.
