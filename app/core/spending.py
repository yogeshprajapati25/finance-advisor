from app.core.models import Transaction, SpendingSummary


def calculate_spending_summary(
    transactions: list[Transaction], monthly_income: float
) -> SpendingSummary:
    category_totals: dict[str, float] = {}
    total_expenses = 0.0

    for txn in transactions:
        category_totals[txn.category] = (
            category_totals.get(txn.category, 0.0) + txn.amount
        )
        total_expenses += txn.amount

    savings_rate = 0.0
    if monthly_income > 0:
        savings_rate = (monthly_income - total_expenses) / monthly_income

    return SpendingSummary(
        total_expenses=round(total_expenses, 2),
        category_breakdown={
            k: round(v, 2) for k, v in category_totals.items()
        },
        savings_rate=round(savings_rate, 4),
    )