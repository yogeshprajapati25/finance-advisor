from fastapi import FastAPI
from pydantic import BaseModel

from app.core.models import UserProfile, AllocationResult,Transaction, SpendingSummary
from app.core.allocation import suggest_allocation
from app.core.spending import calculate_spending_summary
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status

from app.db.database import get_db
from app.db.models import UserDB
from app.core.models import UserSignup, UserLogin, Token
from app.core.security import hash_password, verify_password, create_access_token


from app.db.database import engine, Base
from app.db import models as db_models

app = FastAPI(title="Personal Finance Advisor")

Base.metadata.create_all(bind=engine)

@app.post("/signup", response_model=Token)
def signup(user: UserSignup, db: Session = Depends(get_db)):
    existing = db.query(UserDB).filter(UserDB.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = UserDB(
        email=user.email,
        hashed_password=hash_password(user.password),
        age=user.age,
        dependents=user.dependents,
        has_emergency_fund=user.has_emergency_fund,
        monthly_income=user.monthly_income,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token({"sub": str(new_user.id)})
    return Token(access_token=token)


@app.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token)

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