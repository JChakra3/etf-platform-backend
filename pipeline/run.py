"""
Main pipeline entry point.
Run manually:          python -m pipeline.run
Run via Render Cron:   python -m pipeline.run

Loops all 19 ETFs, scrapes each one, validates with Pydantic,
then upserts MER / yield / AUM / holdings into Turso.
"""
import asyncio
import os
import sys
import time
from datetime import datetime, UTC

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from pipeline.sources import ETF_SOURCES
from pipeline.extract import scrape_etf

# Lazy import db so .env is loaded first
import importlib
db = None

# USD → CAD conversion rate (update monthly or pull from an FX API later)
USD_TO_CAD = 1.36


def _aum_to_cad_millions(aum_millions: float | None, currency: str) -> float | None:
    if aum_millions is None:
        return None
    if currency == "USD":
        return round(aum_millions * USD_TO_CAD, 2)
    return round(aum_millions, 2)


async def run_pipeline():
    global db
    import db as _db
    db = _db

    now = datetime.now(UTC).isoformat()
    as_of = datetime.now(UTC).strftime("%Y-%m-%d")

    tickers = list(ETF_SOURCES.keys())
    ok = 0
    skipped = 0

    print(f"\n{'='*55}")
    print(f"  ETF Scrape Pipeline  —  {now[:19]}Z")
    print(f"  ETFs to process: {len(tickers)}")
    print(f"{'='*55}\n")

    for ticker in tickers:
        source = ETF_SOURCES[ticker]
        url = source["url"]
        aum_currency = source["aum_currency"]

        print(f"  [{ticker}]  {url}")

        # ── Fetch + extract ──────────────────────────────────────────────────
        result = scrape_etf(ticker, url)

        if result is None:
            print(f"    => SKIPPED (scrape failed)\n")
            skipped += 1
            time.sleep(2)
            continue

        # ── Convert AUM to CAD millions ──────────────────────────────────────
        aum_cad = _aum_to_cad_millions(result.aum_millions, aum_currency)

        # ── Build update fields (only non-None values) ───────────────────────
        updates: list[str] = ["last_scraped_at = ?", "updated_at = ?"]
        params: list = [now, now]

        if result.mer is not None and result.mer > 0:
            updates.append("mer = ?");            params.append(result.mer)
        if result.management_fee is not None:
            updates.append("management_fee = ?"); params.append(result.management_fee)
        if result.distribution_yield is not None:
            updates.append("distribution_yield = ?"); params.append(result.distribution_yield)
        if aum_cad is not None:
            updates.append("aum_cad = ?");        params.append(aum_cad)

        params.append(ticker)  # for WHERE clause

        await db.run(
            f"UPDATE etfs SET {', '.join(updates)} WHERE ticker = ? COLLATE NOCASE",
            params,
        )

        # ── Upsert holdings if provided ───────────────────────────────────────
        if result.holdings:
            etf_row = await db.fetch_one(
                "SELECT id FROM etfs WHERE ticker = ? COLLATE NOCASE", [ticker]
            )
            if etf_row:
                etf_id = etf_row["id"]

                # Delete existing holdings for this ETF before reinserting
                await db.run(
                    "DELETE FROM etf_holdings WHERE etf_id = ? AND as_of_date = ?",
                    [etf_id, as_of],
                )

                for h in result.holdings:
                    ticker_val = h.holding_ticker or h.holding_name[:10]
                    await db.run(
                        """
                        INSERT INTO etf_holdings
                          (etf_id, holding_ticker, holding_name, weight_pct, asset_type, country, as_of_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        [etf_id, ticker_val, h.holding_name,
                         h.weight_pct, h.asset_type, h.country, as_of],
                    )

        # ── Summary ───────────────────────────────────────────────────────────
        print(f"    MER={result.mer}  yield={result.distribution_yield}  "
              f"AUM={aum_cad}M CAD  holdings={len(result.holdings)}")
        print(f"    => OK\n")
        ok += 1

        # Respect Gemini free tier: 15 req/min → 1 request every 4 seconds
        time.sleep(4)

    print(f"{'='*55}")
    print(f"  Done — {ok} updated, {skipped} skipped")
    print(f"{'='*55}\n")


async def _main():
    await run_pipeline()
    # Close the Turso client cleanly to avoid unclosed session warnings
    if db and hasattr(db, '_client') and db._client:
        await db._client.close()

if __name__ == "__main__":
    asyncio.run(_main())
