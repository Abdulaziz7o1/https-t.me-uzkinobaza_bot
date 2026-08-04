import asyncio
from database.connection import get_db

async def main():
    async with get_db() as db:
        # Check youtube_channels table
        async with db.execute("SELECT * FROM youtube_channels") as cursor:
            channels = await cursor.fetchall()
            print(f"📊 YouTube kanallari (direct DB):")
            if channels:
                for ch in channels:
                    print(f"ID: {ch[0]}, Channel ID: {ch[1]}, Name: {ch[2]}, URL: {ch[3]}")
            else:
                print("❌ Hech qanday YouTube kanali topilmadi!")

        # Check if table exists
        async with db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='youtube_channels'") as cursor:
            table_exists = await cursor.fetchone()
            print(f"\n📋 Jadval mavjudmi: {'Ha ✅' if table_exists else 'Yo\'q ❌'}")

if __name__ == "__main__":
    asyncio.run(main())
