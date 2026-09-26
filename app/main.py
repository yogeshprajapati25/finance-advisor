from app.db.models import IncomeSourceDB
from app.core.models import IncomeSource
from fastapi import FastAPI
from pydantic import BaseModel
from app.core.models import ProfileUpdate

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
from datetime import datetime


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
        month=current_month_str(),
        user_id=current_user.id,
    )
    db.add(new_txn)
    db.commit()
    db.refresh(new_txn)
    return {
        "id": new_txn.id,
        "category": new_txn.category,
        "amount": new_txn.amount,
        "month": new_txn.month,
    }


@app.get("/transactions")
def get_transactions(
    month: str | None = None,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    query = db.query(TransactionDB).filter(TransactionDB.user_id == current_user.id)
    if month:
        query = query.filter(TransactionDB.month == month)
    txns = query.all()
    return [
        {
            "id": t.id,
            "category": t.category,
            "amount": t.amount,
            "description": t.description,
            "month": t.month,
        }
        for t in txns
    ]

@app.put("/transactions/{txn_id}")
def update_transaction(
    txn_id: int,
    txn: TransactionSchema,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    existing = (
        db.query(TransactionDB)
        .filter(TransactionDB.id == txn_id, TransactionDB.user_id == current_user.id)
        .first()
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Transaction not found")

    existing.category = txn.category
    existing.amount = txn.amount
    existing.description = txn.description
    db.commit()
    return {"message": "Updated"}


@app.delete("/transactions/{txn_id}")
def delete_transaction(
    txn_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    existing = (
        db.query(TransactionDB)
        .filter(TransactionDB.id == txn_id, TransactionDB.user_id == current_user.id)
        .first()
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(existing)
    db.commit()
    return {"message": "Deleted"}

@app.post("/recommend", response_model=AllocationResult)
def recommend(profile: UserProfile) -> AllocationResult:
    return suggest_allocation(profile)

@app.get("/recommend", response_model=AllocationResult)
def recommend_for_user(
    month: str | None = None,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    if not current_user.profile_complete:
        raise HTTPException(
            status_code=400,
            detail="Please complete your profile before requesting a recommendation.",
        )

    target_month = month or current_month_str()

    txns = (
        db.query(TransactionDB)
        .filter(TransactionDB.user_id == current_user.id, TransactionDB.month == target_month)
        .all()
    )
    txn_schemas = [
        TransactionSchema(category=t.category, amount=t.amount, description=t.description)
        for t in txns
    ]

    income_sources = (
        db.query(IncomeSourceDB)
        .filter(IncomeSourceDB.user_id == current_user.id, IncomeSourceDB.month == target_month)
        .all()
    )
    total_income = sum(i.amount for i in income_sources)

    summary = calculate_spending_summary(txn_schemas, total_income)

    profile = UserProfile(
        age=current_user.age,
        monthly_income=total_income,
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


def current_month_str() -> str:
    return datetime.utcnow().strftime("%Y-%m")


@app.post("/income")
def add_income(
    income: IncomeSource,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    new_income = IncomeSourceDB(
        name=income.name,
        amount=income.amount,
        month=income.month or current_month_str(),
        user_id=current_user.id,
    )
    db.add(new_income)
    db.commit()
    db.refresh(new_income)
    return {
        "id": new_income.id,
        "name": new_income.name,
        "amount": new_income.amount,
        "month": new_income.month,
    }


@app.get("/income")
def list_income(
    month: str | None = None,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    query = db.query(IncomeSourceDB).filter(IncomeSourceDB.user_id == current_user.id)
    if month:
        query = query.filter(IncomeSourceDB.month == month)
    sources = query.all()
    return [
        {"id": s.id, "name": s.name, "amount": s.amount, "month": s.month}
        for s in sources
    ]


@app.put("/income/{income_id}")
def update_income(
    income_id: int,
    income: IncomeSource,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    existing = (
        db.query(IncomeSourceDB)
        .filter(IncomeSourceDB.id == income_id, IncomeSourceDB.user_id == current_user.id)
        .first()
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Income source not found")

    existing.name = income.name
    existing.amount = income.amount
    existing.month = income.month or existing.month
    db.commit()
    return {"message": "Updated"}


@app.delete("/income/{income_id}")
def delete_income(
    income_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    existing = (
        db.query(IncomeSourceDB)
        .filter(IncomeSourceDB.id == income_id, IncomeSourceDB.user_id == current_user.id)
        .first()
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Income source not found")

    db.delete(existing)
    db.commit()
    return {"message": "Deleted"}

@app.post("/profile")
def complete_profile(
    profile: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    current_user.age = profile.age
    current_user.dependents = profile.dependents
    current_user.has_emergency_fund = profile.has_emergency_fund
    current_user.profile_complete = True
    db.commit()
    return {"message": "Profile updated"}


@app.get("/profile")
def get_profile(current_user: UserDB = Depends(get_current_user)):
    return {
        "email": current_user.email,
        "age": current_user.age,
        "dependents": current_user.dependents,
        "has_emergency_fund": current_user.has_emergency_fund,
        "profile_complete": current_user.profile_complete,
    }