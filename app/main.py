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

from app.core.security import get_current_user
from app.db.models import TransactionDB
from app.core.models import Transaction as TransactionSchema


from app.db.database import engine, Base
from app.db import models as db_models

app = FastAPI(title="Personal Finance Advisor")

from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="app/static"), name="static")

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

@app.post("/transactions")
def add_transaction(
    txn: TransactionSchema,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    new_txn = TransactionDB(
        category=txn.category,
        amount=txn.amount,
        description=txn.description,
        user_id=current_user.id,
    )
    db.add(new_txn)
    db.commit()
    db.refresh(new_txn)
    return {"id": new_txn.id, "message": "Transaction added"}


@app.get("/transactions")
def get_transactions(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    txns = (
        db.query(TransactionDB)
        .filter(TransactionDB.user_id == current_user.id)
        .all()
    )
    return [
        {
            "id": t.id,
            "category": t.category,
            "amount": t.amount,
            "description": t.description,
        }
        for t in txns
    ]


@app.post("/recommend", response_model=AllocationResult)
def recommend(profile: UserProfile) -> AllocationResult:
    return suggest_allocation(profile)

@app.get("/recommend", response_model=AllocationResult)
def recommend_for_user(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    txns = (
        db.query(TransactionDB)
        .filter(TransactionDB.user_id == current_user.id)
        .all()
    )
    txn_schemas = [
        TransactionSchema(category=t.category, amount=t.amount, description=t.description)
        for t in txns
    ]
    summary = calculate_spending_summary(txn_schemas, current_user.monthly_income)

    profile = UserProfile(
        age=current_user.age,
        monthly_income=current_user.monthly_income,
        monthly_expenses=summary.total_expenses,
        dependents=current_user.dependents,
        has_emergency_fund=current_user.has_emergency_fund,
    )
    return suggest_allocation(profile, savings_rate_override=summary.savings_rate)


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