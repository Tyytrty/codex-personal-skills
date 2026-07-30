#!/usr/bin/env python3
"""Match browser-downloaded PDFs to queued papers and optionally archive them."""

from __future__ import annotations

import argparse
import csv
import logging
import re
import shutil
import time
from difflib import SequenceMatcher
from pathlib import Path


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def safe_name(value: str, limit: int = 120) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    value = re.sub(r"\s+", " ", value).strip(" ._")
    return value[:limit].rstrip(" ._") or "untitled"


def inspect_pdf(path: Path) -> tuple[bool, str]:
    if path.stat().st_size < 10_000:
        return False, ""
    with path.open("rb") as handle:
        if handle.read(5) != b"%PDF-":
            return False, ""
    parts = [path.stem]
    try:
        from pypdf import PdfReader

        logging.getLogger("pypdf").setLevel(logging.ERROR)
        reader = PdfReader(str(path))
        if reader.metadata and reader.metadata.title:
            parts.append(str(reader.metadata.title))
        for page in reader.pages[:2]:
            parts.append(page.extract_text() or "")
    except Exception:
        pass
    return True, normalize(" ".join(parts))


def score(row: dict[str, str], document_text: str) -> float:
    doi = normalize(row.get("doi", ""))
    title = normalize(row.get("title", ""))
    if doi and doi in document_text:
        return 1.0
    if not title:
        return 0.0
    title_words = set(title.split())
    doc_words = set(document_text.split())
    overlap = len(title_words & doc_words) / max(1, len(title_words))
    sequence = SequenceMatcher(None, title, document_text[: len(title) * 3]).ratio()
    return max(overlap, sequence)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("queue", type=Path)
    parser.add_argument("--downloads", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--report", type=Path, default=Path("reconcile_report.csv"))
    parser.add_argument("--min-score", type=float, default=0.72)
    parser.add_argument(
        "--recent-minutes",
        type=float,
        default=0,
        help="Only inspect PDFs modified within this many minutes; 0 means all",
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    queue = read_rows(args.queue)
    documents: list[tuple[Path, str]] = []
    cutoff = (
        time.time() - args.recent_minutes * 60
        if args.recent_minutes > 0
        else 0
    )
    for path in sorted(args.downloads.glob("*.pdf")):
        if path.stat().st_mtime < cutoff:
            continue
        valid, text = inspect_pdf(path)
        if valid:
            documents.append((path, text))

    candidates: list[tuple[float, int, int]] = []
    for row_index, row in enumerate(queue):
        for doc_index, (_, text) in enumerate(documents):
            value = score(row, text)
            if value >= args.min_score:
                candidates.append((value, row_index, doc_index))
    candidates.sort(reverse=True)

    used_rows: set[int] = set()
    used_docs: set[int] = set()
    report: list[dict[str, str]] = []
    assignments: dict[str, str] = {}
    for value, row_index, doc_index in candidates:
        if row_index in used_rows or doc_index in used_docs:
            continue
        used_rows.add(row_index)
        used_docs.add(doc_index)
        row = queue[row_index]
        source = documents[doc_index][0]
        index = int(row.get("index") or row_index + 1)
        doi_key = safe_name(row.get("doi", ""), 70)
        title = safe_name(row.get("title") or source.stem)
        destination = args.output_dir / f"{index:03d}_{doi_key}_{title}.pdf"
        action = "planned"
        if args.apply:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            action = "copied"
            assignments[row.get("doi", "")] = str(destination)
        report.append(
            {
                "index": str(index),
                "doi": row.get("doi", ""),
                "score": f"{value:.3f}",
                "source": str(source),
                "destination": str(destination),
                "action": action,
            }
        )

    write_rows(args.report, report)
    if args.apply and args.manifest and args.manifest.exists():
        manifest = read_rows(args.manifest)
        for row in manifest:
            destination = assignments.get(row.get("doi", ""))
            if destination:
                row["status"] = "browser_downloaded"
                row["file"] = destination
                row["source"] = "browser"
                row["note"] = (
                    row.get("note", "") + "; reconciled_browser_download"
                ).strip("; ")
        write_rows(args.manifest, manifest)

    print(
        f"Summary: queue={len(queue)}, pdfs={len(documents)}, "
        f"matched={len(report)}, mode={'apply' if args.apply else 'dry-run'}"
    )
    print(f"Report: {args.report.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
