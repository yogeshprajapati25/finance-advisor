"""
parsers.py
----------
Parses uploaded files into two normalised lists:
    income:       [{"name": str, "amount": float}, ...]
    transactions: [{"category": str, "amount": float, "description": str}, ...]

Supported formats: CSV, Excel, PDF, Image (OCR).
Images are also saved as a .csv file in the user folder for transparency.
"""

import csv
import io
import json
import re
from pathlib import Path
from typing import Any

# Keywords that indicate a row is INCOME, not an expense.
INCOME_KEYWORDS = {
    "salary", "income", "earning", "earnings", "credit", "revenue",
    "freelance", "bonus", "interest", "dividend", "rent received",
    "business income", "wages", "pension", "stipend",
}


def _is_income(category: str) -> bool:
    cat = category.lower().strip()
    return any(kw in cat for kw in INCOME_KEYWORDS)


def _normalise_rows(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Takes raw dicts with arbitrary column names.
    Returns (income_list, expense_list) — both normalised.
    Skips rows where no numeric amount is found.
    """
    income, expenses = [], []

    for row in rows:
        row = {k.lower().strip(): str(v).strip() for k, v in row.items() if v is not None}

        # Find amount
        amount = None
        for key in ("amount", "price", "value", "debit", "credit", "earning", "expense"):
            if key in row:
                try:
                    amount = float(str(row[key]).replace(",", "").replace("₹", "").strip())
                    if amount > 0:
                        break
                except (ValueError, TypeError):
                    continue
        if amount is None or amount <= 0:
            continue

        category    = row.get("category", row.get("type", row.get("particulars", "Other"))).strip() or "Other"
        description = row.get("description", row.get("note", row.get("narration", ""))).strip()

        if _is_income(category):
            income.append({"name": category, "amount": amount})
        else:
            expenses.append({"category": category, "amount": amount, "description": description})

    return income, expenses


# ── Individual parsers ────────────────────────────────────────────────────────

def parse_csv(content: bytes) -> tuple[list[dict], list[dict]]:
    text   = content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    return _normalise_rows(list(reader))


def parse_excel(content: bytes) -> tuple[list[dict], list[dict]]:
    import openpyxl
    wb      = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    ws      = wb.active
    rows    = list(ws.iter_rows(values_only=True))
    if not rows:
        return [], []
    headers = [str(c).lower().strip() if c else f"col{i}" for i, c in enumerate(rows[0])]
    dicts   = [dict(zip(headers, row)) for row in rows[1:] if any(r is not None for r in row)]
    return _normalise_rows(dicts)


def parse_pdf(content: bytes) -> tuple[list[dict], list[dict]]:
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
                        rows.append(dict(zip(header, [str(v) if v else "" for v in row])))
    return _normalise_rows(rows)


def parse_image(content: bytes) -> tuple[list[dict], list[dict]]:
    """
    OCR → extract 'Label  Amount' lines → split into income/expense.
    """
    from PIL import Image, ImageFilter
    import pytesseract

    img = Image.open(io.BytesIO(content)).convert("L")
    img = img.filter(ImageFilter.SHARPEN)
    raw = pytesseract.image_to_string(img)

    rows = []
    pattern = re.compile(r"^(.+?)\s*[-:=]?\s*(\d[\d,\.]*)\s*$")
    for line in raw.splitlines():
        m = pattern.match(line.strip())
        if m:
            label  = m.group(1).strip()
            try:
                amount = float(m.group(2).replace(",", ""))
            except ValueError:
                continue
            if amount > 0:
                rows.append({"category": label, "amount": amount, "description": ""})

    return _normalise_rows(rows)


# ── Dispatcher ────────────────────────────────────────────────────────────────

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


def parse_file(filename: str, content: bytes) -> tuple[list[dict], list[dict]]:
    """
    Returns (income_list, expense_list).
    Raises ValueError for unsupported extensions.
    """
    ext    = Path(filename).suffix.lower()
    parser = PARSERS.get(ext)
    if not parser:
        raise ValueError(f"Unsupported file type: {ext}")
    return parser(content)


# ── Save to user folder ───────────────────────────────────────────────────────

def _rows_to_csv_bytes(rows: list[dict]) -> bytes:
    """Serialise a list of dicts to CSV bytes."""
    if not rows:
        return b""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def save_to_user_folder(
    user_id: int,
    filename: str,
    income: list[dict],
    expenses: list[dict],
    raw_content: bytes,
    base: Path,
) -> dict:
    """
    Saves:
      - original file (or .csv for images)            → user folder
      - merges income into income.json
      - merges expenses into transactions.json
    Returns a summary dict with counts and the saved filename.
    """
    folder = base / f"user_{user_id}"
    folder.mkdir(parents=True, exist_ok=True)

    # For images: save OCR result as CSV instead of the raw image.
    ext = Path(filename).suffix.lower()
    if ext in {".png", ".jpg", ".jpeg", ".webp"}:
        saved_name = Path(filename).stem + "_ocr.csv"
        all_rows   = [{"category": r["name"], "amount": r["amount"], "description": ""} for r in income]
        all_rows  += expenses
        (folder / saved_name).write_bytes(_rows_to_csv_bytes(all_rows))
    else:
        saved_name = filename
        (folder / saved_name).write_bytes(raw_content)

    # ── Merge income.json ──
    inc_file = folder / "income.json"
    existing_inc: list[dict[str, Any]] = json.loads(inc_file.read_text()) if inc_file.exists() else []
    existing_inc.extend(income)
    inc_file.write_text(json.dumps(existing_inc, indent=2))

    # ── Merge transactions.json ──
    txn_file = folder / "transactions.json"
    existing_txn: list[dict[str, Any]] = json.loads(txn_file.read_text()) if txn_file.exists() else []
    existing_txn.extend(expenses)
    txn_file.write_text(json.dumps(existing_txn, indent=2))

    return {
        "saved_filename": saved_name,
        "income_count":   len(income),
        "expense_count":  len(expenses),
    }


def list_user_files(user_id: int, base: Path) -> list[str]:
    """Return list of uploaded filenames for a user (excludes .json)."""
    folder = base / f"user_{user_id}"
    if not folder.exists():
        return []
    return [f.name for f in sorted(folder.iterdir()) if f.suffix != ".json"]


def delete_user_file(user_id: int, filename: str, base: Path) -> bool:
    """
    Delete an uploaded file and rebuild income.json + transactions.json
    from the remaining files. Returns True if file existed and was deleted.
    """
    folder = base / f"user_{user_id}"
    target = folder / filename
    if not target.exists():
        return False

    target.unlink()

    # Rebuild JSON stores from whatever files remain.
    all_income, all_expenses = [], []
    for f in folder.iterdir():
        if f.suffix == ".json":
            continue
        try:
            inc, exp = parse_file(f.name, f.read_bytes())
            all_income.extend(inc)
            all_expenses.extend(exp)
        except Exception:
            continue

    (folder / "income.json").write_text(json.dumps(all_income, indent=2))
    (folder / "transactions.json").write_text(json.dumps(all_expenses, indent=2))
    return True
