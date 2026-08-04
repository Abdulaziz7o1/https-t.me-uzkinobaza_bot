import aiosqlite
import asyncio

async def check_columns():
    async with aiosqlite.connect("kino_bot.db") as db:
        async with db.execute("PRAGMA table_info(users)") as cursor:
            columns = await cursor.fetchall()
            print("Users table columns:")
            for col in columns:
                print(f"  {col[1]} ({col[2]})")

asyncio.run(check_columns())
