from database.connection import get_db
import asyncio

async def main():
    async with get_db() as db:
        # Check sponsor_channels table
        async with db.execute("SELECT * FROM sponsor_channels") as cursor:
            channels = await cursor.fetchall()
            print("📊 Sponsor kanallari (Telegram):")
            if channels:
                for ch in channels:
                    print(f"ID: {ch[0]}, Channel ID: {ch[1]}, Name: {ch[2]}")
            else:
                print("❌ Hech qanday sponsor kanali topilmadi!")

if __name__ == "__main__":
    asyncio.run(main())
