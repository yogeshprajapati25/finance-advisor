from fastapi import FastAPI

from app.core.models import UserProfile, AllocationResult
from app.core.allocation import suggest_allocation

app = FastAPI(title="Personal Finance Advisor")


@app.post("/recommend", response_model=AllocationResult)
def recommend(profile: UserProfile) -> AllocationResult:
    return suggest_allocation(profile)


@app.get("/health")
def health():
    return {"status": "ok"}