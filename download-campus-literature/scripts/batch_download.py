#!/usr/bin/env python3
"""Script-first downloader for legal OA and campus-authorized scholarly PDFs.

The script never bypasses authentication, CAPTCHAs, paywalls, rate limits, or
publisher access controls. Browser-only cases are written to a compact queue.
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse

try:
    import requests
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Install requests: python -m pip install requests") from exc


DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
OPENALEX_RE = re.compile(r"https?://openalex\.org/(W\d+)", re.IGNORECASE)
USER_AGENT = (
    "CampusLiteratureDownloader/1.0 "
    "(legal OA and institution-authorized access; contact={contact})"
)
FIELDNAMES = [
    "index",
    "doi",
    "openalex_id",
    "title",
    "publisher",
    "status",
    "file",
    "source",
    "landing_url",
    "candidate_url",
    "note",
]


@dataclass
class Entry:
    index: int
    doi: str
    openalex_id: str = ""
    title: str = ""


class PdfMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def add(self, value: str) -> None:
        value = html.unescape(value.strip())
        if value and value not in self.urls:
            self.urls.append(value)

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        data = {key.lower(): value or "" for key, value in attrs}
        tag = tag.lower()
        if tag == "meta":
            key = (data.get("name") or data.get("property") or "").lower()
            if key in {"citation_pdf_url", "eprints.document_url"}:
                self.add(data.get("content", ""))
        elif tag == "link" and "pdf" in data.get("type", "").lower():
            self.add(data.get("href", ""))
        elif tag == "a":
            href = data.get("href", "")
            if re.search(r"(?:/pdf(?:/|$)|\.pdf(?:[?#]|$))", href, re.I):
                self.add(href)


def normalize_doi(value: str) -> str:
    return value.strip().rstrip(".,;:)]}").lower()


def title_from_context(text: str, start: int) -> str:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", start)
    if line_end < 0:
        line_end = len(text)
    line = " ".join(text[line_start:line_end].split())
    line = re.sub(r"^\[\d+\]\s*", "", line)
    line = re.sub(r"\s*(?:DOI\s*:|https?://doi\.org/).*$", "", line, flags=re.I)
    if "[J" in line:
        line = line.split("[J", 1)[0]
    return line[-180:].strip(" .")


def parse_entries(text: str) -> list[Entry]:
    openalex_by_line: dict[int, str] = {}
    for line_number, line in enumerate(text.splitlines()):
        match = OPENALEX_RE.search(line)
        if match:
            openalex_by_line[line_number] = match.group(1).upper()

    seen: set[str] = set()
    entries: list[Entry] = []
    for match in DOI_RE.finditer(text):
        doi = normalize_doi(match.group(0))
        if doi in seen:
            continue
        seen.add(doi)
        line_number = text.count("\n", 0, match.start())
        entries.append(
            Entry(
                index=len(entries) + 1,
                doi=doi,
                openalex_id=openalex_by_line.get(line_number, ""),
                title=title_from_context(text, match.start()),
            )
        )
    return entries


def safe_name(value: str, max_length: int = 130) -> str:
    value = html.unescape(value)
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    value = re.sub(r"\s+", " ", value).strip(" ._")
    return value[:max_length].rstrip(" ._") or "untitled"


def publisher_for(doi: str, url: str = "") -> str:
    prefix_map = [
        ("10.1016/", "Elsevier"),
        ("10.3390/", "MDPI"),
        ("10.1109/", "IEEE"),
        ("10.1007/", "Springer"),
        ("10.1038/", "Nature"),
        ("10.1002/", "Wiley"),
        ("10.1080/", "Taylor & Francis"),
        ("10.1021/", "ACS"),
        ("10.3389/", "Frontiers"),
        ("10.1364/", "Optica"),
        ("10.1117/", "SPIE"),
        ("10.1177/", "SAGE"),
    ]
    for prefix, name in prefix_map:
        if doi.startswith(prefix):
            return name
    host = urlparse(url).netloc.lower()
    host_map = {
        "sciencedirect.com": "Elsevier",
        "mdpi.com": "MDPI",
        "ieeexplore.ieee.org": "IEEE",
        "link.springer.com": "Springer",
        "nature.com": "Nature",
        "onlinelibrary.wiley.com": "Wiley",
        "tandfonline.com": "Taylor & Francis",
        "pubs.acs.org": "ACS",
        "frontiersin.org": "Frontiers",
    }
    for suffix, name in host_map.items():
        if host == suffix or host.endswith("." + suffix):
            return name
    return "Other"


def classify_html(data: bytes) -> str:
    text = data[:250_000].decode("utf-8", errors="ignore").lower()
    if any(
        token in text
        for token in (
            "captcha",
            "cf-chl-",
            "cloudflare",
            "verify you are human",
            "security challenge",
        )
    ):
        return "needs_browser_captcha"
    if any(
        token in text
        for token in (
            "access denied",
            "institutional login",
            "sign in to access",
            "purchase pdf",
            "subscribe to access",
            "ip blocked",
            "cpe00001",
        )
    ):
        return "needs_browser_access"
    return "invalid_pdf"


def request_json(
    session: requests.Session, url: str, timeout: int
) -> dict:
    response = session.get(url, timeout=timeout)
    if response.status_code == 404:
        return {}
    response.raise_for_status()
    return response.json()


def openalex_work(
    session: requests.Session, entry: Entry, timeout: int
) -> dict:
    key = (
        "https://doi.org/" + entry.doi
        if entry.doi
        else entry.openalex_id
    )
    if not key:
        return {}
    url = "https://api.openalex.org/works/" + quote(key, safe="")
    return request_json(session, url, timeout)


def add_candidate(
    candidates: list[tuple[str, str]], url: object, source: str
) -> None:
    if not isinstance(url, str) or not url.startswith(("https://", "http://")):
        return
    if all(existing != url for existing, _ in candidates):
        candidates.append((url, source))


def openalex_candidates(work: dict) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    best = work.get("best_oa_location") or {}
    add_candidate(candidates, best.get("pdf_url"), "openalex_best_oa")
    for location in work.get("locations") or []:
        location = location or {}
        if location.get("is_oa"):
            add_candidate(candidates, location.get("pdf_url"), "openalex_oa")
    return candidates


def unpaywall_candidates(
    session: requests.Session, doi: str, email: str, timeout: int
) -> list[tuple[str, str]]:
    if not email:
        return []
    url = (
        "https://api.unpaywall.org/v2/"
        + quote(doi, safe="")
        + "?email="
        + quote(email)
    )
    data = request_json(session, url, timeout)
    location = data.get("best_oa_location") or {}
    candidates: list[tuple[str, str]] = []
    add_candidate(candidates, location.get("url_for_pdf"), "unpaywall")
    return candidates


def nva_repository_candidates(
    session: requests.Session, doi: str, timeout: int
) -> list[tuple[str, str]]:
    """Return public NVA filelink API URLs for open PDF files.

    NVA file downloads are two-step: the stable public API returns a short-lived
    storage URL. Keep only the stable filelink endpoint in manifests.
    """
    url = (
        "https://api.nva.unit.no/search/resources?doi="
        + quote(doi, safe="")
        + "&size=5"
    )
    data = request_json(session, url, timeout)
    candidates: list[tuple[str, str]] = []
    for hit in data.get("hits") or []:
        publication_id = hit.get("identifier")
        if not isinstance(publication_id, str) or not publication_id:
            continue
        for artifact in hit.get("associatedArtifacts") or []:
            if not isinstance(artifact, dict):
                continue
            if artifact.get("type") != "OpenFile":
                continue
            if artifact.get("mimeType") != "application/pdf":
                continue
            file_id = artifact.get("identifier")
            if not isinstance(file_id, str) or not file_id:
                continue
            add_candidate(
                candidates,
                (
                    "https://api.nva.unit.no/publication/"
                    + quote(publication_id, safe="")
                    + "/filelink/"
                    + quote(file_id, safe="")
                ),
                "nva_repository",
            )
    return candidates


def landing_candidates(
    session: requests.Session, doi: str, timeout: int
) -> tuple[list[tuple[str, str]], str, str]:
    doi_url = "https://doi.org/" + quote(doi, safe="/")
    response = session.get(
        doi_url,
        timeout=timeout,
        allow_redirects=True,
        headers={"Accept": "text/html,application/xhtml+xml,application/pdf"},
    )
    landing_url = response.url or doi_url
    if response.status_code == 429:
        return [], landing_url, "rate_limited"
    if response.status_code in {401, 403}:
        return [], landing_url, "needs_browser_access"
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower()
    if "application/pdf" in content_type or response.content[:5] == b"%PDF-":
        return [(landing_url, "doi_pdf")], landing_url, ""
    if "html" not in content_type:
        return [], landing_url, "needs_browser"
    parser = PdfMetadataParser()
    parser.feed(response.text[:2_000_000])
    candidates: list[tuple[str, str]] = []
    for value in parser.urls:
        add_candidate(
            candidates,
            urljoin(landing_url, value),
            "publisher_metadata",
        )
    html_status = classify_html(response.content)
    return candidates, landing_url, (
        "" if candidates or html_status == "invalid_pdf" else html_status
    )


def stable_candidates(doi: str) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    if doi.startswith("10.3390/"):
        add_candidate(
            candidates,
            "https://www.mdpi.com/" + doi.removeprefix("10.3390/") + "/pdf",
            "mdpi_stable",
        )
    elif doi.startswith("10.48550/arxiv."):
        add_candidate(
            candidates,
            "https://arxiv.org/pdf/" + doi.split("arxiv.", 1)[1],
            "arxiv",
        )
    return candidates


def validate_pdf(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, "missing"
    size = path.stat().st_size
    if size < 10_000:
        return False, "too_small"
    with path.open("rb") as handle:
        if handle.read(5) != b"%PDF-":
            return False, "bad_header"
    try:
        from pypdf import PdfReader

        pages = len(PdfReader(str(path)).pages)
        if pages < 1:
            return False, "zero_pages"
        return True, f"{pages}_pages"
    except ImportError:
        return True, "header_ok"
    except Exception as exc:  # pypdf errors vary by version
        return False, "parse_error:" + type(exc).__name__


def download_candidate(
    session: requests.Session,
    url: str,
    destination: Path,
    timeout: int,
    max_bytes: int,
) -> tuple[bool, str, str]:
    temp = destination.with_suffix(".part")
    temp.unlink(missing_ok=True)
    try:
        note_prefix = ""
        if "api.nva.unit.no/publication/" in url and "/filelink/" in url:
            link_response = session.get(url, timeout=timeout)
            if link_response.status_code in {401, 403}:
                return (
                    False,
                    "needs_browser_access",
                    f"NVA filelink HTTP {link_response.status_code}",
                )
            if link_response.status_code >= 400:
                return (
                    False,
                    "request_error",
                    f"NVA filelink HTTP {link_response.status_code}",
                )
            url = str(link_response.json().get("id") or "")
            if not url.startswith(("https://", "http://")):
                return False, "request_error", "NVA filelink missing URL"
            note_prefix = "nva_open_file:"

        with session.get(
            url, timeout=timeout, stream=True, allow_redirects=True
        ) as response:
            if response.status_code == 429:
                return False, "rate_limited", "HTTP 429"
            if response.status_code in {401, 403}:
                return False, "needs_browser_access", f"HTTP {response.status_code}"
            if response.status_code >= 400:
                return False, "request_error", f"HTTP {response.status_code}"
            first = b""
            preview = bytearray()
            total = 0
            with temp.open("wb") as handle:
                for chunk in response.iter_content(128 * 1024):
                    if not chunk:
                        continue
                    if not first:
                        first = chunk[:8]
                    if len(preview) < 250_000:
                        preview.extend(chunk[: 250_000 - len(preview)])
                    handle.write(chunk)
                    total += len(chunk)
                    if total > max_bytes:
                        temp.unlink(missing_ok=True)
                        return False, "invalid_pdf", "file_too_large"
        if not first.startswith(b"%PDF-"):
            status = classify_html(bytes(preview))
            temp.unlink(missing_ok=True)
            return False, status, "response_not_pdf"
        temp.replace(destination)
        valid, note = validate_pdf(destination)
        if not valid:
            destination.unlink(missing_ok=True)
            return False, "invalid_pdf", note
        return True, "downloaded", note_prefix + note
    except requests.RequestException as exc:
        temp.unlink(missing_ok=True)
        return False, "request_error", type(exc).__name__


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def write_browser_queue(path: Path, rows: list[dict[str, str]]) -> int:
    queued = [
        row
        for row in rows
        if row["status"].startswith("needs_browser")
        or row["status"] in {"invalid_pdf", "request_error"}
    ]
    queued.sort(key=lambda row: (row["publisher"], int(row["index"])))
    write_csv(path, queued)
    return len(queued)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch legal OA/campus PDF discovery and download."
    )
    parser.add_argument("input", type=Path, help="UTF-8 DOI/citation text")
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download valid authorized candidates; default is scan-only",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("downloaded_papers")
    )
    parser.add_argument(
        "--manifest", type=Path, default=Path("download_manifest.csv")
    )
    parser.add_argument(
        "--browser-queue", type=Path, default=Path("browser_queue.csv")
    )
    parser.add_argument("--email", default="", help="Email for Unpaywall")
    parser.add_argument("--delay", type=float, default=1.5)
    parser.add_argument("--timeout", type=int, default=35)
    parser.add_argument("--max-items", type=int, default=0)
    parser.add_argument("--max-mb", type=int, default=200)
    parser.add_argument("--only-publisher", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    entries = parse_entries(
        args.input.read_text(encoding="utf-8", errors="ignore")
    )
    if not entries:
        print("No DOI found.", file=sys.stderr)
        return 2
    if args.max_items > 0:
        entries = entries[: args.max_items]
    args.output_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT.format(
                contact=args.email or "not-provided"
            ),
            "Accept": "application/pdf,text/html,application/json;q=0.9,*/*;q=0.8",
        }
    )
    rows: list[dict[str, str]] = []
    stopped_for_rate_limit = False

    for entry in entries:
        publisher = publisher_for(entry.doi)
        if (
            args.only_publisher
            and publisher.casefold() != args.only_publisher.casefold()
        ):
            continue
        status = "needs_browser"
        source = ""
        landing_url = ""
        candidate_url = ""
        notes: list[str] = []
        title = entry.title
        doi_key = safe_name(entry.doi, 70)
        filename = (
            f"{entry.index:03d}_{doi_key}_"
            + safe_name(title or entry.doi)
            + ".pdf"
        )
        destination = args.output_dir / filename
        existing = sorted(
            args.output_dir.glob(f"{entry.index:03d}_{doi_key}_*.pdf")
        )
        if existing:
            valid, note = validate_pdf(existing[0])
            if valid:
                destination = existing[0]
                status = "already_downloaded"
                notes.append(note)

        candidates: list[tuple[str, str]] = []
        work: dict = {}
        if status != "already_downloaded":
            try:
                work = openalex_work(session, entry, args.timeout)
                if work.get("title"):
                    title = str(work["title"])
                    filename = (
                        f"{entry.index:03d}_{doi_key}_{safe_name(title)}.pdf"
                    )
                    destination = args.output_dir / filename
                candidates.extend(openalex_candidates(work))
            except (requests.RequestException, ValueError) as exc:
                notes.append("OpenAlex:" + type(exc).__name__)

            if args.email:
                try:
                    for item in unpaywall_candidates(
                        session, entry.doi, args.email, args.timeout
                    ):
                        add_candidate(candidates, item[0], item[1])
                except (requests.RequestException, ValueError) as exc:
                    notes.append("Unpaywall:" + type(exc).__name__)

            for item in stable_candidates(entry.doi):
                add_candidate(candidates, item[0], item[1])

            try:
                for item in nva_repository_candidates(
                    session, entry.doi, args.timeout
                ):
                    add_candidate(candidates, item[0], item[1])
            except (requests.RequestException, ValueError) as exc:
                notes.append("NVA:" + type(exc).__name__)

            landing_status = ""
            try:
                landing_items, landing_url, landing_status = landing_candidates(
                    session, entry.doi, args.timeout
                )
                publisher = publisher_for(entry.doi, landing_url)
                for item in landing_items:
                    add_candidate(candidates, item[0], item[1])
            except requests.RequestException as exc:
                notes.append("Landing:" + type(exc).__name__)
                landing_status = "request_error"

            if not args.download:
                status = (
                    "candidate_found"
                    if candidates
                    else landing_status or "needs_browser"
                )
            else:
                status = landing_status or "needs_browser"
                for candidate_url, source in candidates:
                    ok, candidate_status, note = download_candidate(
                        session,
                        candidate_url,
                        destination,
                        args.timeout,
                        args.max_mb * 1024 * 1024,
                    )
                    notes.append(f"{source}:{note}")
                    if ok:
                        status = candidate_status
                        break
                    status = candidate_status
                    if candidate_status == "rate_limited":
                        stopped_for_rate_limit = True
                        break

        row = {
            "index": str(entry.index),
            "doi": entry.doi,
            "openalex_id": entry.openalex_id,
            "title": title,
            "publisher": publisher,
            "status": status,
            "file": str(destination) if status in {
                "downloaded", "already_downloaded"
            } else "",
            "source": source,
            "landing_url": landing_url,
            "candidate_url": candidate_url,
            "note": "; ".join(notes[-6:]),
        }
        rows.append(row)
        write_csv(args.manifest, rows)
        print(
            f"[{len(rows):03d}/{len(entries):03d}] "
            f"{publisher}: {entry.doi} -> {status}",
            flush=True,
        )
        if stopped_for_rate_limit:
            print("Rate limit detected; stopping safely.", file=sys.stderr)
            break
        time.sleep(max(0.0, args.delay))

    queue_count = write_browser_queue(args.browser_queue, rows)
    counts = Counter(row["status"] for row in rows)
    print("Summary: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    print(f"Manifest: {args.manifest.resolve()}")
    print(f"Browser queue: {args.browser_queue.resolve()} ({queue_count})")
    return 3 if stopped_for_rate_limit else 0


if __name__ == "__main__":
    raise SystemExit(main())
