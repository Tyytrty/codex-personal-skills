#!/usr/bin/env python3
"""Pair and rename Didi invoices and trip reports by amount."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader


INVOICE_GLOB = "滴滴电子发票*.pdf"
TRIP_GLOB = "滴滴出行行程报销单*.pdf"
ILLEGAL_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')


@dataclass(frozen=True)
class DidiDocument:
    path: Path
    amount: Decimal


@dataclass(frozen=True)
class TripDocument(DidiDocument):
    start_date: str
    end_date: str
    cities: tuple[str, ...]


def read_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def decimal_amount(value: str) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"))


def parse_invoice(path: Path) -> DidiDocument:
    text = read_pdf_text(path)
    patterns = (
        r"价\s*税\s*合\s*计.*?[（(]\s*小\s*写\s*[）)].*?([0-9]+(?:\.[0-9]{1,2})?)\s*[¥￥]",
        r"[（(]\s*小\s*写\s*[）)]\s*([0-9]+(?:\.[0-9]{1,2})?)\s*[¥￥]",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return DidiDocument(path, decimal_amount(match.group(1)))
    raise ValueError(f"无法提取发票价税合计：{path.name}")


def ordered_unique(values: list[str]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        clean = value.strip()
        if clean and clean not in result:
            result.append(clean)
    return tuple(result)


def parse_trip(path: Path) -> TripDocument:
    text = read_pdf_text(path)
    date_match = re.search(
        r"行程起止日期[：:]\s*(\d{4})-(\d{2})-(\d{2})\s*至\s*"
        r"(\d{4})-(\d{2})-(\d{2})",
        text,
    )
    amount_match = re.search(r"合计\s*([0-9]+(?:\.[0-9]{1,2})?)\s*元", text)
    if not date_match:
        raise ValueError(f"无法提取行程日期：{path.name}")
    if not amount_match:
        raise ValueError(f"无法提取行程合计：{path.name}")

    table_text = text.split("备注", 1)[-1]
    city_matches = re.findall(
        r"(?<![\u4e00-\u9fff])([\u4e00-\u9fff]{2,6})\s*市(?:\s|$)",
        table_text,
    )
    cities = ordered_unique(city_matches)
    if not cities:
        raise ValueError(f"无法提取行程城市：{path.name}")

    groups = date_match.groups()
    start_date = "".join(groups[:3])
    end_date = "".join(groups[3:])
    return TripDocument(
        path=path,
        amount=decimal_amount(amount_match.group(1)),
        start_date=start_date,
        end_date=end_date,
        cities=cities,
    )


def index_unique_by_amount(
    documents: list[DidiDocument], document_type: str
) -> dict[Decimal, DidiDocument]:
    result: dict[Decimal, DidiDocument] = {}
    for document in documents:
        if document.amount in result:
            other = result[document.amount]
            raise ValueError(
                f"{document_type}存在重复金额 {document.amount:.2f}："
                f"{other.path.name}；{document.path.name}。请人工指定配对。"
            )
        result[document.amount] = document
    return result


def safe_component(value: str) -> str:
    return ILLEGAL_FILENAME_CHARS.sub("", value).strip().rstrip(".")


def build_plan(directory: Path) -> list[tuple[Path, Path]]:
    invoices = [parse_invoice(path) for path in sorted(directory.glob(INVOICE_GLOB))]
    trips = [parse_trip(path) for path in sorted(directory.glob(TRIP_GLOB))]
    if not invoices:
        raise ValueError(f"未找到 {INVOICE_GLOB}")
    if not trips:
        raise ValueError(f"未找到 {TRIP_GLOB}")

    invoice_by_amount = index_unique_by_amount(invoices, "发票")
    trip_by_amount = index_unique_by_amount(trips, "行程单")
    if invoice_by_amount.keys() != trip_by_amount.keys():
        missing_trips = sorted(invoice_by_amount.keys() - trip_by_amount.keys())
        missing_invoices = sorted(trip_by_amount.keys() - invoice_by_amount.keys())
        raise ValueError(
            "金额无法一一对应。"
            f"缺少行程单：{missing_trips or '无'}；"
            f"缺少发票：{missing_invoices or '无'}"
        )

    plan: list[tuple[Path, Path]] = []
    for amount in sorted(invoice_by_amount):
        invoice = invoice_by_amount[amount]
        trip = trip_by_amount[amount]
        assert isinstance(trip, TripDocument)
        city = safe_component("-".join(trip.cities))
        base = (
            f"{trip.start_date}至{trip.end_date}_{city}_"
            f"{{kind}}_{amount:.2f}元.pdf"
        )
        plan.append((invoice.path, directory / base.format(kind="滴滴发票")))
        plan.append((trip.path, directory / base.format(kind="滴滴行程单")))

    sources = {source.resolve() for source, _ in plan}
    targets = [target.resolve() for _, target in plan]
    if len(targets) != len(set(targets)):
        raise ValueError("重命名计划产生重复目标文件名。")
    for source, target in plan:
        if target.exists() and target.resolve() not in sources:
            raise FileExistsError(f"目标文件已存在：{target.name}")
        if source.parent.resolve() != directory.resolve():
            raise ValueError(f"源文件不在目标目录内：{source}")
        if target.parent.resolve() != directory.resolve():
            raise ValueError(f"目标文件逃逸目录：{target}")
    return plan


def execute_plan(plan: list[tuple[Path, Path]], dry_run: bool) -> None:
    for source, target in plan:
        print(f"{'[DRY-RUN] ' if dry_run else ''}{source.name} -> {target.name}")
    if dry_run:
        return

    temporary_moves: list[tuple[Path, Path, Path]] = []
    for index, (source, target) in enumerate(plan):
        temporary = source.with_name(f".didi-rename-{index:03d}.tmp")
        if temporary.exists():
            raise FileExistsError(f"临时文件已存在：{temporary.name}")
        source.rename(temporary)
        temporary_moves.append((temporary, source, target))

    try:
        for temporary, _, target in temporary_moves:
            temporary.rename(target)
    except Exception:
        for temporary, source, target in reversed(temporary_moves):
            if temporary.exists():
                temporary.rename(source)
            elif target.exists() and not source.exists():
                target.rename(source)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="按金额配对滴滴发票与行程单，并按日期区间和城市成对重命名。"
    )
    parser.add_argument("directory", type=Path, help="包含滴滴 PDF 的目录")
    parser.add_argument(
        "--dry-run", action="store_true", help="仅显示重命名计划，不修改文件"
    )
    args = parser.parse_args()

    directory = args.directory.expanduser().resolve()
    if not directory.is_dir():
        parser.error(f"目录不存在：{directory}")

    try:
        plan = build_plan(directory)
        execute_plan(plan, args.dry_run)
    except Exception as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
