"""
Fetches a page with httpx, strips it to readable text with BeautifulSoup,
then passes the cleaned text to Gemini for structured extraction.
Uses the google-genai SDK (v1 API endpoint — works with billing-enabled accounts).
"""
import os
import re
import json
import httpx
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from dotenv import load_dotenv

from pipeline.models import ScrapedETF

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

_CLIENT = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
_MODEL = "gemini-3.5-flash"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-CA,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_MAX_CHARS = 80_000


def _fetch_text(url: str, timeout: int = 20) -> str:
    """Download a page and return cleaned visible text."""
    with httpx.Client(headers=_HEADERS, follow_redirects=True, timeout=timeout) as client:
        resp = client.get(url)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "img",
                     "header", "footer", "nav", "aside"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    lines = [l for l in text.splitlines() if l.strip()]
    return "\n".join(lines)[:_MAX_CHARS]


_PROMPT_TEMPLATE = """
You are a financial data extraction assistant.

Below is the visible text from the official ETF provider page for {ticker}.
Extract the fields and return ONLY a single JSON object with exactly these keys:

{{
  "distribution_yield": <float or null>,
  "mer": <float or null>,
  "management_fee": <float or null>,
  "aum_millions": <float or null>,
  "price": <float or null>,
  "holdings": [
    {{
      "holding_ticker": <string or null>,
      "holding_name": <string>,
      "weight_pct": <float>,
      "asset_type": <"Equity"|"Bond"|"ETF"|"Cash"|"Other">,
      "country": <2-letter code e.g. "US" or "CA">
    }}
  ]
}}

Rules:
- Convert ALL percentages to decimals: 1.23% -> 0.0123, 0.09% -> 0.0009
- AUM in MILLIONS of native currency: $1.4B -> 1400.0, $560M -> 560.0, $1.4T -> 1400000.0
- Holdings weight_pct must be decimal: 7.1% -> 0.071
- price is the current market price per share/unit in native currency (e.g. 123.45)
- Return null for any field not found - never guess or invent data
- Return up to 10 holdings ordered by weight descending
- Return empty list [] for holdings if no holdings table found
- Return ONLY the JSON object, no markdown, no explanation

PAGE TEXT:
{text}
"""


def scrape_etf(ticker: str, url: str) -> ScrapedETF | None:
    """
    Fetch the ETF page, clean it, send to Gemini, validate with Pydantic.
    Returns None if the page fetch or extraction fails.
    """
    try:
        text = _fetch_text(url)
    except Exception as e:
        print(f"    [FETCH ERROR] {ticker}: {e}")
        return None

    prompt = _PROMPT_TEMPLATE.format(ticker=ticker, text=text)

    try:
        response = _CLIENT.models.generate_content(
            model=_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        raw = response.text
    except Exception as e:
        print(f"    [GEMINI ERROR] {ticker}: {e}")
        return None

    try:
        data = json.loads(_repair_json(raw))
        return ScrapedETF(**data)
    except Exception as e:
        print(f"    [PARSE ERROR] {ticker}: {e}\n    Raw: {raw[:300]}")
        return None


def _repair_json(raw: str) -> str:
    """Fix the two common Gemini JSON formatting bugs before parsing."""
    s = raw.strip()

    # Early exit — already valid
    try:
        json.loads(s)
        return s
    except json.JSONDecodeError:
        pass

    # Bug 1: one or more extra trailing `}` (sometimes separated by whitespace/newlines)
    # Keep stripping the last `}` until valid or nothing left to strip
    candidate = s
    while candidate.endswith("}"):
        candidate = candidate[:-1].rstrip()
        try:
            json.loads(candidate + "}")
            return candidate + "}"
        except json.JSONDecodeError:
            pass

    # Bug 2: truncated response — missing closing `]` and/or `}`
    # Re-start from original stripped string
    s2 = s
    open_brackets = s2.count("[") - s2.count("]")
    open_braces   = s2.count("{") - s2.count("}")
    s2 += "]" * max(open_brackets, 0) + "}" * max(open_braces, 0)
    return s2
