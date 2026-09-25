from pydantic import BaseModel


class UserProfile(BaseModel):
    age: int
    monthly_income: float
    monthly_expenses: float
    dependents: int = 0
    has_emergency_fund: bool = False


class AllocationResult(BaseModel):
    equity_pct: float
    debt_pct: float
    gold_pct: float
    fd_pct: float
    reasoning: list[str]