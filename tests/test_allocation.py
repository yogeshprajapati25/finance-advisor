from app.core.models import UserProfile
from app.core.allocation import suggest_allocation


def test_young_high_saver():
    profile = UserProfile(
        age=25, monthly_income=100000, monthly_expenses=40000,
        has_emergency_fund=True,
    )
    result = suggest_allocation(profile)
    assert result.status == "ok"
    assert result.equity_pct == 80


def test_older_moderate_saver():
    profile = UserProfile(
        age=55, monthly_income=100000, monthly_expenses=90000,
        has_emergency_fund=True,
    )
    result = suggest_allocation(profile)
    assert result.status == "ok"
    assert result.equity_pct == 37.5


def test_overspending_returns_zero_allocation():
    profile = UserProfile(
        age=30, monthly_income=50000, monthly_expenses=70000,
        has_emergency_fund=True,
    )
    result = suggest_allocation(profile, savings_rate_override=-0.4)
    assert result.status == "overspending"
    assert result.equity_pct == 0
    assert result.debt_pct == 0
    assert result.gold_pct == 0
    assert result.fd_pct == 0


def test_breakeven_returns_zero_allocation():
    profile = UserProfile(
        age=30, monthly_income=50000, monthly_expenses=50000,
        has_emergency_fund=True,
    )
    result = suggest_allocation(profile, savings_rate_override=0.0)
    assert result.status == "breakeven"
    assert result.equity_pct == 0


def test_no_emergency_fund_flagged():
    profile = UserProfile(
        age=30, monthly_income=80000, monthly_expenses=60000,
        has_emergency_fund=False,
    )
    result = suggest_allocation(profile)
    assert any("emergency fund" in r.lower() for r in result.reasoning)


def test_equity_clamped_at_20_minimum():
    profile = UserProfile(
        age=70, monthly_income=50000, monthly_expenses=48000,
        has_emergency_fund=True,
    )
    result = suggest_allocation(profile)
    assert result.equity_pct >= 20


def test_allocation_sums_to_100_when_ok():
    profile = UserProfile(
        age=40, monthly_income=100000, monthly_expenses=70000,
        has_emergency_fund=True,
    )
    result = suggest_allocation(profile)
    total = result.equity_pct + result.debt_pct + result.gold_pct + result.fd_pct
    assert round(total, 1) == 100.0


def test_different_savings_rates_give_different_results():
    profile = UserProfile(
        age=30, monthly_income=100000, monthly_expenses=0,
        has_emergency_fund=True,
    )
    r1 = suggest_allocation(profile, savings_rate_override=0.2)
    r2 = suggest_allocation(profile, savings_rate_override=0.35)
    assert r1.equity_pct != r2.equity_pct