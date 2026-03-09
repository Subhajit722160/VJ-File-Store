# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import pytz
import random
import string
from datetime import datetime, timedelta
from config import SHORTLINK_API, SHORTLINK_URL
from shortzy import Shortzy

# TOKENS dict stays in RAM — it's only used for one-time token validation
# (short-lived, no need to persist across restarts)
TOKENS = {}

IST = pytz.timezone('Asia/Kolkata')


async def get_verify_shorted_link(link):
    shortzy = Shortzy(api_key=SHORTLINK_API, base_site=SHORTLINK_URL)
    link = await shortzy.convert(link)
    return link


async def check_token(bot, userid, token):
    user = await bot.get_users(userid)
    if user.id in TOKENS:
        TKN = TOKENS[user.id]
        if token in TKN:
            return not TKN[token]  # True if not yet used
    return False


async def get_token(bot, userid, link):
    user = await bot.get_users(userid)
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=7))
    TOKENS[user.id] = {token: False}
    link = f"{link}verify-{user.id}-{token}"
    shortened_verify_url = await get_verify_shorted_link(link)
    return str(shortened_verify_url)


async def verify_user(bot, userid, token):
    """
    Mark user as verified. Saves verification timestamp to MongoDB.
    Valid for exactly 24 hours from now (IST).
    """
    from plugins.dbusers import db
    user = await bot.get_users(userid)
    TOKENS[user.id] = {token: True}
    now = datetime.now(IST)
    await db.set_user_verified(user.id, now)


async def check_verification(bot, userid):
    """
    Returns True if user is verified and 24 hours have NOT yet passed.
    Reads from MongoDB — persists across bot restarts.
    """
    from plugins.dbusers import db
    user = await bot.get_users(userid)
    verified_at = await db.get_user_verified_at(user.id)
    if not verified_at:
        return False
    now = datetime.now(IST)
    if verified_at.tzinfo is None:
        verified_at = IST.localize(verified_at)
    elapsed = now - verified_at
    if elapsed < timedelta(hours=24):
        return True
    else:
        # Expired — clear from DB
        await db.clear_user_verified(user.id)
        return False


def get_verified_users_count():
    """
    Returns count of currently verified users (within 24h).
    Calls db synchronously via a cached count — use get_verified_users_count_async instead.
    """
    # Use the async version in commands.py
    return 0  # placeholder — use get_verified_users_count_async below


async def get_verified_users_count_async():
    """Returns count of users whose verification has not yet expired (within 24h)."""
    from plugins.dbusers import db
    return await db.count_verified_users()


async def get_user_verify_expiry(userid):
    """Returns remaining time string for a verified user, or None if not verified."""
    from plugins.dbusers import db
    verified_at = await db.get_user_verified_at(userid)
    if not verified_at:
        return None
    now = datetime.now(IST)
    if verified_at.tzinfo is None:
        verified_at = IST.localize(verified_at)
    remaining = timedelta(hours=24) - (now - verified_at)
    if remaining.total_seconds() > 0:
        hours, rem = divmod(int(remaining.total_seconds()), 3600)
        minutes = rem // 60
        return f"{hours}h {minutes}m"
    return None
