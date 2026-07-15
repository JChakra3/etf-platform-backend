"""
Discovers ETFs from Yahoo Finance's screener API.
Filters by minimum AUM to avoid tiny/illiquid funds.
Returns US and Canadian ETFs with basic metadata.
"""
import httpx
import time

MIN_AUM_USD = 10_000_000   # $10M minimum AUM
PAGE_SIZE   = 250

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://finance.yahoo.com/",
}


def _get_crumb(session: httpx.Client) -> str:
    session.get("https://finance.yahoo.com/", follow_redirects=True)
    time.sleep(1)
    resp = session.get(
        "https://query1.finance.yahoo.com/v1/test/getcrumb",
        follow_redirects=True,
    )
    resp.raise_for_status()
    return resp.text.strip()


def _exchange_to_country(exchange: str, currency: str) -> str:
    ca_exchanges = {"Toronto", "TSX", "TSX Venture", "CNQ", "NEO"}
    if any(e in exchange for e in ca_exchanges):
        return "CA"
    if currency == "CAD":
        return "CA"
    return "US"


def get_all_etfs(min_aum_usd: float = MIN_AUM_USD) -> list[dict]:
    """
    Returns list of dicts with keys:
      ticker, name, exchange, country, currency, price, volume, aum_usd
    """
    results = []

    with httpx.Client(headers=_HEADERS, follow_redirects=True, timeout=30) as session:
        try:
            crumb = _get_crumb(session)
        except Exception as e:
            print(f"  [SCREENER] Could not get crumb: {e}")
            return []

        offset = 0
        total = None

        while total is None or offset < total:
            payload = {
                "offset": offset,
                "size": PAGE_SIZE,
                "sortField": "fundnetassets",
                "sortType": "DESC",
                "quoteType": "ETF",
                "query": {
                    "operator": "AND",
                    "operands": [
                        {
                            "operator": "GT",
                            "operands": ["fundnetassets", min_aum_usd],
                        }
                    ],
                },
                "userId": "",
                "userIdType": "guid",
            }

            try:
                resp = session.post(
                    f"https://query1.finance.yahoo.com/v1/finance/screener"
                    f"?crumb={crumb}&formatted=false&lang=en-US&region=US",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                print(f"  [SCREENER] Request failed at offset {offset}: {e}")
                break

            result_block = data.get("finance", {}).get("result", [])
            if not result_block:
                break

            block  = result_block[0]
            quotes = block.get("quotes", [])
            if total is None:
                total = block.get("total", 0)
                print(f"  [SCREENER] Total ETFs matching filter: {total}")

            for q in quotes:
                ticker   = q.get("symbol", "")
                name     = q.get("shortName") or q.get("longName") or ticker
                exchange = q.get("fullExchangeName") or q.get("exchange") or ""
                currency = q.get("currency") or "USD"
                country  = _exchange_to_country(exchange, currency)
                price    = q.get("regularMarketPrice")
                volume   = q.get("regularMarketVolume")
                aum_usd  = q.get("netAssets")

                if not ticker:
                    continue

                results.append({
                    "ticker":   ticker,
                    "name":     name,
                    "exchange": exchange,
                    "country":  country,
                    "currency": currency,
                    "price":    price,
                    "volume":   volume,
                    "aum_usd":  aum_usd,
                })

            offset += PAGE_SIZE
            time.sleep(0.5)

    print(f"  [SCREENER] Found {len(results)} ETFs with AUM > ${min_aum_usd/1e6:.0f}M")
    return results
