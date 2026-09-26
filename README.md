# Finance Advisor

A full-stack personal finance backend that recommends an investment
allocation (Equity / Debt / Gold / FD) based on a logged-in user's age,
income, and real spending data — with plain-English reasoning behind
every recommendation.

Each user signs up, logs their transactions, and gets a personalized,
explainable allocation computed from their own saved data — not a
hardcoded demo.

## Why this project

Most "robo-advisor" demos let an LLM guess numbers, which makes them
unauditable and untestable. Here, the allocation logic is deterministic,
rule-based Python — fully unit-tested and explainable. An AI/MCP layer
(planned) will only narrate these results in natural language, never
invent them.

## Features

- **Auth**: signup/login with hashed passwords and JWT tokens
- **Per-user data isolation**: each user only sees their own transactions
  and recommendations
- **Spending tracking**: log transactions, see category breakdowns and
  savings rate
- **Personalized allocation engine**: rule-based Equity/Debt/Gold/FD
  split with human-readable reasoning for every recommendation
- **Simple web UI**: signup, login, and a dashboard to add transactions
  and view your allocation — no need to use Swagger to demo it
- **Postgres persistence**, running via Docker

## Tech stack

- Python, FastAPI
- PostgreSQL + SQLAlchemy (via Docker)
- Pydantic (data validation)
- JWT auth (python-jose) + bcrypt password hashing (passlib)
- Vanilla HTML/CSS/JS frontend, served by FastAPI
- Pytest for unit tests on the core engine

## Project structure

app/
├── core/
│ ├── models.py # Pydantic schemas (UserProfile, Transaction, etc.)
│ ├── allocation.py # Core allocation engine (suggest_allocation)
│ ├── spending.py # Spending summary & savings rate calculation
│ └── security.py # Password hashing, JWT creation/validation
├── db/
│ ├── database.py # SQLAlchemy engine/session setup
│ └── models.py # DB tables: UserDB, TransactionDB
├── static/
│ ├── signup.html
│ ├── login.html
│ ├── dashboard.html
│ └── style.css
└── main.py # FastAPI app & all routes
tests/
├── test_allocation.py
└── test_spending.py
docker-compose.yml # Postgres container


## Setup

**1. Start Postgres:**
```bash
docker compose up -d
```

**2. Create a virtual environment and install dependencies:**
```bash
python -m venv venv
source venv/bin/activate   # venv\Scripts\activate on Windows
pip install -r requirements.txt
```

**3. Create a `.env` file** in the project root:

DATABASE_URL=postgresql+psycopg2://finance_user:finance_pass@localhost:5432/finance_advisor
SECRET_KEY=your-random-secret-key-here


**4. Run the app:**
```bash
uvicorn app.main:app --reload
```

## Using it

**Via the web UI (recommended):**
Open `http://127.0.0.1:8000/static/signup.html`, create an account, and
you'll land on a dashboard where you can add transactions and see your
personalized allocation update live.

**Via the API directly:**
Open `http://127.0.0.1:8000/docs` for the interactive Swagger UI —
useful for testing individual endpoints (`/signup`, `/login`,
`/transactions`, `/recommend`).

## Run tests

```bash
pytest tests/ -v
```

Tests cover the core allocation engine and spending summary logic —
the two most important, deterministic parts of the system.

## Allocation logic (current rules)

1. **Emergency fund check** — flags if the user lacks roughly 6 months
   of expenses saved, and recommends prioritizing that first.
2. **Base equity %** = `100 - age`, clamped to 20–80%.
3. **Adjusted by savings rate** — computed from real logged transactions,
   not a static field. High savers get pushed toward more equity, low
   savers toward safer instruments.
4. **Gold** fixed at ~7.5% for diversification.
5. **Remainder** split between Debt and FD.

Every recommendation returns the reasoning behind each number, not just
the percentages themselves.

## Roadmap

- [x] Core allocation engine + tests
- [x] Spending summary from real transactions
- [x] FastAPI layer
- [x] Postgres persistence
- [x] Auth (signup/login, JWT, per-user data isolation)
- [x] Web UI (signup, login, dashboard)
- [ ] Goal-based SIP planner
- [ ] Real mutual fund NAV data integration
- [ ] MCP server layer (expose core logic as MCP tools for AI assistants)
- [ ] Dockerize the FastAPI app itself (currently only Postgres runs in Docker)
- [ ] CI via GitHub Actions

## Design notes

- The recommendation engine (`app/core/allocation.py`) is pure,
  framework-agnostic Python — it doesn't know about FastAPI, the
  database, or auth. This keeps it independently testable and reusable
  (e.g. by a future MCP layer) without duplicating logic.
- Database models (`UserDB`, `TransactionDB`) are kept separate from
  API/validation schemas (`UserProfile`, `Transaction`) — a standard
  pattern that decouples the persistence layer from the API contract.