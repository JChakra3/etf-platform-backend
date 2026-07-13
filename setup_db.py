"""
Initializes (or re-initializes) the Phase 1 schema in the active Turso database.
Run once before seeding:  python setup_db.py

Safe to re-run — uses DROP IF EXISTS so stale tables from older schemas are replaced.
FTS5 and IS NULL ORDER BY are excluded — not supported over Turso HTTP transport.
"""
import asyncio, os
from dotenv import load_dotenv
import libsql_client

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

STATEMENTS = [
    # ── Drop old tables (clears any previous simple schema) ──────────────────
    "DROP TABLE IF EXISTS etf_holdings",
    "DROP TABLE IF EXISTS etf_metrics",
    "DROP TABLE IF EXISTS search_events",
    "DROP TABLE IF EXISTS etfs",

    # ── Core ETF table ────────────────────────────────────────────────────────
    """
    CREATE TABLE etfs (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker              TEXT    NOT NULL UNIQUE COLLATE NOCASE,
        name                TEXT    NOT NULL,
        provider            TEXT    NOT NULL,
        exchange            TEXT    NOT NULL,
        country             TEXT    NOT NULL,
        currency            TEXT    NOT NULL,
        inception_date      TEXT,
        etf_category        TEXT    NOT NULL,
        asset_class         TEXT    NOT NULL,
        strategy_type       TEXT    NOT NULL,
        sector_focus        TEXT,
        geographic_exposure TEXT    NOT NULL,
        is_covered_call     INTEGER NOT NULL DEFAULT 0,
        is_leveraged        INTEGER NOT NULL DEFAULT 0,
        is_inverse          INTEGER NOT NULL DEFAULT 0,
        is_hedged           INTEGER NOT NULL DEFAULT 0,
        is_esg              INTEGER NOT NULL DEFAULT 0,
        distribution_yield  REAL,
        dividend_frequency  TEXT,
        growth_or_income    TEXT,
        mer                 REAL,
        management_fee      REAL,
        aum_cad             REAL,
        risk_score          INTEGER,
        risk_asset_class    INTEGER,
        risk_concentration  INTEGER,
        risk_leverage       INTEGER,
        risk_liquidity      INTEGER,
        risk_credit         INTEGER,
        risk_currency       INTEGER,
        tfsa_eligible       INTEGER NOT NULL DEFAULT 1,
        rrsp_eligible       INTEGER NOT NULL DEFAULT 1,
        withholding_tax_note TEXT,
        roc_note            TEXT,
        ai_summary          TEXT,
        search_keywords     TEXT,
        data_source_url     TEXT,
        last_scraped_at     TEXT NOT NULL DEFAULT (datetime('now')),
        created_at          TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,

    # ── Indexes ───────────────────────────────────────────────────────────────
    "CREATE INDEX idx_etfs_country     ON etfs (country)",
    "CREATE INDEX idx_etfs_asset_class ON etfs (asset_class)",
    "CREATE INDEX idx_etfs_strategy    ON etfs (strategy_type)",
    "CREATE INDEX idx_etfs_risk_score  ON etfs (risk_score)",
    "CREATE INDEX idx_etfs_mer         ON etfs (mer)",
    "CREATE INDEX idx_etfs_yield       ON etfs (distribution_yield)",
    "CREATE INDEX idx_etfs_aum         ON etfs (aum_cad)",
    "CREATE INDEX idx_etfs_div_freq    ON etfs (dividend_frequency)",

    # ── Holdings ──────────────────────────────────────────────────────────────
    """
    CREATE TABLE etf_holdings (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        etf_id          INTEGER NOT NULL,
        holding_ticker  TEXT    NOT NULL,
        holding_name    TEXT    NOT NULL,
        weight_pct      REAL    NOT NULL,
        asset_type      TEXT,
        country         TEXT,
        as_of_date      TEXT    NOT NULL,
        created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
    )
    """,
    "CREATE INDEX idx_holdings_etf ON etf_holdings (etf_id, weight_pct DESC)",

    # ── Historical metrics ────────────────────────────────────────────────────
    """
    CREATE TABLE etf_metrics (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        etf_id          INTEGER NOT NULL,
        metric_date     TEXT    NOT NULL,
        price           REAL,
        total_return_1y REAL,
        total_return_3y REAL,
        total_return_5y REAL,
        distribution    REAL,
        aum_cad         REAL,
        volume          INTEGER,
        created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
    )
    """,
    "CREATE INDEX idx_metrics_etf_date ON etf_metrics (etf_id, metric_date DESC)",

    # ── Search analytics ──────────────────────────────────────────────────────
    """
    CREATE TABLE search_events (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        query       TEXT    NOT NULL,
        result_count INTEGER,
        searched_at TEXT    NOT NULL DEFAULT (datetime('now'))
    )
    """,
]


async def main():
    client = libsql_client.create_client(
        url=os.environ["TURSO_URL"],
        auth_token=os.environ["TURSO_TOKEN"],
    )
    for stmt in STATEMENTS:
        sql = stmt.strip()
        try:
            await client.execute(sql)
            label = sql.split()[0:3]
            print(f"  OK  {' '.join(label)}")
        except Exception as e:
            print(f"  ERR {sql[:60]}... ERROR: {e}")

    await client.close()
    print("\nSchema ready. Run: python seed.py")

asyncio.run(main())
