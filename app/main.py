from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db, engine, Base
from app.db.models import UserDB, TransactionDB, IncomeSourceDB
from app.core.models import (
    UserProfile,
    AllocationResult,
    Transaction as TransactionSchema,
    SpendingSummary,
    UserSignup,
    UserLogin,
    Token,
    IncomeSource,
    ProfileUpdate,
)
from app.core.allocation import suggest_allocation
from app.core.spending import calculate_spending_summary
from app.core.security import hash_password, verify_password, create_access_token, get_current_user

app = FastAPI(title="Personal Finance Advisor")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

Base.metadata.create_all(bind=engine)


def current_month_str() -> str:
    return datetime.utcnow().strftime("%Y-%m")


# ============================================================
# PAGE ROUTES — serve the frontend HTML at clean URLs
# ============================================================

@app.get("/")
def root_page():
    return FileResponse("app/static/login.html")


@app.get("/login")
def login_page():
    return FileResponse("app/static/login.html")


@app.get("/signup")
def signup_page():
    return FileResponse("app/static/signup.html")


@app.get("/dashboard")
def dashboard_page():
    return FileResponse("app/static/dashboard.html")


@app.get("/profile")
def profile_page():
    return FileResponse("app/static/profile.html")


# ============================================================
# API ROUTES — all data endpoints, under /api
# ============================================================

@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---- Auth ----

@app.post("/api/signup", response_model=Token)
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


@app.post("/api/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token)


# ---- Profile ----

@app.post("/api/profile")
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


@app.get("/api/profile")
def get_profile(current_user: UserDB = Depends(get_current_user)):
    return {
        "email": current_user.email,
        "age": current_user.age,
        "dependents": current_user.dependents,
        "has_emergency_fund": current_user.has_emergency_fund,
        "profile_complete": current_user.profile_complete,
    }


# ---- Transactions ----

@app.post("/api/transactions")
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


@app.get("/api/transactions")
def get_transactions(
    month: Optional[str] = None,
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


@app.put("/api/transactions/{txn_id}")
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


@app.delete("/api/transactions/{txn_id}")
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


# ---- Income sources ----

@app.post("/api/income")
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


@app.get("/api/income")
def list_income(
    month: Optional[str] = None,
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


@app.put("/api/income/{income_id}")
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


@app.delete("/api/income/{income_id}")
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


# ---- Recommendation ----

@app.get("/api/recommend", response_model=AllocationResult)
def recommend_for_user(
    month: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    if not current_user.profile_complete:
        raise HTTPException(
            status_code=400,
            detail="Please complete your profile before requesting a recommendation.",
        )

    # Guard: age must be set (profile_complete flag alone isn't enough if
    # the DB row was created before the flag was introduced)
    if current_user.age is None:
        raise HTTPException(
            status_code=400,
            detail="Your profile is missing your age. Please update your profile.",
        )

    target_month = month or current_month_str()

    txns = (
        db.query(TransactionDB)
        .filter(TransactionDB.user_id == current_user.id, TransactionDB.month == target_month)
        .all()
    )
    income_sources = (
        db.query(IncomeSourceDB)
        .filter(IncomeSourceDB.user_id == current_user.id, IncomeSourceDB.month == target_month)
        .all()
    )

    if not txns and not income_sources:
        raise HTTPException(
            status_code=400,
            detail="Add at least one income source or transaction for this month to get a recommendation.",
        )

    txn_schemas = [
        TransactionSchema(category=t.category, amount=t.amount, description=t.description)
        for t in txns
    ]
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


# ---- Stateless recommend (kept for testing/demo without auth) ----

@app.post("/api/recommend-stateless", response_model=AllocationResult)
def recommend_stateless(profile: UserProfile) -> AllocationResult:
    return suggest_allocation(profile)


class RecommendFromTransactionsRequest(BaseModel):
    profile: UserProfile
    transactions: list[TransactionSchema]


@app.post("/api/recommend-from-transactions", response_model=AllocationResult)
def recommend_from_transactions(
    request: RecommendFromTransactionsRequest,
) -> AllocationResult:
    summary = calculate_spending_summary(
        request.transactions, request.profile.monthly_income
    )
    return suggest_allocation(
        request.profile, savings_rate_override=summary.savings_rate
    )