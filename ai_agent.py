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
_MODEL = "gemini-2.0-flash"

_SYSTEM_PROMPT = """You are an expert ETF research assistant for a Canadian-focused retail investing platform.
You have access to a database of ETFs including Canadian and US-listed funds.

When answering:
- Be concise but thorough. Use plain language — no jargon unless necessary.
- When comparing ETFs, use the actual data provided. Never fabricate numbers.
- If data is missing (shown as null/None), say so honestly.
- Format numbers clearly: yields as %, MERs as %, AUM in billions/millions.
- For Canadian investors, note whether an ETF is TFSA/RRSP eligible when relevant.
- You may give an opinion or recommendation, but always note it is not financial advice.

ETF data from the database will be provided with each message as context.
If the user asks about a specific ETF and it's not in the context, say you don't have data on it."""


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
    # Extract keywords from recent messages to fetch relevant ETFs
    recent_text = " ".join(m["content"] for m in messages[-3:]).lower()
    etfs = await _fetch_relevant_etfs(recent_text, db_fetch)
    context_block = _format_etf_context(etfs)

    # Build Gemini history (all but last user message)
    history = []
    for m in messages[:-1]:
        role = "user" if m["role"] == "user" else "model"
        history.append(types.Content(role=role, parts=[types.Part(text=m["content"])]))

    # Last user message gets the DB context injected
    last_content = messages[-1]["content"]
    augmented = f"{last_content}\n\n[ETF Database Context]\n{context_block}"

    chat_session = _CLIENT.chats.create(
        model=_MODEL,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            temperature=0.4,
            max_output_tokens=800,
        ),
        history=history,
    )

    response = chat_session.send_message(augmented)
    return response.text


async def generate_overview(etf: dict) -> str:
    """Generate a 2-3 sentence plain-English overview for an ETF detail page."""
    prompt = f"""Write a 2-3 sentence plain-English overview of this ETF for a retail Canadian investor.
Focus on: what it holds, who it's best for, and one key strength or risk.
Do not start with the ticker name. Do not use bullet points.

ETF Data:
- Ticker: {etf.get('ticker')}
- Name: {etf.get('name')}
- Provider: {etf.get('provider')}
- Asset Class: {etf.get('asset_class')}
- Strategy: {etf.get('strategy_type')}
- MER: {etf.get('mer')}%
- Distribution Yield: {etf.get('distribution_yield')}%
- Geographic Exposure: {etf.get('geographic_exposure')}
- AUM: ${etf.get('aum_cad')}M CAD
- Exchange: {etf.get('exchange')}
- Covered Call: {etf.get('is_covered_call')}
- Leveraged: {etf.get('is_leveraged')}
- Risk Score: {etf.get('risk_score')}/5
- AI Summary: {etf.get('ai_summary')}
"""
    response = _CLIENT.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.3, max_output_tokens=200),
    )
    return response.text.strip()


async def _fetch_relevant_etfs(query_text: str, db_fetch) -> list[dict]:
    """Simple keyword-based ETF lookup from the DB."""
    # Check for specific tickers mentioned (2-5 uppercase letters)
    import re
    tickers = re.findall(r'\b([A-Z]{2,5})\b', query_text.upper())

    rows = []
    if tickers:
        placeholders = ",".join("?" for _ in tickers[:5])
        rows = await db_fetch(
            f"SELECT * FROM etfs WHERE ticker IN ({placeholders}) LIMIT 5",
            tickers[:5],
        )

    # Also do a text search based on keywords
    keyword_map = {
        "bond": "Bonds", "fixed income": "Bonds",
        "dividend": "Income", "income": "Income",
        "growth": "Growth", "sector": "Sector",
        "covered call": "Covered Call", "leverage": "Leveraged",
    }
    asset_filter = None
    for kw, val in keyword_map.items():
        if kw in query_text:
            asset_filter = val
            break

    if asset_filter:
        extra = await db_fetch(
            "SELECT * FROM etfs WHERE asset_class = ? OR strategy_type = ? OR growth_or_income = ? ORDER BY aum_cad DESC LIMIT 6",
            [asset_filter, asset_filter, asset_filter],
        )
        # Merge without duplicates
        existing = {r["ticker"] for r in rows}
        rows += [r for r in extra if r["ticker"] not in existing]
    elif not rows:
        # Fallback: top ETFs by AUM
        rows = await db_fetch(
            "SELECT * FROM etfs ORDER BY aum_cad DESC LIMIT 8", []
        )

    return rows
