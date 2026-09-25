from app.core.models import Transaction
from app.core.spending import calculate_spending_summary


def test_category_breakdown():
    transactions = [
        Transaction(category="Food", amount=5000),
        Transaction(category="Food", amount=2000),
        Transaction(category="Rent", amount=20000),
    ]
    summary = calculate_spending_summary(transactions, monthly_income=50000)

    assert summary.category_breakdown["Food"] == 7000
    assert summary.category_breakdown["Rent"] == 20000
    assert summary.total_expenses == 27000


def test_savings_rate_calculation():
    transactions = [Transaction(category="Rent", amount=30000)]
    summary = calculate_spending_summary(transactions, monthly_income=100000)

    assert summary.savings_rate == 0.7  # (100000-30000)/100000


def test_no_transactions():
    summary = calculate_spending_summary([], monthly_income=50000)

    assert summary.total_expenses == 0
    assert summary.savings_rate == 1.0
    assert summary.category_breakdown == {}


def test_zero_income_no_crash():
    transactions = [Transaction(category="Food", amount=1000)]
    summary = calculate_spending_summary(transactions, monthly_income=0)

    assert summary.savings_rate == 0.0