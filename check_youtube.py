import asyncio
from database.connection import get_db
from database.requests import get_youtube_channels

async def main():
    channels = await get_youtube_channels()
    print(f"📊 YouTube kanallari:")
    if channels:
        for ch in channels:
            print(f"ID: {ch[0]}, Channel ID: {ch[1]}, Name: {ch[2]}, URL: {ch[3]}")
    else:
        print("❌ Hech qanday YouTube kanali topilmadi!")

if __name__ == "__main__":
    asyncio.run(main())
