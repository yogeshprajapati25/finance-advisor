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

class Transaction(BaseModel):
    category: str
    amount: float
    description: str = ""


class SpendingSummary(BaseModel):
    total_expenses: float
    category_breakdown: dict[str, float]
    savings_rate: float


class UserSignup(BaseModel):
    email: str
    password: str
    age: int
    dependents: int = 0
    has_emergency_fund: bool = False
    monthly_income: float = 0.0


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"