import asyncio
from database.connection import get_db

async def main():
    async with get_db() as db:
        # YouTube jadvallarini o'chirish
        await db.execute("DROP TABLE IF EXISTS youtube_subscriptions")
        await db.execute("DROP TABLE IF EXISTS youtube_channels")
        await db.commit()
        print("✅ YouTube jadvallari o'chirildi!")

if __name__ == "__main__":
    asyncio.run(main())
