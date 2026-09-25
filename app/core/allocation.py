from app.core.models import UserProfile, AllocationResult

GOLD_PCT = 7.5  # fixed, within the 5-10% band


def suggest_allocation(profile: UserProfile) -> AllocationResult:
    reasoning: list[str] = []

    # 1. Emergency fund check
    if not profile.has_emergency_fund:
        reasoning.append(
            "No emergency fund detected — prioritize building 6 months of "
            "expenses in a liquid fund/FD before increasing equity exposure."
        )

    # 2. Base equity % from age, clamped 20-80
    base_equity = 100 - profile.age
    base_equity = max(20, min(80, base_equity))
    reasoning.append(
        f"Base equity allocation of {base_equity}% derived from age "
        f"({profile.age}) using the '100 - age' rule, clamped to 20-80%."
    )

    # 3. Adjust by savings rate
    savings_rate = 0.0
    if profile.monthly_income > 0:
        savings_rate = (
            profile.monthly_income - profile.monthly_expenses
        ) / profile.monthly_income

    equity_pct = base_equity
    if savings_rate >= 0.4:
        equity_pct += 10
        reasoning.append(
            f"High savings rate ({savings_rate:.0%}) — increasing equity "
            f"allocation by 10% to capture higher long-term growth."
        )
    elif savings_rate < 0.15:
        equity_pct -= 10
        reasoning.append(
            f"Low savings rate ({savings_rate:.0%}) — reducing equity "
            f"allocation by 10% in favor of safer, more liquid instruments."
        )
    else:
        reasoning.append(
            f"Moderate savings rate ({savings_rate:.0%}) — no adjustment "
            f"to base equity allocation."
        )

    equity_pct = max(20, min(80, equity_pct))

    # 4. Gold fixed, remainder split between debt and FD
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
    )