"""
AI agent logic: conversational ETF assistant powered by Gemini.
Uses the DB as context — searches for relevant ETFs based on the conversation,
then passes structured data to Gemini alongside the full chat history.
"""
import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

_CLIENT = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
_MODEL = "gemini-3.5-flash"

_SYSTEM_PROMPT = """You are an expert ETF research assistant for a Canadian-focused retail investing platform.

HOW TO ANSWER:
Step 1 - Check the ETF Database Context appended to the user's message. These are real ETFs from our platform with live data (MER, yield, AUM, exchange, price).
Step 2 - Use the database ETFs as your primary examples. Mention their real ticker, what they track, their MER, and yield.
Step 3 - Supplement with your own ETF knowledge for any well-known ETFs not in the database (VFV, XIU, ZAG, VAB, QQQ, SPY, etc.). Note if they may not be on our platform.
Step 4 - Combine both into a clear, complete answer that directly addresses the user's question.

ALWAYS name specific ETF tickers. Never give a vague answer. If asked about any ETF category, list at least 3-5 real ETFs with their tickers, what index they track, approximate MER, and typical yield range. Use real numbers from the database when available; use your training knowledge otherwise.

FORMATTING:
- Plain text only. No markdown, no asterisks, no bold, no # headings.
- One short intro sentence, then a numbered list of ETFs, then a brief closing explanation.
- Each ETF entry: "1. TICKER - Name (what it tracks). MER: X%. Yield: ~X%. Suited for: [investor type]."

BOUNDARIES:
- Never say "you should buy X" or make a direct personal recommendation.
- Always end with: This is for informational purposes only and is not financial advice. Please consult a financial advisor."""


def _format_etf_context(etfs: list[dict]) -> str:
    if not etfs:
        return "No specific ETF data found for this query."
    lines = []
    for e in etfs[:8]:
        lines.append(
            f"- {e.get('ticker')} | {e.get('name')} | {e.get('provider')} | "
            f"MER: {e.get('mer')}% | Yield: {e.get('distribution_yield')}% | "
            f"AUM: ${e.get('aum_cad')}M CAD | Exchange: {e.get('exchange')} | "
            f"Asset Class: {e.get('asset_class')} | Strategy: {e.get('strategy_type')} | "
            f"Currency: {e.get('currency')} | Country: {e.get('country')} | "
            f"Price: {e.get('price')} | Risk Score: {e.get('risk_score')}/5 | "
            f"Covered Call: {e.get('is_covered_call')} | Leveraged: {e.get('is_leveraged')}"
        )
    return "\n".join(lines)


async def chat(messages: list[dict], db_fetch) -> str:
    """
    messages: list of {role: 'user'|'assistant', content: str}
    db_fetch: async callable(sql, params) -> list[dict]
    """
    recent_text = " ".join(m["content"] for m in messages[-3:]).lower()
    etfs = await _fetch_relevant_etfs(recent_text, db_fetch)
    context_block = _format_etf_context(etfs)

    # Build contents as plain dicts (same pattern as pipeline/extract.py)
    contents = []
    for m in messages[:-1]:
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})

    last_content = messages[-1]["content"]
    augmented = f"{last_content}\n\n[ETF Database Context]\n{context_block}"
    contents.append({"role": "user", "parts": [{"text": augmented}]})

    # If only one message, generate_content accepts a plain string
    if len(contents) == 1:
        prompt = f"{_SYSTEM_PROMPT}\n\n{augmented}"
        response = _CLIENT.models.generate_content(
            model=_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.4, max_output_tokens=3000),
        )
    else:
        response = _CLIENT.models.generate_content(
            model=_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                temperature=0.4,
                max_output_tokens=3000,
            ),
        )
    return response.text


def _mer_label(mer) -> str:
    if mer is None: return "MER: not available"
    pct = mer * 100
    if pct < 0.10: return f"MER: {pct:.3f}% (exceptionally low — one of the cheapest funds available; fees have almost no impact on returns)"
    if pct < 0.25: return f"MER: {pct:.2f}% (very low — well below the industry average of ~0.5%)"
    if pct < 0.50: return f"MER: {pct:.2f}% (low cost — below the industry average)"
    if pct < 0.90: return f"MER: {pct:.2f}% (moderate — near the industry average)"
    return f"MER: {pct:.2f}% (high — above average; will noticeably drag long-term returns)"

def _yield_label(yld) -> str:
    if yld is None: return "Distribution yield: not available"
    pct = yld * 100
    if pct == 0: return "Distribution yield: 0% (no regular payouts; growth-only fund)"
    if pct < 1.0: return f"Distribution yield: {pct:.2f}% (very low; this is primarily a growth-focused fund)"
    if pct < 3.0: return f"Distribution yield: {pct:.2f}% (modest income alongside capital growth)"
    if pct < 6.0: return f"Distribution yield: {pct:.2f}% (solid income component; attractive for income-focused investors)"
    return f"Distribution yield: {pct:.2f}% (high yield; primarily an income fund)"

