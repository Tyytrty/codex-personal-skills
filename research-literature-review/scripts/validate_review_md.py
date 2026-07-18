#!/usr/bin/env python3
"""验证 Markdown 综述、GB/T 7714—2015 顺序编码引文和原文图来源。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


NUMERIC_CITE_RE = re.compile(r"(?<!\d)\[([0-9]+(?:\s*,\s*[0-9]+)*)\]")
REF_LINE_RE = re.compile(r"(?m)^\s*\[(\d+)\]\s+(.+)$")
TYPE_CODE_RE = re.compile(r"\[(M|J|C|D|R|S|P|N|G|A|CM|DS|DB|CP|EB|Z)(/OL)?\]")


def bib_count(text: str) -> int:
    return len(re.findall(r"(?m)^@[A-Za-z]+\{[^,]+,", text))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--md", type=Path, required=True)
    parser.add_argument("--bib", type=Path, required=True)
    parser.add_argument("--min-refs", type=int, default=1)
    parser.add_argument("--max-refs", type=int, default=10000)
    parser.add_argument("--min-words", type=int, default=0)
    parser.add_argument("--max-words", type=int, default=10000000)
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []
    text = args.md.read_text(encoding="utf-8")
    bib_text = args.bib.read_text(encoding="utf-8")

    if re.search(r"\[@[^\]]+\]", text):
        errors.append("仍有 [@bibkey] 占位符")
    if "\\cite{" in text:
        errors.append("仍有 LaTeX \\cite{}")

    ref_split = re.split(r"(?m)^#{1,6}\s*(参考文献|References)\s*$", text, maxsplit=1)
    if len(ref_split) < 3:
        errors.append("缺少参考文献章节")
        body, refs_text = text, ""
    else:
        body, refs_text = ref_split[0], ref_split[2]

    required = ["摘要", "引言", "讨论", "展望", "结论"]
    headings = re.findall(r"(?m)^#{1,6}\s+(.+?)\s*$", body)
    for name in required:
        if not any(name.lower() in h.lower() for h in headings):
            errors.append(f"缺少章节: {name}")

    groups = [[int(x) for x in m.group(1).split(",")] for m in NUMERIC_CITE_RE.finditer(body)]
    seen: set[int] = set()
    first_order: list[int] = []
    expected = 1
    for group in groups:
        for number in group:
            if number not in seen:
                if number != expected:
                    errors.append(f"首次被引顺序错误: 期望 [{expected}]，实际先出现 [{number}]")
                    expected = number
                seen.add(number)
                first_order.append(number)
                expected += 1

    ref_entries = [(int(n), line.strip()) for n, line in REF_LINE_RE.findall(refs_text)]
    ref_numbers = [n for n, _ in ref_entries]
    if ref_numbers != list(range(1, len(ref_numbers) + 1)):
        errors.append("参考文献编号不是 GB/T 7714 方括号形式的连续递增序号")
    if set(ref_numbers) != seen:
        errors.append("正文引用编号与参考文献表不一致")
    if re.search(r"(?m)^\s*\d+\.\s+", refs_text):
        errors.append("参考文献表使用了“1.”形式；GB/T 7714 顺序编码制应使用“[1]”")
    for number, line in ref_entries:
        if not TYPE_CODE_RE.search(line):
            errors.append(f"参考文献 [{number}] 缺少或使用了无效的文献类型/载体标识")
        if not line.endswith("."):
            errors.append(f"参考文献 [{number}] 末尾应使用句点")
        online = re.search(r"\[[A-Z]+/OL\]", line)
        if online and not re.search(r"\[\d{4}-\d{2}-\d{2}\]", line):
            warnings.append(f"在线参考文献 [{number}] 缺少 YYYY-MM-DD 引用日期")
        if online and not re.search(r"https?://|DOI:", line, re.I):
            errors.append(f"在线参考文献 [{number}] 缺少访问路径或 DOI")

    countable = re.sub(r"```.*?```", "", body, flags=re.S)
    countable = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", countable)
    countable = re.sub(r"https?://\S+", "", countable)
    word_count = len(re.findall(r"[\u4e00-\u9fff]", countable))
    word_count += len(re.findall(r"\b[A-Za-z][A-Za-z0-9_-]*\b", countable))
    if not args.min_words <= word_count <= args.max_words:
        errors.append(f"正文字数 {word_count} 不在 {args.min_words} 至 {args.max_words} 范围")

    n_bib = bib_count(bib_text)
    n_refs = len(ref_numbers)
    if not args.min_refs <= n_refs <= args.max_refs:
        errors.append(f"参考文献数 {n_refs} 不在 {args.min_refs} 至 {args.max_refs} 范围")
    if n_bib != n_refs:
        errors.append(f"BibTeX 条目数 {n_bib} 与参考文献表 {n_refs} 不一致")

    images = list(re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", body))
    for match in images:
        raw_path = match.group(1).strip().split()[0].strip("<>")
        if re.match(r"https?://", raw_path):
            errors.append(f"原文图必须下载到资产目录并使用相对路径: {raw_path}")
            continue
        image_path = (args.md.parent / raw_path).resolve()
        if not image_path.exists():
            errors.append(f"图片不存在: {raw_path}")
        caption_window = body[match.end() : match.end() + 600]
        for token in ["来源", "原文图", "DOI"]:
            if token not in caption_window:
                errors.append(f"图片 {raw_path} 的图注缺少 {token}")
        if not re.search(r"CC BY|CC0|公共领域|授权|许可", caption_window, re.I):
            errors.append(f"图片 {raw_path} 的图注缺少复用许可")
    if not images:
        warnings.append("未嵌入关键原文图；若无可合法复用图片，应在验证报告说明")

    forbidden_docx = args.md.with_suffix(".docx")
    if forbidden_docx.exists():
        errors.append(f"检测到不应生成的 Word 文件: {forbidden_docx.name}")

    result = {
        "status": "PASS" if not errors else "FAIL",
        "reference_style": "GB/T 7714—2015 顺序编码制",
        "references": n_refs,
        "word_count": word_count,
        "bib_entries": n_bib,
        "first_citation_order": first_order,
        "images": len(images),
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
