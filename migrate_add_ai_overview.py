"""Add ai_overview column to etfs table."""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

from db import run

async def main():
    try:
        await run("ALTER TABLE etfs ADD COLUMN ai_overview TEXT", [])
        print("Added ai_overview column.")
    except Exception as e:
        print(f"Note: {e}")

asyncio.run(main())
