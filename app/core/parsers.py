"""
parsers.py
----------
Converts uploaded files (CSV, Excel, PDF, Image) into a
normalised list of transaction dicts:
    [{"category": str, "amount": float, "description": str}, ...]

Each parser is independent — add new ones without touching the rest.
"""

import io
import json
import re
from pathlib import Path
from typing import Any


# ── helpers ──────────────────────────────────────────────────────────────────

def _normalise_rows(rows: list[dict]) -> list[dict]:
    """
    Accept rows with arbitrary column names and map them to
    {category, amount, description}.  Best-effort — skips rows
    where no numeric amount can be found.
    """
    result = []
    for row in rows:
        # flatten keys to lowercase
        row = {k.lower().strip(): v for k, v in row.items()}

        # find amount — accept 'amount', 'price', 'value', 'debit', 'credit'
        amount = None
        for key in ("amount", "price", "value", "debit", "credit"):
            if key in row:
                try:
                    amount = float(str(row[key]).replace(",", "").strip())
                    break
                except (ValueError, TypeError):
                    continue
        if amount is None:
            continue

        category    = str(row.get("category", row.get("type", "Other"))).strip() or "Other"
        description = str(row.get("description", row.get("note", row.get("narration", "")))).strip()

        result.append({"category": category, "amount": amount, "description": description})
    return result


# ── parsers ──────────────────────────────────────────────────────────────────

def parse_csv(content: bytes) -> list[dict]:
    import csv
    text   = content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    return _normalise_rows(list(reader))


def parse_excel(content: bytes) -> list[dict]:
    import openpyxl
    wb   = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    ws   = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(c).lower().strip() if c else f"col{i}" for i, c in enumerate(rows[0])]
    dicts   = [dict(zip(headers, row)) for row in rows[1:] if any(row)]
    return _normalise_rows(dicts)


def parse_pdf(content: bytes) -> list[dict]:
    import pdfplumber
    rows = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            for table in (page.extract_tables() or []):
                if not table:
                    continue
                header = [str(c).lower().strip() if c else f"col{i}"
                          for i, c in enumerate(table[0])]
                for row in table[1:]:
                    if any(row):
                        rows.append(dict(zip(header, row)))
    return _normalise_rows(rows)


def parse_image(content: bytes) -> list[dict]:
    """
    OCR the image with Tesseract, then extract lines that look like
    '<label>  <number>' — works for handwritten ledgers and bank screenshots.
    """
    from PIL import Image, ImageFilter
    import pytesseract

    img = Image.open(io.BytesIO(content)).convert("L")          # greyscale
    img = img.filter(ImageFilter.SHARPEN)                        # sharpen edges

    raw  = pytesseract.image_to_string(img)
    rows = []
    # match lines like: "Groceries  1200" or "salary - 50000"
    pattern = re.compile(r"^(.+?)\s*[-:]?\s*(\d[\d,\.]+)\s*$")
    for line in raw.splitlines():
        m = pattern.match(line.strip())
        if m:
            label  = m.group(1).strip()
            amount = float(m.group(2).replace(",", ""))
            rows.append({"category": label, "amount": amount, "description": ""})
    return rows


# ── dispatcher ────────────────────────────────────────────────────────────────

PARSERS = {
    ".csv":  parse_csv,
    ".xlsx": parse_excel,
    ".xls":  parse_excel,
    ".pdf":  parse_pdf,
    ".png":  parse_image,
    ".jpg":  parse_image,
    ".jpeg": parse_image,
    ".webp": parse_image,
}


def parse_file(filename: str, content: bytes) -> list[dict]:
    """
    Entry point — pick the right parser from the file extension.
    Returns normalised transaction list or raises ValueError.
    """
    ext = Path(filename).suffix.lower()
    parser = PARSERS.get(ext)
    if not parser:
        raise ValueError(f"Unsupported file type: {ext}")
    return parser(content)


def save_to_user_folder(user_id: int, transactions: list[dict], base: Path) -> Path:
    """
    Merge new transactions with any existing ones and persist as JSON.
    Returns the path of the saved file.
    """
    folder = base / f"user_{user_id}"
    folder.mkdir(parents=True, exist_ok=True)

    txn_file = folder / "transactions.json"
    existing: list[dict[str, Any]] = []
    if txn_file.exists():
        existing = json.loads(txn_file.read_text())

    existing.extend(transactions)
    txn_file.write_text(json.dumps(existing, indent=2))
    return txn_file
