"""
mcp_client.py
-------------
Thin wrapper that calls the MCP server tools directly as Python functions.

Since both FastAPI and the MCP server run in the same process, we import
the tool functions directly instead of making network calls.
This keeps things simple for local/Render deployment while still being
real MCP tool usage — the same functions the MCP server exposes.
"""

from mcp_server.tools import get_transactions, get_income, get_summary


def fetch_file_transactions(user_id: int) -> list[dict]:
    """Return transactions parsed from uploaded files for this user."""
    return get_transactions(user_id)


def fetch_file_income(user_id: int) -> list[dict]:
    """Return income entries parsed from uploaded files for this user."""
    return get_income(user_id)


def fetch_file_summary(user_id: int) -> dict:
    """Return financial summary from uploaded files for this user."""
    return get_summary(user_id)