def _aum_label(aum) -> str:
    if aum is None: return "AUM: not available"
    if aum > 10_000: return f"AUM: ${aum/1000:.1f}B CAD (very large — excellent liquidity, tight bid-ask spreads)"
    if aum > 1_000:  return f"AUM: ${aum/1000:.1f}B CAD (large fund — good liquidity)"
    if aum > 100:    return f"AUM: ${aum:.0f}M CAD (mid-sized — reasonable liquidity)"
    return f"AUM: ${aum:.0f}M CAD (smaller fund — liquidity may be limited; watch bid-ask spreads)"


async def generate_overview(etf: dict) -> str:
    """Generate a data-driven plain-English overview for an ETF detail page."""
    ticker   = etf.get('ticker', '')
    name     = etf.get('name', '')
    provider = etf.get('provider', '')
    asset    = etf.get('asset_class', '')
    strategy = etf.get('strategy_type', '')
    geo      = etf.get('geographic_exposure', '')
    exchange = etf.get('exchange', '')
    covered  = etf.get('is_covered_call', False)
    leveraged = etf.get('is_leveraged', False)
    risk     = etf.get('risk_score')

    flags = []
    if covered:  flags.append("uses covered call options to generate extra income (which can cap upside)")
    if leveraged: flags.append("uses leverage — amplifies both gains and losses, higher risk")

    prompt = f"""You are writing the AI overview card on an ETF research platform. Write exactly 4 sentences in plain, direct English about {ticker} ({name}) for a Canadian retail investor. No bullet points, no markdown, no headers.

Sentence 1: What this ETF is and what it holds or tracks (use your knowledge of {ticker}).
Sentence 2: Who this ETF suits and what investing goal it serves.
Sentence 3: Make a specific observation about the fee using this fact — {_mer_label(etf.get('mer'))}
Sentence 4: Make a specific observation about the yield and fund size using these facts — {_yield_label(etf.get('distribution_yield'))} | {_aum_label(etf.get('aum_cad'))}

Additional context (use only if relevant):
- Provider: {provider}
- Asset class: {asset}
- Strategy: {strategy}
- Geographic exposure: {geo}
- Exchange: {exchange}
- Risk score: {risk}/5
{('- Special notes: ' + '; '.join(flags)) if flags else ''}

Output only the 4 sentences, nothing else. No labels, no intro, no sign-off."""
    response = _CLIENT.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=600),
    )
    return response.text.strip()


async def _fetch_relevant_etfs(query_text: str, db_fetch) -> list[dict]:
    """Intent-aware ETF lookup from the DB."""
    import re
    q = query_text.lower()
    rows = []
    existing: set[str] = set()

    def _merge(new_rows):
        for r in new_rows:
            if r["ticker"] not in existing:
                existing.add(r["ticker"])
                rows.append(r)

    # 1. Specific tickers mentioned by the user
    tickers = re.findall(r'\b([A-Z]{2,5})\b', query_text.upper())
    if tickers:
        placeholders = ",".join("?" for _ in tickers[:6])
        _merge(await db_fetch(
            f"SELECT * FROM etfs WHERE ticker IN ({placeholders})",
            tickers[:6],
        ))

    # 2. Intent-based queries — translate natural language to SQL filters
    intents = []

    if any(w in q for w in ["low yield", "low distribution", "growth", "growth etf", "simple", "broad market", "index", "safe"]):
        intents.append(("distribution_yield ASC", "growth_or_income = 'Growth' OR asset_class = 'Stocks'"))

    if any(w in q for w in ["high yield", "income", "dividend", "monthly", "distribution"]):
        intents.append(("distribution_yield DESC", "distribution_yield > 0"))

    if any(w in q for w in ["bond", "fixed income", "safe", "low risk", "conservative"]):
        intents.append(("aum_cad DESC", "asset_class = 'Bonds'"))

    if any(w in q for w in ["covered call", "option", "enhanced yield"]):
        intents.append(("distribution_yield DESC", "is_covered_call = 1"))

    if any(w in q for w in ["leverage", "leveraged", "2x", "3x"]):
        intents.append(("aum_cad DESC", "is_leveraged = 1"))

    if any(w in q for w in ["sector", "tech", "technology", "health", "energy", "financial"]):
        intents.append(("aum_cad DESC", "strategy_type = 'Sector'"))

    if any(w in q for w in ["canadian", "canada", "tsx", "canadian market"]):
        intents.append(("aum_cad DESC", "country = 'CA'"))

    if any(w in q for w in ["us ", "american", "s&p", "nasdaq", "nyse", "united states"]):
        intents.append(("aum_cad DESC", "country = 'US'"))

    if any(w in q for w in ["cheap", "low mer", "low fee", "low cost", "low expense"]):
        intents.append(("mer ASC", "mer IS NOT NULL AND mer > 0"))

    if any(w in q for w in ["gold", "commodity", "commodities", "oil", "real estate", "reit"]):
        intents.append(("aum_cad DESC", "asset_class IN ('Gold', 'Commodities', 'Real Estate')"))

    for order, where in intents:
        _merge(await db_fetch(
            f"SELECT * FROM etfs WHERE {where} AND aum_cad IS NOT NULL ORDER BY {order} LIMIT 8",
            [],
        ))

    # 3. Fallback: top ETFs by AUM if nothing matched
    if not rows:
        _merge(await db_fetch(
            "SELECT * FROM etfs WHERE aum_cad IS NOT NULL ORDER BY aum_cad DESC LIMIT 12", []
        ))

    return rows[:15]
