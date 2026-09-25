
# Finance Advisor

A backend service that recommends a personal investment allocation
(Equity / Debt / Gold / FD) based on a user's age, income, and spending
patterns — with human-readable reasoning behind every recommendation.

Built as a portfolio project to demonstrate clean backend architecture:
core business logic is deterministic, framework-agnostic Python, fully
unit-tested, and exposed through a FastAPI service (with an MCP server
layer planned).

## Why this project

Most "robo-advisor" demos let an LLM guess numbers, which makes them
unauditable and untestable. Here, the allocation logic is plain,
rule-based Python — testable and explainable — and any AI layer added
later only explains the output, never invents it.

## Tech stack

- Python
- FastAPI
- Pydantic
- Pytest

## Project structure

app/
├── core/
│ ├── models.py # UserProfile, AllocationResult
│ └── allocation.py # Core allocation engine (suggest_allocation)
└── main.py # FastAPI app, /recommend endpoint
tests/
└── test_allocation.py # Unit tests for the allocation engine


## Setup

```bash
python -m venv venv
source venv/bin/activate   # venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## Run the API

```bash
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/docs to try the `/recommend` endpoint.

## Run tests

```bash
pytest tests/ -v
```

## Allocation logic (current rules)

1. Emergency fund check — flags if the user lacks ~6 months of expenses saved.
2. Base equity % = `100 - age`, clamped to 20–80%.
3. Adjusted ±10% based on savings rate.
4. Gold fixed at ~7.5% for diversification.
5. Remainder split between Debt and FD.

Every recommendation includes the reasoning for each rule applied.

## Roadmap

- [x] Core allocation engine + tests
- [ ] FastAPI `/recommend` endpoint
- [ ] Spending summary from transactions
- [ ] Goal-based SIP planner
- [ ] PostgreSQL persistence
- [ ] Real mutual fund NAV data integration
- [ ] MCP server layer
- [ ] Docker + CI