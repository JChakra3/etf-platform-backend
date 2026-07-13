"""
Turso database client — single shared async client for all requests.
Uses https:// transport (required on Windows where WebSockets are blocked).
"""
import os
import libsql_client
from dotenv import load_dotenv
from typing import Any

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

_client: libsql_client.Client | None = None


def get_client() -> libsql_client.Client:
    global _client
    if _client is None:
        _client = libsql_client.create_client(
            url=os.environ["TURSO_URL"],       # must be https://
            auth_token=os.environ["TURSO_TOKEN"],
        )
    return _client


async def fetch_all(sql: str, params: list[Any] | None = None) -> list[dict]:
    result = await get_client().execute(sql, params or [])
    cols = [col if isinstance(col, str) else col.name for col in result.columns]
    return [dict(zip(cols, row)) for row in result.rows]


async def fetch_one(sql: str, params: list[Any] | None = None) -> dict | None:
    rows = await fetch_all(sql, params)
    return rows[0] if rows else None


async def run(sql: str, params: list[Any] | None = None) -> int:
    result = await get_client().execute(sql, params or [])
    return result.rows_affected
