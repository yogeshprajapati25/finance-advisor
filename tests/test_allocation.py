from app.core.models import UserProfile
from app.core.allocation import suggest_allocation


def test_young_high_saver():
    profile = UserProfile(
        age=25,
        monthly_income=100000,
        monthly_expenses=40000,  # 60% savings rate
        has_emergency_fund=True,
    )
    result = suggest_allocation(profile)
    assert result.equity_pct == 80  # base 75, +10 clamped to 80
    assert result.gold_pct == 7.5
    assert "emergency fund" not in " ".join(result.reasoning).lower()


def test_older_low_saver():
    profile = UserProfile(
        age=55,
        monthly_income=100000,
        monthly_expenses=90000,  # 10% savings rate
        has_emergency_fund=True,
    )
    result = suggest_allocation(profile)
    # base = 45, -10 for low savings = 35
    assert result.equity_pct == 35


def test_no_emergency_fund_flagged():
    profile = UserProfile(
        age=30,
        monthly_income=80000,
        monthly_expenses=60000,
        has_emergency_fund=False,
    )
    result = suggest_allocation(profile)
    assert any("emergency fund" in r.lower() for r in result.reasoning)


def test_equity_clamped_at_20_minimum():
    profile = UserProfile(
        age=70,
        monthly_income=50000,
        monthly_expenses=48000,  # low savings rate
        has_emergency_fund=True,
    )
    result = suggest_allocation(profile)
    assert result.equity_pct >= 20


def test_allocation_sums_to_100():
    profile = UserProfile(
        age=40,
        monthly_income=100000,
        monthly_expenses=70000,
        has_emergency_fund=True,
    )
    result = suggest_allocation(profile)
    total = (
        result.equity_pct + result.debt_pct + result.gold_pct + result.fd_pct
    )
    assert round(total, 1) == 100.0