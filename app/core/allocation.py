"""
allocation.py
-------------
Smart allocation engine.

Flow:
  1. Overspending (savings ≤ 0)  → tell user what to cut
  2. Under-threshold savings      → tell user how much more to save
  3. Healthy savings              → show equity/debt/gold/fd split
"""

from app.core.models import UserProfile, AllocationResult

GOLD_PCT = 7.5


def _min_investment_threshold(age: int, dependents: int) -> float:
    """
    Minimum monthly savings (₹) before recommending investments.
    Increases with dependents (₹1 000 each).
    """
    if age < 30:
        base = 2_000
    elif age <= 45:
        base = 5_000
    else:
        base = 3_000
    return base + dependents * 1_000


def suggest_allocation(
    profile: UserProfile,
    savings_rate_override: float | None = None,
    category_breakdown: dict | None = None,
) -> AllocationResult:
    reasoning: list[str] = []

    # ── Compute savings ──────────────────────────────────────────────────────
    savings = profile.monthly_income - profile.monthly_expenses
    if savings_rate_override is not None:
        rate = savings_rate_override
    else:
        rate = savings / profile.monthly_income if profile.monthly_income > 0 else 0.0

    fmt_inr = lambda v: f"₹{v:,.0f}"

    # ── Case 1: Overspending ─────────────────────────────────────────────────
    if savings <= 0:
        reasoning.append(
            f"Your spending ({fmt_inr(profile.monthly_expenses)}) exceeds "
            f"your income ({fmt_inr(profile.monthly_income)}) by "
            f"{fmt_inr(abs(savings))} this month."
        )
        reasoning.append(
            "Investing isn't advisable right now. Focus on closing this gap first."
        )
        if category_breakdown:
            top = max(category_breakdown, key=category_breakdown.get)
            reasoning.append(
                f"Your biggest expense is {top} at "
                f"{fmt_inr(category_breakdown[top])}. "
                "Consider reducing discretionary spending here."
            )
        reasoning.append(
            "Tips: track daily expenses, cancel unused subscriptions, "
            "and avoid impulse purchases."
        )
        return AllocationResult(
            equity_pct=0, debt_pct=0, gold_pct=0, fd_pct=0,
            reasoning=reasoning, status="overspending",
        )

    # ── Case 2: Saving but below investment threshold ────────────────────────
    threshold = _min_investment_threshold(profile.age, profile.dependents)
    if savings < threshold:
        reasoning.append(
            f"You're saving {fmt_inr(savings)}/month — good start! "
            f"But to invest comfortably at your life stage, "
            f"you need at least {fmt_inr(threshold)}/month in savings."
        )
        gap = threshold - savings
        reasoning.append(
            f"You need {fmt_inr(gap)} more per month before investing makes sense."
        )
        if not profile.has_emergency_fund:
            reasoning.append(
                "You also don't have an emergency fund yet. "
                "Aim for 6 months of expenses in a liquid account before investing."
            )
        if category_breakdown:
            # Suggest cutting the top non-essential expense
            non_essential = {
                k: v for k, v in category_breakdown.items()
                if k.lower() not in {"rent", "emi", "loan", "utilities", "electricity"}
            }
            if non_essential:
                top = max(non_essential, key=non_essential.get)
                reasoning.append(
                    f"Your highest discretionary spend is {top} "
                    f"({fmt_inr(non_essential[top])}). "
                    "Reducing this could help you reach your savings goal faster."
                )
        reasoning.append(
            f"Savings rate: {rate:.0%}. Target at least 20-30% of your income."
        )
        return AllocationResult(
            equity_pct=0, debt_pct=0, gold_pct=0, fd_pct=0,
            reasoning=reasoning, status="below_threshold",
        )

    # ── Case 3: Healthy savings → show allocation ─────────────────────────────
    if not profile.has_emergency_fund:
        reasoning.append(
            "No emergency fund detected — put 20% of your investable surplus "
            "into a liquid fund/FD until you have 6 months of expenses covered."
        )

    # 100-age rule clamped to 20-80%
    base_equity = max(20, min(80, 100 - profile.age))
    reasoning.append(
        f"Base equity allocation: {base_equity}% (100 − age {profile.age}, clamped to 20-80%)."
    )

    # Dependents → reduce equity exposure
    dep_penalty = profile.dependents * 3
    if dep_penalty:
        reasoning.append(
            f"Reducing equity by {dep_penalty}% due to {profile.dependents} dependent(s)."
        )

    # Savings rate adjustment (±15 points)
    adj = max(-15, min(15, (rate - 0.25) * 50))
    if adj > 2:
        reasoning.append(f"Strong savings rate ({rate:.0%}) — boosting equity by {adj:.0f} pts.")
    elif adj < -2:
        reasoning.append(f"Low savings rate ({rate:.0%}) — reducing equity by {abs(adj):.0f} pts.")

    equity_pct = max(20, min(80, base_equity - dep_penalty + adj))
    remaining  = 100 - equity_pct - GOLD_PCT
    debt_pct   = remaining * 0.6
    fd_pct     = remaining * 0.4

    reasoning.append(
        f"Gold fixed at {GOLD_PCT}% for inflation hedge. "
        f"Remaining {remaining:.1f}% split: Debt {debt_pct:.1f}%, FD {fd_pct:.1f}%."
    )
    reasoning.append(
        f"Monthly investable surplus: {fmt_inr(savings)} "
        f"(savings rate: {rate:.0%})."
    )

    return AllocationResult(
        equity_pct=round(equity_pct, 1),
        debt_pct=round(debt_pct, 1),
        gold_pct=round(GOLD_PCT, 1),
        fd_pct=round(fd_pct, 1),
        reasoning=reasoning,
        status="ok",
    )
