import pytz
from datetime import datetime, timedelta
import motor.motor_asyncio
from config import DB_NAME, DB_URI

DATABASE_NAME = DB_NAME
DATABASE_URI = DB_URI

IST = pytz.timezone('Asia/Kolkata')


def get_ist_today_str():
    """Returns today's date string in IST (YYYY-MM-DD)."""
    return datetime.now(IST).strftime('%Y-%m-%d')


class Database:

    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users
        self.grp = self.db.groups
        self.stats_col = self.db.bot_stats

    # ─────────────────────────────────────────────
    # Basic User Methods
    # ─────────────────────────────────────────────

    def new_user(self, id, name):
        return dict(
            id=id,
            name=name,
            ban_status=dict(
                is_banned=False,
                ban_reason="",
            ),
            premium=False,
            premium_expiry=None,
            daily_files=dict(date="", count=0),
            verified_at=None,   # IST datetime string — stored in DB, persists across restarts
        )

    def new_group(self, id, title):
        return dict(
            id=id,
            title=title,
            chat_status=dict(
                is_disabled=False,
                reason="",
            ),
        )

    async def add_user(self, id, name):
        user = self.new_user(id, name)
        await self.col.insert_one(user)

    async def is_user_exist(self, id):
        user = await self.col.find_one({'id': int(id)})
        return bool(user)

    async def total_users_count(self):
        count = await self.col.count_documents({})
        return count

    async def get_all_users(self):
        return self.col.find({})

    async def delete_user(self, user_id):
        await self.col.delete_many({'id': int(user_id)})

    # ─────────────────────────────────────────────
    # Verification Methods (MongoDB-backed)
    # ─────────────────────────────────────────────

    async def set_user_verified(self, user_id: int, verified_at: datetime):
        """
        Save verification timestamp to MongoDB.
        verified_at should be an IST-aware datetime.
        Stored as ISO string for easy retrieval.
        """
        verified_str = verified_at.strftime('%Y-%m-%d %H:%M:%S')
        await self.col.update_one(
            {'id': int(user_id)},
            {'$set': {'verified_at': verified_str}},
            upsert=True
        )

    async def get_user_verified_at(self, user_id: int):
        """
        Returns the IST datetime when user was last verified, or None.
        Bot restart safe — reads from MongoDB.
        """
        user = await self.col.find_one({'id': int(user_id)})
        if not user:
            return None
        verified_str = user.get('verified_at')
        if not verified_str:
            return None
        try:
            dt = datetime.strptime(verified_str, '%Y-%m-%d %H:%M:%S')
            return IST.localize(dt)
        except Exception:
            return None

    async def clear_user_verified(self, user_id: int):
        """Remove verification record for user (expired)."""
        await self.col.update_one(
            {'id': int(user_id)},
            {'$set': {'verified_at': None}}
        )

    async def count_verified_users(self) -> int:
        """
        Returns count of users whose verification is still valid (within 24h from verified_at).
        Checks all users with verified_at set.
        """
        now = datetime.now(IST)
        cutoff = now - timedelta(hours=24)
        cutoff_str = cutoff.strftime('%Y-%m-%d %H:%M:%S')
        # Users verified after cutoff are still active
        count = await self.col.count_documents({
            'verified_at': {'$gt': cutoff_str}
        })
        return count

    # ─────────────────────────────────────────────
    # Premium Methods
    # ─────────────────────────────────────────────

    async def add_premium(self, user_id: int, days: int):
        """Grant premium access for `days` days from now (IST)."""
        now = datetime.now(IST)
        expiry = now + timedelta(days=days)
        expiry_str = expiry.strftime('%Y-%m-%d %H:%M:%S')
        await self.col.update_one(
            {'id': int(user_id)},
            {'$set': {'premium': True, 'premium_expiry': expiry_str}},
            upsert=True
        )

    async def remove_premium(self, user_id: int):
        """Remove premium access."""
        await self.col.update_one(
            {'id': int(user_id)},
            {'$set': {'premium': False, 'premium_expiry': None}}
        )

    async def is_premium(self, user_id: int) -> bool:
        """Returns True if user has active premium."""
        user = await self.col.find_one({'id': int(user_id)})
        if not user:
            return False
        if not user.get('premium', False):
            return False
        expiry_str = user.get('premium_expiry')
        if not expiry_str:
            return False
        try:
            expiry = IST.localize(datetime.strptime(expiry_str, '%Y-%m-%d %H:%M:%S'))
        except Exception:
            return False
        now = datetime.now(IST)
        if now > expiry:
            await self.remove_premium(user_id)
            return False
        return True

    async def get_premium_expiry(self, user_id: int):
        """Returns premium expiry datetime string or None."""
        user = await self.col.find_one({'id': int(user_id)})
        if not user:
            return None
        return user.get('premium_expiry', None)

    async def total_premium_count(self) -> int:
        """Count users with active (non-expired) premium."""
        now_str = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
        count = await self.col.count_documents({
            'premium': True,
            'premium_expiry': {'$gt': now_str}
        })
        return count

    # ─────────────────────────────────────────────
    # Daily File Limit Methods
    # ─────────────────────────────────────────────

    async def get_daily_file_count(self, user_id: int) -> int:
        """Returns how many files this user has accessed today (IST date)."""
        today = get_ist_today_str()
        user = await self.col.find_one({'id': int(user_id)})
        if not user:
            return 0
        daily = user.get('daily_files', {})
        if daily.get('date') == today:
            return daily.get('count', 0)
        return 0

    async def increment_daily_file_count(self, user_id: int):
        """Increment today's file count for this user (IST date)."""
        today = get_ist_today_str()
        user = await self.col.find_one({'id': int(user_id)})
        if not user:
            return
        daily = user.get('daily_files', {})
        if daily.get('date') == today:
            new_count = daily.get('count', 0) + 1
        else:
            new_count = 1
        await self.col.update_one(
            {'id': int(user_id)},
            {'$set': {'daily_files': {'date': today, 'count': new_count}}}
        )

    # ─────────────────────────────────────────────
    # File Stats Methods
    # ─────────────────────────────────────────────

    async def increment_total_file_count(self):
        """Called when a new file link is generated."""
        today = get_ist_today_str()
        stat = await self.stats_col.find_one({'_id': 'file_stats'})
        if not stat:
            await self.stats_col.insert_one({
                '_id': 'file_stats',
                'total': 1,
                'today_date': today,
                'today_count': 1
            })
        else:
            new_total = stat.get('total', 0) + 1
            if stat.get('today_date') == today:
                new_today = stat.get('today_count', 0) + 1
            else:
                new_today = 1
            await self.stats_col.update_one(
                {'_id': 'file_stats'},
                {'$set': {
                    'total': new_total,
                    'today_date': today,
                    'today_count': new_today
                }}
            )

    async def get_file_stats(self) -> dict:
        """Returns {'total': int, 'today_count': int}."""
        today = get_ist_today_str()
        stat = await self.stats_col.find_one({'_id': 'file_stats'})
        if not stat:
            return {'total': 0, 'today_count': 0}
        today_count = stat.get('today_count', 0) if stat.get('today_date') == today else 0
        return {
            'total': stat.get('total', 0),
            'today_count': today_count
        }


db = Database(DATABASE_URI, DATABASE_NAME)
