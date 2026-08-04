import asyncio
from database.connection import get_db
from database.requests import get_stats

async def main():
    stats = await get_stats()
    print(f"📊 Bot statistikasi:")
    print(f"👥 Jami a'zolar: {stats['users']}")
    print(f"🚫 Bloklanganlar: {stats['banned']}")
    print(f"🎬 Kinolar soni: {stats['movies']}")
    print(f"✅ Faol a'zolar: {stats['users'] - stats['banned']}")
    
    users_count = stats['users']
    if users_count < 1000:
        category = "Kichik bot (< 1000 a'zo)"
        income = "$10-50/oy"
    elif users_count < 5000:
        category = "Kichik bot (1000-5000 a'zo)"
        income = "$50-200/oy"
    elif users_count < 20000:
        category = "O'rta bot (5000-20000 a'zo)"
        income = "$200-1000/oy"
    else:
        category = "Katta bot (20000+ a'zo)"
        income = "$1000+/oy"
    
    print(f"\n📈 Kategoriya: {category}")
    print(f"💰 Taxminiy daromad: {income}")

if __name__ == "__main__":
    asyncio.run(main())
