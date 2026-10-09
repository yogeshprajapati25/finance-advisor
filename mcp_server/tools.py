"""
tools.py
--------
Pure functions that read from input_data/user_{id}/.
No MCP dependency here — easy to test independently.
"""

import json
from pathlib import Path

BASE = Path("input_data")


def _txn_file(user_id: int) -> Path:
    return BASE / f"user_{user_id}" / "transactions.json"


def _inc_file(user_id: int) -> Path:
    return BASE / f"user_{user_id}" / "income.json"


def get_transactions(user_id: int) -> list[dict]:
    """Return all transactions for a user from their local JSON file."""
    f = _txn_file(user_id)
    if not f.exists():
        return []
    return json.loads(f.read_text())


def get_income(user_id: int) -> list[dict]:
    """Return all income entries for a user from their local JSON file."""
    f = _inc_file(user_id)
    if not f.exists():
        return []
    return json.loads(f.read_text())


def get_summary(user_id: int) -> dict:
    """
    Return a financial summary for the user:
        total_income, total_spending, balance, transaction_count
    """
    transactions = get_transactions(user_id)
    income       = get_income(user_id)

    total_income   = sum(i.get("amount", 0) for i in income)
    total_spending = sum(t.get("amount", 0) for t in transactions)

    return {
        "user_id":           user_id,
        "total_income":      round(total_income, 2),
        "total_spending":    round(total_spending, 2),
        "balance":           round(total_income - total_spending, 2),
        "transaction_count": len(transactions),
    }
