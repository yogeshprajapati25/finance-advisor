from fastapi import FastAPI
from pydantic import BaseModel

from app.core.models import UserProfile, AllocationResult,Transaction, SpendingSummary
from app.core.allocation import suggest_allocation
from app.core.spending import calculate_spending_summary

app = FastAPI(title="Personal Finance Advisor")


@app.post("/recommend", response_model=AllocationResult)
def recommend(profile: UserProfile) -> AllocationResult:
    return suggest_allocation(profile)


@app.get("/health")
def health():
    return {"status": "ok"}


class RecommendFromTransactionsRequest(BaseModel):
    profile: UserProfile
    transactions: list[Transaction]


@app.post("/recommend-from-transactions", response_model=AllocationResult)
def recommend_from_transactions(
    request: RecommendFromTransactionsRequest,
) -> AllocationResult:
    summary = calculate_spending_summary(
        request.transactions, request.profile.monthly_income
    )
    return suggest_allocation(
        request.profile, savings_rate_override=summary.savings_rate
    )