import asyncio
from database.connection import get_db

async def main():
    async with get_db() as db:
        # Noto'g'ri YouTube linkini o'chirish
        await db.execute("DELETE FROM sponsor_channels WHERE channel_id = ?", ("https://youtube.com/@MadridPrimee",))
        await db.commit()
        print("✅ Noto'g'ri YouTube linki sponsor kanallaridan o'chirildi!")

if __name__ == "__main__":
    asyncio.run(main())
