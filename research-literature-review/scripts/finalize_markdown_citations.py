#!/usr/bin/env python3
"""按正文首次出现顺序编号，并按 GB/T 7714—2015 生成参考文献表。"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path


PLACEHOLDER_RE = re.compile(
    r"\[((?:@[A-Za-z0-9_.:/-]+)(?:\s*[;,]\s*@[A-Za-z0-9_.:/-]+)*)\]"
)

TYPE_CODES = {
    "article": "J",
    "book": "M",
    "inbook": "M",
    "incollection": "M",
    "inproceedings": "C",
    "conference": "C",
    "proceedings": "C",
    "phdthesis": "D",
    "mastersthesis": "D",
    "thesis": "D",
    "techreport": "R",
    "report": "R",
    "standard": "S",
    "patent": "P",
    "newspaper": "N",
    "database": "DB",
    "dataset": "DS",
    "software": "CP",
    "online": "EB",
    "misc": "Z",
}


def split_entries(text: str) -> list[tuple[str, str, str]]:
    entries: list[tuple[str, str, str]] = []
    pos = 0
    while True:
        match = re.search(r"@([A-Za-z]+)\s*\{", text[pos:])
        if not match:
            break
        entry_type = match.group(1).lower()
        brace = pos + match.end() - 1
        comma = text.find(",", brace)
        if comma < 0:
            break
        key = text[brace + 1 : comma].strip()
        depth = 1
        i = brace
        while depth and i + 1 < len(text):
            i += 1
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
        if depth:
            raise ValueError(f"BibTeX 条目花括号不闭合: {key}")
        entries.append((entry_type, key, text[comma + 1 : i]))
        pos = i + 1
    return entries


def parse_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    i = 0
    while i < len(body):
        match = re.search(r"([A-Za-z][A-Za-z0-9_-]*)\s*=\s*", body[i:])
        if not match:
            break
        name = match.group(1).lower()
        i += match.end()
        if i >= len(body):
            break
        opener = body[i]
        if opener == "{":
            depth, j = 1, i + 1
            while depth and j < len(body):
                if body[j] == "{":
                    depth += 1
                elif body[j] == "}":
                    depth -= 1
                j += 1
            value = body[i + 1 : j - 1]
            i = j
        elif opener == '"':
            j = i + 1
            while j < len(body):
                if body[j] == '"' and body[j - 1] != "\\":
                    break
                j += 1
            value = body[i + 1 : j]
            i = j + 1
        else:
            j = body.find(",", i)
            j = len(body) if j < 0 else j
            value = body[i:j]
            i = j
        fields[name] = clean_tex(value)
    return fields


def clean_tex(value: str) -> str:
    value = html.unescape(value)
    value = value.replace("\\&", "&").replace("\\_", "_").replace("~", " ")
    value = re.sub(r"\\[A-Za-z]+\s*\{([^{}]*)\}", r"\1", value)
    value = value.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", value).strip()


def load_bib(path: Path) -> dict[str, dict[str, str]]:
    parsed: dict[str, dict[str, str]] = {}
    for entry_type, key, body in split_entries(path.read_text(encoding="utf-8")):
        if key in parsed:
            raise ValueError(f"重复 BibTeX key: {key}")
        fields = parse_fields(body)
        fields["_entry_type"] = entry_type
        parsed[key] = fields
    if not parsed:
        raise ValueError("未解析到 BibTeX 条目")
    return parsed


def has_cjk(text: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", text))


def format_authors(raw: str) -> str:
    if not raw:
        return "佚名"
    authors = [re.sub(r"\s+", " ", item).strip() for item in re.split(r"\s+and\s+", raw) if item.strip()]
    shown = authors[:3]
    rendered = ", ".join(shown)
    if len(authors) > 3:
        rendered += ", 等" if has_cjk(raw) else ", et al."
    return rendered


def normalize_pages(value: str) -> str:
    return re.sub(r"\s*--?\s*", "-", value.strip())


def document_code(fields: dict[str, str]) -> str:
    explicit = fields.get("typecode") or fields.get("gbtype")
    base = explicit.upper() if explicit else TYPE_CODES.get(fields.get("_entry_type", "misc"), "Z")
    if "/" in base:
        return base
    is_online = bool(fields.get("url") or fields.get("urldate"))
    return f"{base}/OL" if is_online else base


def format_reference(number: int, fields: dict[str, str]) -> str:
    entry_type = fields.get("_entry_type", "misc")
    authors = format_authors(fields.get("author") or fields.get("editor", ""))
    title = fields.get("title", "题名缺失")
    code = document_code(fields)
    year = fields.get("year", "")
    pages = normalize_pages(fields.get("pages", ""))
    venue = fields.get("journal", "")
    volume = fields.get("volume", "")
    issue = fields.get("number", "")
    publisher = fields.get("publisher", "")
    address = fields.get("address") or fields.get("location", "")
    edition = fields.get("edition", "")
    school = fields.get("school") or fields.get("institution", "")
    booktitle = fields.get("booktitle", "")
    number_value = fields.get("patentnumber") or fields.get("number", "")

    if entry_type == "article":
        source = ", ".join(item for item in (venue, year) if item)
        if volume:
            source += (", " if source else "") + volume + (f"({issue})" if issue else "")
        elif issue:
            source += (", " if source else "") + f"({issue})"
        if pages:
            source += f": {pages}"
        core = f"{authors}. {title}[{code}]. {source}"
    elif entry_type in {"inbook", "incollection", "inproceedings", "conference"}:
        host = booktitle or publisher
        publication = ": ".join(item for item in (address, publisher) if item)
        if year:
            publication += (", " if publication else "") + year
        if pages:
            publication += f": {pages}"
        core = f"{authors}. {title}[{code}]//{host}. {publication}"
    elif entry_type in {"phdthesis", "mastersthesis", "thesis"}:
        publication = ": ".join(item for item in (address, school) if item)
        if year:
            publication += (", " if publication else "") + year
        if pages:
            publication += f": {pages}"
        core = f"{authors}. {title}[{code}]. {publication}"
    elif entry_type == "patent":
        patent_title = title + (f": {number_value}" if number_value else "")
        date = fields.get("date") or year
        core = f"{authors}. {patent_title}[{code}]. {date}"
    elif entry_type in {"book", "proceedings", "techreport", "report", "standard"}:
        publication = ": ".join(item for item in (address, publisher or school) if item)
        if year:
            publication += (", " if publication else "") + year
        if pages:
            publication += f": {pages}"
        edition_text = f". {edition}" if edition else ""
        core = f"{authors}. {title}[{code}]{edition_text}. {publication}"
    else:
        publication = ": ".join(item for item in (address, publisher or school) if item)
        if year:
            publication += (", " if publication else "") + year
        core = f"{authors}. {title}[{code}]. {publication}"

    url = fields.get("url", "")
    urldate = fields.get("urldate") or fields.get("accessdate")
    doi = re.sub(
        r"^https?://(?:dx\.)?doi\.org/", "", fields.get("doi", ""), flags=re.I
    )
    core = core.rstrip(". ")
    if urldate:
        core += f"[{urldate}]"
    if url:
        core += f". {url}"
    if doi:
        core += f". DOI:{doi}"
    core = re.sub(r"\s+", " ", core).strip().rstrip(".") + "."
    core = core.replace("et al..", "et al.")
    return f"[{number}] {core}"


def strip_reference_section(text: str) -> str:
    return re.split(r"(?m)^#{1,6}\s*(参考文献|References)\s*$", text, maxsplit=1)[0].rstrip()


def finalize(text: str, bib: dict[str, dict[str, str]]) -> tuple[str, list[str]]:
    text = strip_reference_section(text)
    order: list[str] = []
    numbers: dict[str, int] = {}

    def replace(match: re.Match[str]) -> str:
        keys = re.findall(r"@([A-Za-z0-9_.:/-]+)", match.group(1))
        values: list[int] = []
        for key in keys:
            if key not in bib:
                raise ValueError(f"正文引用 key 不在 BibTeX 中: {key}")
            if key not in numbers:
                numbers[key] = len(order) + 1
                order.append(key)
            values.append(numbers[key])
        return "[" + ", ".join(str(v) for v in values) + "]"

    rendered = PLACEHOLDER_RE.sub(replace, text)
    leftovers = re.findall(r"\[@[^\]]+\]", rendered)
    if leftovers:
        raise ValueError(f"存在无法解析的引用占位符: {leftovers[:3]}")
    uncited = [key for key in bib if key not in numbers]
    if uncited:
        raise ValueError("BibTeX 中存在未被正文引用的条目: " + ", ".join(uncited[:20]))

    refs = [format_reference(i, bib[key]) for i, key in enumerate(order, 1)]
    rendered += "\n\n## 参考文献\n\n" + "\n\n".join(refs) + "\n"
    return rendered, order


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--bib", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rendered, order = finalize(args.input.read_text(encoding="utf-8"), load_bib(args.bib))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"GB/T 7714—2015 引用定序完成: {len(order)} 篇 -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
