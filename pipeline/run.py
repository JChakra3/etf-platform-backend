"""
Main pipeline entry point.
Run manually:          python -m pipeline.run
Run via GitHub Actions: python -m pipeline.run

1. Calls Yahoo Finance screener to discover all ETFs with AUM > $10M
2. Inserts any new ETFs not already in the database
3. Scrapes each ETF's Yahoo Finance page with Gemini for MER/yield/AUM/price/holdings
4. Upserts results into Turso
"""
import asyncio
import os
import time
from datetime import datetime, UTC

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from pipeline.screener import get_all_etfs
from pipeline.extract import scrape_etf
from pipeline.etf_universe import ETF_UNIVERSE
from ai_agent import generate_overview, generate_search_tags

db = None

USD_TO_CAD = 1.36


def _aum_to_cad_millions(aum_millions: float | None, currency: str) -> float | None:
    if aum_millions is None:
        return None
    if currency == "USD":
        return round(aum_millions * USD_TO_CAD, 2)
    return round(aum_millions, 2)


def _ticker_to_yahoo_url(ticker: str) -> str:
    return f"https://finance.yahoo.com/quote/{ticker}/"


async def _ensure_etf_exists(ticker: str, info: dict) -> None:
    """Insert ETF into DB if it doesn't exist yet."""
    existing = await db.fetch_one(
        "SELECT id FROM etfs WHERE ticker = ? COLLATE NOCASE", [ticker]
    )
    if existing:
        return

    currency = info.get("currency") or ("CAD" if info.get("country") == "CA" else "USD")
    country  = info.get("country", "US")
    name     = info.get("name") or ticker
    exchange = info.get("exchange") or ""
    price    = info.get("price")
    volume   = info.get("volume")
    now      = datetime.now(UTC).isoformat()

    await db.run(
        """
        INSERT OR IGNORE INTO etfs (
            ticker, name, provider, exchange, country, currency,
            etf_category, asset_class, strategy_type, geographic_exposure,
            price, volume, last_scraped_at, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ticker, name, "Unknown", exchange, country, currency,
            "Unknown", "Unknown", "Unknown", "Unknown",
            price, volume, now, now, now,
        ],
    )
    print(f"    => NEW ETF inserted: {ticker} ({name})")


async def run_pipeline():
    global db
    import db as _db
    db = _db

    now   = datetime.now(UTC).isoformat()
    as_of = datetime.now(UTC).strftime("%Y-%m-%d")

    # Ensure search_keywords column exists
    try:
        await db.run("ALTER TABLE etfs ADD COLUMN search_keywords TEXT", [])
    except Exception:
        pass  # column already exists

    print(f"\n{'='*60}")
    print(f"  ETF Scrape Pipeline  —  {now[:19]}Z")
    print(f"{'='*60}\n")

    # ── Step 1: Discover ETFs from screener ──────────────────────────────────
    print("  [1/3] Running Yahoo Finance screener...\n")
    screener_etfs = get_all_etfs()

    if not screener_etfs:
        print("  [WARN] Screener returned 0 results — falling back to static ETF universe")
        screener_etfs = ETF_UNIVERSE

    # ── Step 2: Insert new ETFs ───────────────────────────────────────────────
    print(f"\n  [2/3] Syncing {len(screener_etfs)} ETFs to database...\n")
    for info in screener_etfs:
        await _ensure_etf_exists(info["ticker"], info)

    # ── Step 3: Scrape each ETF with Gemini ──────────────────────────────────
    ticker_meta = {e["ticker"]: e for e in screener_etfs}
    all_tickers = list(ticker_meta.keys())

    print(f"\n  [3/3] Scraping {len(all_tickers)} ETFs with Gemini...\n")
    ok = 0
    skipped = 0

    for ticker in all_tickers:
        meta     = ticker_meta[ticker]
        currency = meta.get("currency") or "USD"
        url      = _ticker_to_yahoo_url(ticker)

        print(f"  [{ticker}]  {url}")

        result = scrape_etf(ticker, url)

        if result is None:
            print(f"    => SKIPPED (scrape failed)\n")
            skipped += 1
            time.sleep(2)
            continue

        aum_cad = _aum_to_cad_millions(result.aum_millions, currency)
        price   = result.price or meta.get("price")

        updates: list[str] = ["last_scraped_at = ?", "updated_at = ?"]
        params: list       = [now, now]

        if result.mer is not None and result.mer > 0:
            updates.append("mer = ?");                params.append(result.mer)
        if result.management_fee is not None:
            updates.append("management_fee = ?");     params.append(result.management_fee)
        if result.distribution_yield is not None:
            updates.append("distribution_yield = ?"); params.append(result.distribution_yield)
        if aum_cad is not None:
            updates.append("aum_cad = ?");            params.append(aum_cad)
        if price is not None:
            updates.append("price = ?");              params.append(price)
        if meta.get("volume") is not None:
            updates.append("volume = ?");             params.append(meta["volume"])
        if result.exchange:
            updates.append("exchange = ?");           params.append(result.exchange)

        params.append(ticker)

        await db.run(
            f"UPDATE etfs SET {', '.join(updates)} WHERE ticker = ? COLLATE NOCASE",
            params,
        )

        if result.holdings:
            etf_row = await db.fetch_one(
                "SELECT id FROM etfs WHERE ticker = ? COLLATE NOCASE", [ticker]
            )
            if etf_row:
                etf_id = etf_row["id"]
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

        print(f"    price={price}  MER={result.mer}  yield={result.distribution_yield}  "
              f"AUM={aum_cad}M CAD  holdings={len(result.holdings)}")

        # Generate AI overview + search tags
        etf_row_full = await db.fetch_one(
            "SELECT * FROM etfs WHERE ticker = ? COLLATE NOCASE", [ticker]
        )
        if etf_row_full:
            etf_dict = dict(etf_row_full)

            # Search tags (pure logic, no Gemini)
            tags = generate_search_tags(etf_dict)
            await db.run(
                "UPDATE etfs SET search_keywords = ? WHERE ticker = ? COLLATE NOCASE",
                [tags, ticker],
            )
            print(f"    => Tags: {tags[:80]}{'...' if len(tags) > 80 else ''}")

            # AI overview (cached — only generate if missing)
            if not etf_dict.get("ai_overview"):
                try:
                    overview = await generate_overview(etf_dict)
                    await db.run(
                        "UPDATE etfs SET ai_overview = ? WHERE ticker = ? COLLATE NOCASE",
                        [overview, ticker],
                    )
                    print(f"    => Overview generated ({len(overview)} chars)")
                except Exception as e:
                    print(f"    => Overview failed: {e}")
                time.sleep(2)

        print(f"    => OK\n")
        ok += 1

        time.sleep(4)

    print(f"{'='*60}")
    print(f"  Done — {ok} updated, {skipped} skipped")
    print(f"{'='*60}\n")


async def _main():
    await run_pipeline()
    if db and hasattr(db, '_client') and db._client:
        await db._client.close()

if __name__ == "__main__":
    asyncio.run(_main())
