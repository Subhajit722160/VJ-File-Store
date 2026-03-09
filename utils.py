# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import pytz
import random
import string
from datetime import datetime, timedelta
from config import SHORTLINK_API, SHORTLINK_URL
from shortzy import Shortzy

TOKENS = {}
# VERIFIED stores: {user_id: datetime_of_verification (IST)}
VERIFIED = {}


async def get_verify_shorted_link(link):
    shortzy = Shortzy(api_key=SHORTLINK_API, base_site=SHORTLINK_URL)
    link = await shortzy.convert(link)
    return link


async def check_token(bot, userid, token):
    user = await bot.get_users(userid)
    if user.id in TOKENS.keys():
        TKN = TOKENS[user.id]
        if token in TKN.keys():
            is_used = TKN[token]
            if is_used == True:
                return False
            else:
                return True
    return False


async def get_token(bot, userid, link):
    user = await bot.get_users(userid)
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=7))
    TOKENS[user.id] = {token: False}
    link = f"{link}verify-{user.id}-{token}"
    shortened_verify_url = await get_verify_shorted_link(link)
    return str(shortened_verify_url)


async def verify_user(bot, userid, token):
    """Mark user as verified. Verification is valid for exactly 24 hours from now."""
    user = await bot.get_users(userid)
    TOKENS[user.id] = {token: True}
    tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(tz)
    VERIFIED[user.id] = now


async def check_verification(bot, userid):
    """Returns True if user is verified and 24 hours have NOT yet passed."""
    user = await bot.get_users(userid)
    tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(tz)
    if user.id in VERIFIED:
        verified_at = VERIFIED[user.id]
        # Make sure verified_at is timezone-aware
        if verified_at.tzinfo is None:
            verified_at = tz.localize(verified_at)
        elapsed = now - verified_at
        if elapsed < timedelta(hours=24):
            return True
        else:
            # Expired — remove from dict
            del VERIFIED[user.id]
            return False
    return False


def get_verified_users_count():
    """Returns count of currently verified users (within 24h window)."""
    tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(tz)
    count = 0
    expired_ids = []
    for uid, verified_at in VERIFIED.items():
        if verified_at.tzinfo is None:
            verified_at = tz.localize(verified_at)
        elapsed = now - verified_at
        if elapsed < timedelta(hours=24):
            count += 1
        else:
            expired_ids.append(uid)
    # Clean up expired
    for uid in expired_ids:
        del VERIFIED[uid]
    return count


def get_user_verify_expiry(userid):
    """Returns remaining time string for a verified user, or None if not verified."""
    tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(tz)
    if userid in VERIFIED:
        verified_at = VERIFIED[userid]
        if verified_at.tzinfo is None:
            verified_at = tz.localize(verified_at)
        elapsed = now - verified_at
        remaining = timedelta(hours=24) - elapsed
        if remaining.total_seconds() > 0:
            hours, rem = divmod(int(remaining.total_seconds()), 3600)
            minutes = rem // 60
            return f"{hours}h {minutes}m"
    return None
