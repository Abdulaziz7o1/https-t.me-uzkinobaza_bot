import re
import logging
from database.connection import get_db

logger = logging.getLogger(__name__)

# 100% Telegram tomonidan tasdiqlangan rasmiy va premium animatsiyali emojilar ID bazasi
DEFAULT_CUSTOM_EMOJIS: dict[str, str] = {
    "🍿": "5371081166013078244",
    "🎬": "5375464961822695044",
    "👑": "5467406098367521267",
    "⭐": "5435957248314579621",
    "⭐️": "5435957248314579621",
    "💎": "5471952986970267163",
    "🔥": "5420315771991497307",
    "🚀": "5445284980978621387",
    "✅": "5427009714745517609",
    "❌": "5465665476971471368",
    "🎁": "5199749070830197566",
    "💰": "5375296873982604963",
    "📊": "5431577498364158238",
    "⚙️": "5199638831904596483",
    "⚙": "5199638831904596483",
    "🔍": "5188217332748527444",
    "⏳": "5451732530048802485",
    "📢": "5199850887324902331",
    "💬": "5465300082628763143",
    "🛡️": "5373173798633752502",
    "🛡": "5373173798633752502",
    "🏆": "5409008750893734809",
    "🎟️": "5377599075237502153",
    "🎟": "5377599075237502153",
    "🚨": "4983302733659374380",
    "🤖": "5372981976804366741",
    "📥": "5433811242135331842",
    "🎲": "5386782763288371963",
    "🎂": "5370999492914976897",
    "💳": "5280872069519654995",
    "🗑️": "5355021050637722984",
    "🗑": "5355021050637722984",
    "🔔": "5242628160297641831",
    "👍": "5469770542288478598",
    "👎": "5472309400536358507",
    "👤": "5373012449597335010",
    "👥": "5372926953978341366",
    "⚡": "5431449001532594346",
    "⚡️": "5431449001532594346",
    "🎉": "5436040291507247633",
    "❤️": "5449505950283078474",
    "🔒": "5199896439748043379",
    "✏️": "5199501302756812716",
    "✏": "5199501302756812716",
    "🖥️": "6032943812534340781",
    "🖥": "6032943812534340781",
    "⚠️": "5992308972328064706",
    "💤": "5215252253501301306",
    "🔄": "5226702984204797593",
    "♻️": "5226702984204797593",
    "♻": "5226702984204797593",
    "📈": "5197503331215361533",
    "📉": "5429518319243775957",
    "👋": "5472055112702629499",
    "➕": "5226945370684140473",
    "✨": "5472164874886846699",
    "📁": "5433653135799228968",
    "🔝": "5422354988103901774",
    "🗳": "5359741159566484212",
    "🗳️": "5359741159566484212",
    "🔗": "5375129357373165375",
    "💡": "5472146462362048818",
    "⏰": "5413704112220949842",
    "🕐": "5413704112220949842",
    "🕒": "5413704112220949842",
    "📬": "5350421256627838238",
    "📩": "5350421256627838238",
    "✉️": "5350421256627838238",
    "✉": "5350421256627838238",
    "📅": "5431897022456145283",
    "📆": "5431897022456145283",
    "💸": "5472030678633684592",
    "💵": "5472030678633684592",
    "🪙": "5379600444098093058",
    "🛠": "5199638831904596483",
    "🛠️": "5199638831904596483",
    "💾": "5433653135799228968",
    "🧹": "5355021050637722984",
    "🚫": "5465665476971471368",
    "🆘": "5377316857231450742",
    "❓": "5377316857231450742",
    "❗️": "5379748062124056162",
    "‼️": "5377498341074542641"
}

# Xotira keshi
_EMOJI_CACHE: dict[str, str] = dict(DEFAULT_CUSTOM_EMOJIS)
_CUSTOM_EMOJIS_ENABLED: bool = True
_EMOJI_REGEX: re.Pattern | None = None


def _compile_regex():
    global _EMOJI_REGEX
    if not _EMOJI_CACHE:
        _EMOJI_REGEX = None
        return
    # Uzunroq belgilarni oldin almashtirish uchun (masalan, ⭐️ oldin, keyin ⭐)
    sorted_keys = sorted(_EMOJI_CACHE.keys(), key=lambda x: len(x), reverse=True)
    escaped_keys = [re.escape(k) for k in sorted_keys]
    pattern = "(" + "|".join(escaped_keys) + ")"
    _EMOJI_REGEX = re.compile(pattern)


_compile_regex()


