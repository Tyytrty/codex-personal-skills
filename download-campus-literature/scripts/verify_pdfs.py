#!/usr/bin/env python3
"""Validate downloaded PDFs and print a compact summary."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def inspect_pdf(path: Path) -> tuple[bool, str, str]:
    if path.stat().st_size < 10_000:
        return False, "too_small", ""
    with path.open("rb") as handle:
        if handle.read(5) != b"%PDF-":
            return False, "bad_header", ""
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        pages = len(reader.pages)
        title = ""
        if reader.metadata:
            title = str(reader.metadata.title or "")
        if pages < 1:
            return False, "zero_pages", title
        return True, f"{pages}_pages", title
    except ImportError:
        return True, "header_ok_no_pypdf", ""
    except Exception as exc:
        return False, "parse_error:" + type(exc).__name__, ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    rows: list[dict[str, str]] = []
    for path in sorted(args.directory.glob("*.pdf")):
        valid, note, title = inspect_pdf(path)
        rows.append(
            {
                "file": path.name,
                "valid": str(valid).lower(),
                "bytes": str(path.stat().st_size),
                "note": note,
                "title": title,
            }
        )
        print(f"{'OK' if valid else 'FAIL'}\t{path.name}\t{note}")

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["file", "valid", "bytes", "note", "title"],
            )
            writer.writeheader()
            writer.writerows(rows)

    valid_count = sum(row["valid"] == "true" for row in rows)
    print(f"Summary: valid={valid_count}, invalid={len(rows) - valid_count}")
    return 0 if valid_count == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
