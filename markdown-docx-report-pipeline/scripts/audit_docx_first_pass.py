#!/usr/bin/env python3
"""Catch Word/DOCX first-open risks before desktop rendering."""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def attr(node, name, default=None):
    return node.get(f"{W}{name}", default) if node is not None else default


def load_xml(zf: zipfile.ZipFile, name: str):
    return ET.fromstring(zf.read(name))


def style_map(styles_root):
    result = {}
    for style in styles_root.findall(f"{W}style"):
        style_id = attr(style, "styleId")
        if style_id:
            result[style_id] = style
    return result


def heading_style_ids(styles):
    ids = set()
    for style_id, style in styles.items():
        name = style.find(f"{W}name")
        value = attr(name, "val", "").lower().replace(" ", "")
        if style_id.lower() in {"heading1", "heading2", "heading3"} or value in {"heading1", "heading2", "heading3"}:
            ids.add(style_id)
    return ids


def color_problem(color):
    if color is None:
        return "missing explicit black color"
    value = attr(color, "val", "").upper()
    themed = any(attr(color, key) is not None for key in ("themeColor", "themeTint", "themeShade"))
    if value != "000000":
        return f"color is {value or 'unset'}, not 000000"
    if themed:
        return "theme color attributes remain"
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("docx", type=Path)
    parser.add_argument("--require-black-headings", action="store_true")
    parser.add_argument("--allow-update-fields", action="store_true")
    args = parser.parse_args()

    errors = []
    warnings = []
    if not args.docx.is_file():
        parser.error(f"DOCX not found: {args.docx}")

    try:
        with zipfile.ZipFile(args.docx) as zf:
            xml_names = [n for n in zf.namelist() if n.endswith((".xml", ".rels"))]
            for name in xml_names:
                try:
                    load_xml(zf, name)
                except ET.ParseError as exc:
                    errors.append(f"malformed XML: {name}: {exc}")

            document = load_xml(zf, "word/document.xml")
            styles_root = load_xml(zf, "word/styles.xml")
            settings = load_xml(zf, "word/settings.xml")
            styles = style_map(styles_root)

            update = settings.find(f"{W}updateFields")
            if not args.allow_update_fields and update is not None and attr(update, "val", "true").lower() not in {"0", "false", "off"}:
                errors.append("w:updateFields is enabled; leave it absent/false before first Word open")

            hids = heading_style_ids(styles)
            if args.require_black_headings:
                for style_id in sorted(hids):
                    style = styles[style_id]
                    problem = color_problem(style.find(f"{W}rPr/{W}color"))
                    if problem:
                        errors.append(f"heading style {style_id}: {problem}")

                for index, paragraph in enumerate(document.iter(f"{W}p"), start=1):
                    pstyle = paragraph.find(f"{W}pPr/{W}pStyle")
                    if attr(pstyle, "val") not in hids:
                        continue
                    for run in paragraph.findall(f"{W}r"):
                        color = run.find(f"{W}rPr/{W}color")
                        if color is not None:
                            problem = color_problem(color)
                            if problem:
                                errors.append(f"heading paragraph {index}: {problem}")

            for index, paragraph in enumerate(document.iter(f"{W}p"), start=1):
                if paragraph.find(f".//{W}drawing") is None:
                    continue
                spacing = paragraph.find(f"{W}pPr/{W}spacing")
                pstyle = paragraph.find(f"{W}pPr/{W}pStyle")
                if spacing is None and attr(pstyle, "val") in styles:
                    spacing = styles[attr(pstyle, "val")].find(f"{W}pPr/{W}spacing")
                if attr(spacing, "lineRule", "auto") == "exact":
                    errors.append(f"image paragraph {index} uses exact line spacing and may clip")

            visible_text = "".join(node.text or "" for node in document.iter(f"{W}t"))
            for token in ("TODO", "待插入", "<!--"):
                if token in visible_text:
                    errors.append(f"unresolved placeholder token: {token}")

            if not hids:
                warnings.append("no Heading 1/2/3 styles detected")

    except (zipfile.BadZipFile, KeyError) as exc:
        errors.append(f"invalid DOCX package: {exc}")

    for item in warnings:
        print(f"WARNING: {item}")
    for item in errors:
        print(f"ERROR: {item}")
    if errors:
        print(f"FAIL: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"PASS: 0 errors, {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
