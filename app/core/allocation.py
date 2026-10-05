from app.core.models import UserProfile, AllocationResult

GOLD_PCT = 7.5


def suggest_allocation(
    profile: UserProfile, savings_rate_override: float | None = None
) -> AllocationResult:
    reasoning: list[str] = []

    if savings_rate_override is not None:
        savings_rate = savings_rate_override
    else:
        savings_rate = 0.0
        if profile.monthly_income > 0:
            savings_rate = (
                profile.monthly_income - profile.monthly_expenses
            ) / profile.monthly_income

    # Case: overspending (expenses > income)
    if savings_rate < 0:
        reasoning.append(
            "Your expenses exceed your income this period. Investing isn't "
            "advisable right now — focus on cutting expenses, increasing "
            "income, or covering the gap with savings before allocating "
            "anything to investments."
        )
        return AllocationResult(
            equity_pct=0.0, debt_pct=0.0, gold_pct=0.0, fd_pct=0.0,
            reasoning=reasoning, status="overspending",
        )

    # Case: breakeven (income exactly covers expenses, nothing left over)
    if savings_rate == 0:
        reasoning.append(
            "You're breaking even this period — income covers expenses "
            "exactly, with nothing left over to invest yet. This isn't a "
            "deficit, but there's no surplus to allocate until your "
            "savings rate turns positive."
        )
        return AllocationResult(
            equity_pct=0.0, debt_pct=0.0, gold_pct=0.0, fd_pct=0.0,
            reasoning=reasoning, status="breakeven",
        )

    # Case: normal — positive savings rate
    if not profile.has_emergency_fund:
        reasoning.append(
            "No emergency fund detected — prioritize building 6 months of "
            "expenses in a liquid fund/FD before increasing equity exposure."
        )

    base_equity = 100 - profile.age
    base_equity = max(20, min(80, base_equity))
    reasoning.append(
        f"Base equity allocation of {base_equity}% derived from age "
        f"({profile.age}) using the '100 - age' rule, clamped to 20-80%."
    )

    adjustment = (savings_rate - 0.25) * 50
    adjustment = max(-15, min(15, adjustment))
    equity_pct = max(20, min(80, base_equity + adjustment))

    if adjustment > 2:
        reasoning.append(
            f"Savings rate of {savings_rate:.0%} is healthy — "
            f"increasing equity allocation by {adjustment:.1f} points."
        )
    elif adjustment < -2:
        reasoning.append(
            f"Savings rate of {savings_rate:.0%} is low — reducing "
            f"equity allocation by {abs(adjustment):.1f} points in "
            f"favor of safer instruments."
        )
    else:
        reasoning.append(
            f"Savings rate of {savings_rate:.0%} is moderate — no "
            f"major adjustment to base equity allocation."
        )

    remaining = 100 - equity_pct - GOLD_PCT
    debt_pct = remaining * 0.6
    fd_pct = remaining * 0.4

    reasoning.append(
        f"Gold fixed at {GOLD_PCT}% for diversification; remaining "
        f"{remaining:.1f}% split between Debt ({debt_pct:.1f}%) and "
        f"FD ({fd_pct:.1f}%)."
    )

    return AllocationResult(
        equity_pct=round(equity_pct, 1),
        debt_pct=round(debt_pct, 1),
        gold_pct=round(GOLD_PCT, 1),
        fd_pct=round(fd_pct, 1),
        reasoning=reasoning,
        status="ok",
    )