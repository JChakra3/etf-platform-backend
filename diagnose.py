"""Quick diagnostic — run with: python diagnose.py"""
import asyncio, os
from dotenv import load_dotenv
import libsql_client

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

async def main():
    c = libsql_client.create_client(
        url=os.environ["TURSO_URL"],
        auth_token=os.environ["TURSO_TOKEN"],
    )

    # Test 1: plain count
    try:
        r = await c.execute("SELECT COUNT(*) FROM etfs")
        print(f"ETF count: {r.rows[0][0]}")
    except Exception as e:
        print(f"COUNT failed: {e}")

    # Test 2: simple select
    try:
        r = await c.execute("SELECT ticker, name FROM etfs LIMIT 3")
        cols = [col if isinstance(col, str) else col.name for col in r.columns]
        for row in r.rows:
            print(dict(zip(cols, row)))
    except Exception as e:
        print(f"SELECT failed: {e}")

    # Test 3: parameterised query
    try:
        r = await c.execute("SELECT ticker FROM etfs WHERE ticker = ?", ["VFV"])
        print(f"VFV lookup: {r.rows}")
    except Exception as e:
        print(f"Parameterised query failed: {e}")

    # Test 4: ORDER BY with IS NULL
    try:
        r = await c.execute("SELECT ticker FROM etfs ORDER BY aum_cad IS NULL, aum_cad DESC LIMIT 3")
        print(f"ORDER BY IS NULL: {[row[0] for row in r.rows]}")
    except Exception as e:
        print(f"ORDER BY IS NULL failed: {e}")

    # Test 5: FTS5
    try:
        r = await c.execute("SELECT rowid FROM etfs_fts WHERE etfs_fts MATCH ?", ["vanguard*"])
        print(f"FTS5 match count: {len(r.rows)}")
    except Exception as e:
        print(f"FTS5 failed: {e}")

    await c.close()

asyncio.run(main())
