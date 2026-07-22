"""Clear cached ai_overview so all ETF pages regenerate with the new prompt."""
import asyncio, os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
from db import run, fetch_all

async def main():
    rows = await fetch_all("SELECT COUNT(*) as n FROM etfs WHERE ai_overview IS NOT NULL", [])
    print(f"Clearing {rows[0]['n']} cached overviews...")
    await run("UPDATE etfs SET ai_overview = NULL", [])
    print("Done.")

asyncio.run(main())
