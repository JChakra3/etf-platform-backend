import os
import httpx
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from db import fetch_all, fetch_one, run
from models import ETFSummary, ETFDetail, ETFHolding, SearchResponse

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

app = FastAPI(title="ETF Intelligence API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ── Columns returned for list/search views ───────────────────────────────────
_SUMMARY_COLS = """
    e.id, e.ticker, e.name, e.provider, e.country, e.currency,
    e.etf_category, e.asset_class, e.strategy_type, e.sector_focus,
    e.geographic_exposure, e.is_covered_call, e.is_leveraged,
    e.is_inverse, e.is_hedged, e.distribution_yield, e.dividend_frequency,
    e.growth_or_income, e.mer, e.aum_cad, e.price, e.exchange, e.risk_score
"""

_VALID_SORT = {"aum_cad", "mer", "distribution_yield", "risk_score", "name", "price"}


def _bools(row: dict) -> dict:
    """Cast SQLite 0/1 integers to Python booleans."""
    for k in ("is_covered_call", "is_leveraged", "is_inverse", "is_hedged",
              "is_esg", "tfsa_eligible", "rrsp_eligible"):
        if k in row:
            row[k] = bool(row[k])
    return row


# ── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


# ── FX Rate ──────────────────────────────────────────────────────────────────

_fx_cache: dict = {}

@app.get("/fx")
async def get_fx():
    """Returns live USD→CAD rate from frankfurter.app (cached per day)."""
    import time
    now = time.time()
    if _fx_cache.get("ts") and now - _fx_cache["ts"] < 3600:
        return _fx_cache["data"]
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get("https://api.frankfurter.app/latest?from=USD&to=CAD")
            resp.raise_for_status()
            rate = resp.json()["rates"]["CAD"]
    except Exception:
        rate = _fx_cache.get("data", {}).get("usd_to_cad", 1.36)
    data = {"usd_to_cad": rate}
    _fx_cache["data"] = data
    _fx_cache["ts"] = now
    return data


# ── Search ───────────────────────────────────────────────────────────────────

@app.get("/search", response_model=SearchResponse)
async def search_etfs(
    background_tasks: BackgroundTasks,
    q: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    currency: Optional[str] = Query(None),
    asset_class: Optional[str] = Query(None),
    strategy_type: Optional[str] = Query(None),
    sector_focus: Optional[str] = Query(None),
    is_covered_call: Optional[bool] = Query(None),
    is_leveraged: Optional[bool] = Query(None),
    is_hedged: Optional[bool] = Query(None),
    dividend_frequency: Optional[str] = Query(None),
    growth_or_income: Optional[str] = Query(None),
    risk_score_min: Optional[int] = Query(None, ge=1, le=5),
    risk_score_max: Optional[int] = Query(None, ge=1, le=5),
    mer_max: Optional[float] = Query(None, ge=0),
    yield_min: Optional[float] = Query(None, ge=0),
    aum_min_cad: Optional[float] = Query(None, ge=0),
    exchange: Optional[str] = Query(None),
    price_min: Optional[float] = Query(None, ge=0),
    price_max: Optional[float] = Query(None, ge=0),
    sort: str = Query("aum_cad"),
    order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    params: list = []
    where: list[str] = []

    # Text search — LIKE across ticker, name, provider, search_keywords
    # (FTS5 MATCH is not supported over Turso HTTP transport)
    if q and q.strip():
        term = f"%{q.strip()}%"
        where.append(
            "(e.ticker LIKE ? OR e.name LIKE ? OR e.provider LIKE ? OR e.search_keywords LIKE ?)"
        )
        params.extend([term, term, term, term])
        background_tasks.add_task(_log_search, q.strip())

    # Filters
    if country:
        where.append("e.country = ?"); params.append(country.upper())
    if currency:
        where.append("e.currency = ?"); params.append(currency.upper())
    if asset_class:
        where.append("e.asset_class = ?"); params.append(asset_class)
    if strategy_type:
        where.append("e.strategy_type = ?"); params.append(strategy_type)
    if sector_focus:
        where.append("e.sector_focus = ?"); params.append(sector_focus)
    if is_covered_call is not None:
        where.append("e.is_covered_call = ?"); params.append(1 if is_covered_call else 0)
    if is_leveraged is not None:
        where.append("e.is_leveraged = ?"); params.append(1 if is_leveraged else 0)
    if is_hedged is not None:
        where.append("e.is_hedged = ?"); params.append(1 if is_hedged else 0)
    if dividend_frequency:
        where.append("e.dividend_frequency = ?"); params.append(dividend_frequency)
    if growth_or_income:
        where.append("e.growth_or_income = ?"); params.append(growth_or_income)
    if risk_score_min is not None:
        where.append("e.risk_score >= ?"); params.append(risk_score_min)
    if risk_score_max is not None:
        where.append("e.risk_score <= ?"); params.append(risk_score_max)
    if mer_max is not None:
        where.append("e.mer <= ?"); params.append(mer_max)
    if yield_min is not None:
        where.append("e.distribution_yield >= ?"); params.append(yield_min)
    if aum_min_cad is not None:
        where.append("e.aum_cad >= ?"); params.append(aum_min_cad)
    if exchange:
        where.append("e.exchange = ?"); params.append(exchange)
    if price_min is not None:
        where.append("e.price >= ?"); params.append(price_min)
    if price_max is not None:
        where.append("e.price <= ?"); params.append(price_max)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    safe_sort  = sort  if sort  in _VALID_SORT   else "aum_cad"
    safe_order = "DESC" if order.lower() == "desc" else "ASC"
    # CASE WHEN used for NULL-last sorting (IS NULL in ORDER BY not supported over Turso HTTP)
    order_sql  = f"ORDER BY CASE WHEN e.{safe_sort} IS NULL THEN 1 ELSE 0 END, e.{safe_sort} {safe_order}"
    offset     = (page - 1) * page_size

    count_rows = await fetch_all(f"SELECT COUNT(*) AS n FROM etfs e {where_sql}", params)
    total      = count_rows[0]["n"] if count_rows else 0

    rows = await fetch_all(
        f"SELECT {_SUMMARY_COLS} FROM etfs e {where_sql} {order_sql} LIMIT ? OFFSET ?",
        params + [page_size, offset],
    )

    return SearchResponse(
        results=[ETFSummary(**_bools(r)) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── ETF Detail ───────────────────────────────────────────────────────────────

@app.get("/etfs/{ticker}", response_model=ETFDetail)
async def get_etf(ticker: str):
    row = await fetch_one(
        "SELECT * FROM etfs WHERE ticker = ? COLLATE NOCASE", [ticker]
    )
    if not row:
        raise HTTPException(status_code=404, detail=f"ETF '{ticker}' not found")

    _bools(row)

    # Most recent holdings snapshot
    holdings = await fetch_all(
        """
        SELECT holding_ticker, holding_name, weight_pct, asset_type, country, as_of_date
        FROM etf_holdings
        WHERE etf_id = ?
          AND as_of_date = (SELECT MAX(as_of_date) FROM etf_holdings WHERE etf_id = ?)
        ORDER BY weight_pct DESC
        LIMIT 25
        """,
        [row["id"], row["id"]],
    )

    return ETFDetail(
        **row,
        holdings=[ETFHolding(**h) for h in holdings],
    )


# ── Background task ───────────────────────────────────────────────────────────

async def _log_search(query: str) -> None:
    try:
        await run("INSERT INTO search_events (query) VALUES (?)", [query])
    except Exception:
        pass  # never crash a request over analytics
