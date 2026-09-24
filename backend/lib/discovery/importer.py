"""Parse statement data the user supplies (their own data) into Transactions.

Two shapes are accepted:

1. CSV with a header row (bank "export to CSV"): delimiter ; , tab or | is detected,
   quoted fields are honoured, and columns are found by name (TR/EN):
     date         tarih, işlem tarihi, date, transaction date, booking date
     description  açıklama, işlem açıklaması, description, details, merchant, işyeri
     amount       tutar, işlem tutarı, amount
     debit        borç, debit, çıkan, harcama (money out; used instead of amount if present)
     credit       alacak, credit, giren       (money in; rows with only credit are skipped)
     currency     para birimi, döviz, currency

2. Loose lines without a header:
     <date> <sep> <description> <sep> <amount> [currency]
   date: YYYY-MM-DD, DD.MM.YYYY or DD/MM/YYYY; amount: 229,99 / 1.299,90 / 1,299.90,
   optionally signed; TRY/TL/₺, USD/$, EUR/€ before or after sets the currency.

The text is parsed in memory and discarded; nothing here is persisted or logged.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date

from lib.discovery.transactions import Transaction
from lib.provider_catalog import fold

MAX_CHARS = 500_000
MAX_LINES = 5_000

_DATE = re.compile(r"^\s*\"?(\d{4}-\d{2}-\d{2}|\d{1,2}[./]\d{1,2}[./]\d{4})")
_TAIL = re.compile(r"(?P<pre>TRY|TL|USD|EUR|₺|\$|€)?[\s;|]*(?P<num>[-+]?\d[\d.,]*)[\s;,|\"]*(?P<post>TRY|TL|USD|EUR|₺|\$|€)?[\s;,|\"]*$", re.I)
_CURRENCY = {"TRY": "TRY", "TL": "TRY", "₺": "TRY", "USD": "USD", "$": "USD", "EUR": "EUR", "€": "EUR"}
_SYMBOLS = re.compile(r"(TRY|TL|USD|EUR|₺|\$|€)", re.I)

COLUMNS = {
    "date": ("tarih", "islem tarihi", "date", "transaction date", "booking date", "posting date"),
    "description": ("aciklama", "islem aciklamasi", "description", "details", "merchant", "isyeri", "islem"),
    "amount": ("tutar", "islem tutari", "amount"),
    "debit": ("borc", "debit", "cikan", "harcama"),
    "credit": ("alacak", "credit", "giren"),
    "currency": ("para birimi", "doviz", "currency", "doviz cinsi"),
}


class ImportTooLarge(ValueError):
    pass


def _parse_date(token: str) -> date:
    token = token.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", token):
        return date.fromisoformat(token)
    parts = re.split(r"[./]", token)
    if len(parts) != 3:
        raise ValueError("unsupported date")
    day, month, year = parts
    return date(int(year), int(month), int(day))


def parse_amount(raw: str) -> float:
    s = _SYMBOLS.sub("", raw).replace(" ", "").replace(" ", "").strip().lstrip("+")
    negative = s.startswith("-") or (s.startswith("(") and s.endswith(")"))
    s = s.strip("()").lstrip("-")
    if not s:
        raise ValueError("empty amount")
    if "," in s and "." in s:
        decimal = "," if s.rfind(",") > s.rfind(".") else "."
        thousands = "." if decimal == "," else ","
        s = s.replace(thousands, "").replace(decimal, ".")
    elif "," in s:
        s = s.replace(",", ".") if re.search(r",\d{1,2}$", s) else s.replace(",", "")
    elif s.count(".") > 1 or re.search(r"\.\d{3}$", s):
        s = s.replace(".", "")
    value = float(s)
    return -value if negative else value


def _currency_of(text: str, default: str = "TRY") -> str:
    match = _SYMBOLS.search(text or "")
    return _CURRENCY.get(match.group(1).upper(), default) if match else default


def _header_columns(cells: list[str]) -> dict[str, int] | None:
    found: dict[str, int] = {}
    for index, cell in enumerate(cells):
        key = fold(cell).strip(" \"'")
        for column, names in COLUMNS.items():
            if column not in found and key in names:
                found[column] = index
    if "date" in found and "description" in found and ("amount" in found or "debit" in found):
        return found
    return None


def _sniff_delimiter(first_line: str) -> str:
    counts = {d: first_line.count(d) for d in (";", "\t", "|", ",")}
    return max(counts, key=lambda d: counts[d]) if any(counts.values()) else ","


def _parse_csv(text: str, delimiter: str, columns: dict[str, int]) -> tuple[list[Transaction], int]:
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    next(reader, None)  # header
    out: list[Transaction] = []
    skipped = 0

    for row in reader:
        if not any(cell.strip() for cell in row):
            continue

        def cell(name: str) -> str:
            index = columns.get(name)
            return row[index].strip() if index is not None and index < len(row) else ""

        try:
            when = _parse_date(cell("date"))
            raw_amount = cell("debit") or cell("amount")
            if not raw_amount:
                skipped += 1  # only a credit (money in): not a subscription payment
                continue
            amount = abs(parse_amount(raw_amount))
            currency = _currency_of(cell("currency"), _currency_of(raw_amount))
        except ValueError:
            skipped += 1
            continue
        description = cell("description")
        if not description or amount == 0:
            skipped += 1
            continue
        out.append(Transaction(date=when, description=description[:120], amount=amount, currency=currency))
    return out, skipped


def _parse_lines(lines: list[str]) -> tuple[list[Transaction], int]:
    out: list[Transaction] = []
    skipped = 0
    for line in lines:
        date_match = _DATE.match(line)
        tail = _TAIL.search(line)
        if not date_match or not tail:
            skipped += 1
            continue
        try:
            when = _parse_date(date_match.group(1))
            amount = parse_amount(tail.group("num"))
        except ValueError:
            skipped += 1
            continue
        middle = line[date_match.end():tail.start()]
        description = re.sub(r"^[\s;,\t|\"]+|[\s;,\t|\"]+$", "", middle)
        if not description or amount == 0:
            skipped += 1
            continue
        symbol = (tail.group("pre") or tail.group("post") or "TRY").upper()
        out.append(Transaction(date=when, description=description[:120], amount=abs(amount), currency=_CURRENCY.get(symbol, "TRY")))
    return out, skipped


def parse_statement(text: str) -> tuple[list[Transaction], int]:
    """Return (transactions, skipped_line_count). Raises ImportTooLarge over the limits."""
    if len(text) > MAX_CHARS:
        raise ImportTooLarge("Metin çok uzun")
    text = text.lstrip("﻿")  # Excel's UTF-8 BOM
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) > MAX_LINES:
        raise ImportTooLarge("Satır sayısı çok fazla")
    if not lines:
        return [], 0
    delimiter = _sniff_delimiter(lines[0])
    header = next(csv.reader([lines[0]], delimiter=delimiter), [])
    columns = _header_columns(header)
    if columns:
        return _parse_csv("\n".join(lines), delimiter, columns)
    return _parse_lines(lines)
