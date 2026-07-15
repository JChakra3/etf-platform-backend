"""
One-time migration: adds price and volume columns to the etfs table.
Run once: python migrate_add_price.py
"""
import asyncio, os
from dotenv import load_dotenv
import libsql_client

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

STATEMENTS = [
    "ALTER TABLE etfs ADD COLUMN price REAL",
    "ALTER TABLE etfs ADD COLUMN volume INTEGER",
    "CREATE INDEX IF NOT EXISTS idx_etfs_price ON etfs (price)",
]

async def main():
    client = libsql_client.create_client(
        url=os.environ["TURSO_URL"],
        auth_token=os.environ["TURSO_TOKEN"],
    )
    for stmt in STATEMENTS:
        try:
            await client.execute(stmt)
            print(f"  OK  {stmt[:60]}")
        except Exception as e:
            print(f"  SKIP {stmt[:60]} — {e}")
    await client.close()
    print("\nMigration done.")

asyncio.run(main())