async def init_custom_emojis():
    """Bazada custom_emojis jadvalini yaratish va boshlang'ich ma'lumotlarni yuklash"""
    global _EMOJI_CACHE, _CUSTOM_EMOJIS_ENABLED
    try:
        async with get_db() as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS custom_emojis (
                    emoji_char TEXT PRIMARY KEY,
                    custom_emoji_id TEXT NOT NULL,
                    description TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            await db.commit()

            # Standart emojilarni bazaga kiritish yoki yangilash
            for char, cid in DEFAULT_CUSTOM_EMOJIS.items():
                await db.execute(
                    "INSERT INTO custom_emojis (emoji_char, custom_emoji_id) VALUES (?, ?) "
                    "ON CONFLICT(emoji_char) DO UPDATE SET custom_emoji_id = excluded.custom_emoji_id",
                    (char, cid)
                )
            await db.commit()

            # Bazadagi barcha emojilarni yuklash
            async with db.execute("SELECT emoji_char, custom_emoji_id FROM custom_emojis") as c:
                rows = await c.fetchall()
                for char, cid in rows:
                    _EMOJI_CACHE[char] = cid

            # Sozlama: yoqilganmi?
            async with db.execute("SELECT value FROM settings WHERE key = 'custom_emojis_enabled'") as c:
                row = await c.fetchone()
                if row:
                    _CUSTOM_EMOJIS_ENABLED = (row[0] == '1' or row[0].lower() == 'true')
                else:
                    _CUSTOM_EMOJIS_ENABLED = True

        _compile_regex()
        logger.info(f"Custom Emojilar muvaffaqiyatli yuklandi: {len(_EMOJI_CACHE)} ta emoji (Faol: {_CUSTOM_EMOJIS_ENABLED})")
    except Exception as e:
        logger.error(f"init_custom_emojis xatolik: {e}")


def is_custom_emojis_enabled() -> bool:
    return _CUSTOM_EMOJIS_ENABLED


async def set_custom_emojis_enabled(enabled: bool):
    global _CUSTOM_EMOJIS_ENABLED
    _CUSTOM_EMOJIS_ENABLED = enabled
    try:
        async with get_db() as db:
            val = '1' if enabled else '0'
            await db.execute(
                "INSERT INTO settings (key, value) VALUES ('custom_emojis_enabled', ?) ON CONFLICT(key) DO UPDATE SET value = ?",
                (val, val)
            )
            await db.commit()
    except Exception as e:
        logger.error(f"set_custom_emojis_enabled error: {e}")


async def save_custom_emoji(emoji_char: str, custom_emoji_id: str, description: str = None) -> bool:
    """Yangi custom emojini saqlash yoki yangilash"""
    global _EMOJI_CACHE
    try:
        async with get_db() as db:
            await db.execute(
                "INSERT INTO custom_emojis (emoji_char, custom_emoji_id, description) VALUES (?, ?, ?) "
                "ON CONFLICT(emoji_char) DO UPDATE SET custom_emoji_id = ?, description = ?",
                (emoji_char, custom_emoji_id, description, custom_emoji_id, description)
            )
            # variant selector bilan va siz bir xil saqlash
            base = emoji_char.replace('\ufe0f', '')
            if base != emoji_char:
                await db.execute(
                    "INSERT INTO custom_emojis (emoji_char, custom_emoji_id, description) VALUES (?, ?, ?) "
                    "ON CONFLICT(emoji_char) DO UPDATE SET custom_emoji_id = ?, description = ?",
                    (base, custom_emoji_id, description, custom_emoji_id, description)
                )
                _EMOJI_CACHE[base] = custom_emoji_id

            await db.commit()
            _EMOJI_CACHE[emoji_char] = custom_emoji_id
            _compile_regex()
            return True
    except Exception as e:
        logger.error(f"save_custom_emoji xatolik: {e}")
        return False


def get_all_custom_emojis() -> dict[str, str]:
    return dict(_EMOJI_CACHE)


def get_custom_emoji_id(emoji_char: str) -> str | None:
    """Berilgan emoji belgisi uchun custom_emoji_id qaytaradi"""
    if not emoji_char:
        return None
    return _EMOJI_CACHE.get(emoji_char) or _EMOJI_CACHE.get(emoji_char.replace('\ufe0f', ''))


def get_custom_emoji_id_for_text(text: str) -> str | None:
    """Matn ichidagi birinchi uchragan taniqli emojining custom_emoji_id sini qaytaradi"""
    if not text or not _EMOJI_REGEX:
        return None
    match = _EMOJI_REGEX.search(text)
    if match:
        ch = match.group(0)
        return _EMOJI_CACHE.get(ch) or _EMOJI_CACHE.get(ch.replace('\ufe0f', ''))
    return None


def apply_custom_emojis(text: str) -> str:
    """
    HTML matndagi emojilarni avtomatik <tg-emoji emoji-id="..."> formatiga o'tkazish.
    Mavjud HTML teglari (<b>, <a> va h.k.) hamda allaqachon <tg-emoji> ichida bo'lgan
    emojilarga tegmaydi.
    """
    if not text or not isinstance(text, str):
        return text

    if not _CUSTOM_EMOJIS_ENABLED or not _EMOJI_REGEX:
        return text

    # Matnni HTML teglari va oddiy matn bo'laklariga ajratish
    tokens = re.split(r'(<[^>]+>)', text)
    result = []
    in_tg_emoji = False

    for token in tokens:
        if not token:
            continue

        if token.startswith('<') and token.endswith('>'):
            tag_lower = token.lower()
            if tag_lower.startswith('<tg-emoji'):
                in_tg_emoji = True
            elif tag_lower == '</tg-emoji>':
                in_tg_emoji = False
            result.append(token)
        else:
            if in_tg_emoji:
                result.append(token)
            else:
                # Oddiy matndagi emojilarni almashtirish
                def _replace(match):
                    ch = match.group(0)
                    cid = _EMOJI_CACHE.get(ch)
                    if cid:
                        return f'<tg-emoji emoji-id="{cid}">{ch}</tg-emoji>'
                    return ch

                replaced = _EMOJI_REGEX.sub(_replace, token)
                result.append(replaced)

    return "".join(result)
