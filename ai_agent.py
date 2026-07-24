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


def _mer_sentence(mer) -> str | None:
    if mer is None: return None
    pct = mer * 100
    if pct < 0.10: return f"Its MER of {pct:.3f}% is exceptionally low, meaning fees take almost nothing from your returns each year."
    if pct < 0.25: return f"Its MER of {pct:.2f}% is very low, well below the industry average of around 0.5%, keeping more money working for you."
    if pct < 0.50: return f"Its MER of {pct:.2f}% is below the industry average, making it a cost-efficient option."
    if pct < 0.90: return f"Its MER of {pct:.2f}% is near the industry average, which is reasonable for the strategy it offers."
    return f"Its MER of {pct:.2f}% is above average, so investors should weigh the higher cost against the potential benefits of the strategy."

def _yield_sentence(yld, aum) -> str | None:
    if yld is None and aum is None: return None
    parts = []
    if yld is not None:
        pct = yld * 100
        if pct == 0:
            parts.append("It pays no regular distributions, so all returns come from price growth")
        elif pct < 1.0:
            parts.append(f"Its distribution yield of {pct:.2f}% is minimal, reflecting its focus on growth over income")
        elif pct < 3.0:
            parts.append(f"It offers a modest yield of {pct:.2f}%, providing a small income stream alongside growth")
        elif pct < 6.0:
            parts.append(f"Its distribution yield of {pct:.2f}% provides meaningful income, appealing to income-focused investors")
        else:
            parts.append(f"Its high distribution yield of {pct:.2f}% makes it primarily an income-generating fund")
    if aum is not None:
        if aum > 10_000:
            parts.append(f"and with over ${aum/1000:.0f}B CAD in assets it is one of the largest and most liquid ETFs available")
        elif aum > 1_000:
            parts.append(f"and its ${aum/1000:.1f}B CAD in assets gives it strong liquidity")
        elif aum > 100:
            parts.append(f"and its ${aum:.0f}M CAD in assets provides reasonable liquidity for most investors")
        else:
            parts.append(f"though its smaller size of ${aum:.0f}M CAD means liquidity may be more limited")
    return ", ".join(parts) + "." if parts else None


async def generate_overview(etf: dict) -> str:
    """Generate a data-driven plain-English overview for an ETF detail page."""
    ticker    = etf.get('ticker', '')
    name      = etf.get('name', '')
    provider  = etf.get('provider', '')
    asset     = etf.get('asset_class', '')
    strategy  = etf.get('strategy_type', '')
    geo       = etf.get('geographic_exposure', '')
    covered   = etf.get('is_covered_call', False)
    leveraged = etf.get('is_leveraged', False)

    flags = []
    if covered:  flags.append("uses covered call options to boost income, which can limit upside in strong markets")
    if leveraged: flags.append("uses leverage to amplify returns, which also amplifies losses and increases risk significantly")

    # Pre-build data sentences — skip any where data is missing
    mer_sentence   = _mer_sentence(etf.get('mer'))
    yield_sentence = _yield_sentence(etf.get('distribution_yield'), etf.get('aum_cad'))

    data_lines = []
    if mer_sentence:   data_lines.append(f"- Fee fact: {mer_sentence}")
    if yield_sentence: data_lines.append(f"- Yield/size fact: {yield_sentence}")
    if flags:          data_lines.append(f"- Special note: {'; '.join(flags)}")
    data_block = "\n".join(data_lines) if data_lines else "- No additional data available"

    prompt = f"""Write 3 short, plain English sentences about {ticker} ({name}) for a Canadian retail investor. Use only plain text: no asterisks, no dashes used as bullets, no markdown, no special characters, no em dashes.

Sentence 1: What this ETF tracks or holds and its general strategy. Use your knowledge of {ticker}.
Sentence 2: What type of investor this suits and why.
Sentence 3: Use one or two of these pre-written data facts, worked naturally into a sentence:
{data_block}

Rules: Output only the 3 sentences with no labels, no intro, no sign-off. Each sentence must be complete and end with a period. Keep each sentence under 30 words."""

    response = _CLIENT.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=1000),
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
