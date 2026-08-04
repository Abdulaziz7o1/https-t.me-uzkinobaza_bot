import asyncio
from database.connection import get_db

async def main():
    async with get_db() as db:
        # YouTube kanal qo'shish
        channel_id = "UCq-Fj5jknLsUf-MWSy4_brA"  # Misol YouTube kanal ID
        channel_name = "Test YouTube Kanal"  # Kanal nomi
        channel_url = f"https://www.youtube.com/channel/{channel_id}"

        try:
            await db.execute(
                "INSERT INTO youtube_channels (channel_id, channel_name, channel_url) VALUES (?, ?, ?)",
                (channel_id, channel_name, channel_url)
            )
            await db.commit()
            print(f"✅ YouTube kanal muvaffaqiyatli qo'shildi!")
            print(f"📋 Kanal ID: {channel_id}")
            print(f"📋 Kanal nomi: {channel_name}")
            print(f"📋 Kanal URL: {channel_url}")
        except Exception as e:
            print(f"❌ Xatolik: {e}")

if __name__ == "__main__":
    asyncio.run(main())
