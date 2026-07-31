"""
One-time script: backfill search_keywords for all existing ETFs.
Run from the backend directory:  python backfill_tags.py
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

import db
from ai_agent import generate_search_tags


async def main():
    # Ensure column exists
    try:
        await db.run("ALTER TABLE etfs ADD COLUMN search_keywords TEXT", [])
        print("Added search_keywords column.")
    except Exception:
        print("search_keywords column already exists.")

    rows = await db.fetch_all("SELECT * FROM etfs ORDER BY ticker", [])
    print(f"\nBackfilling {len(rows)} ETFs...\n")

    for i, row in enumerate(rows, 1):
        tags = generate_search_tags(dict(row))
        await db.run(
            "UPDATE etfs SET search_keywords = ? WHERE ticker = ? COLLATE NOCASE",
            [tags, row["ticker"]],
        )
        print(f"  [{i:3}/{len(rows)}] {row['ticker']:8} → {tags[:70]}{'...' if len(tags) > 70 else ''}")

    print(f"\nDone. {len(rows)} ETFs tagged.")

    if db._client:
        await db._client.close()


if __name__ == "__main__":
    asyncio.run(main())
