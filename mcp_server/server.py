"""
server.py
---------
Finance Advisor MCP Server.

Exposes 3 tools to any MCP-compatible client:
  - get_transactions(user_id)
  - get_income(user_id)
  - get_summary(user_id)

Run locally:
    python -m mcp_server.server

Or via FastMCP dev mode:
    fastmcp dev mcp_server/server.py
"""

from fastmcp import FastMCP
from mcp_server.tools import get_transactions, get_income, get_summary

mcp = FastMCP(
    name="Finance Advisor",
    instructions="Provides financial data tools for per-user transaction and income files.",
)


@mcp.tool
def fetch_transactions(user_id: int) -> list[dict]:
    """Get all transactions for a user from their uploaded data files."""
    return get_transactions(user_id)


@mcp.tool
def fetch_income(user_id: int) -> list[dict]:
    """Get all income entries for a user from their uploaded data files."""
    return get_income(user_id)


@mcp.tool
def fetch_summary(user_id: int) -> dict:
    """
    Get a financial summary for a user:
    total_income, total_spending, balance, transaction_count.
    """
    return get_summary(user_id)


if __name__ == "__main__":
    mcp.run()
