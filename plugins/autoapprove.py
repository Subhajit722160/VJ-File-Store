# Auto Approve Join Requests + /approveall
# Put this file inside the "plugins" folder (plugins/autoapprove.py).
# bot.py already loads every file in plugins/*.py, so nothing else needs to change.
#
# Requirement: the bot must be an ADMIN in the channel/group with the
# "Invite Users via Link" (Add Members) permission.

import asyncio
import logging
import time

from pyrogram import Client, filters, enums, raw
from pyrogram.errors import FloodWait, RPCError
from config import ADMINS

logger = logging.getLogger(__name__)

# Chats where /approveall is currently running (prevents running twice at once)
RUNNING = set()

PAGE_LIMIT = 100        # how many pending requests to fetch per page (Telegram max = 100)
CONCURRENCY = 10        # how many approvals to do in parallel
PROGRESS_EVERY = 10     # seconds between progress message edits


# ----------------------------------------------------------------------
# 1) AUTO APPROVE: every new join request is approved immediately
# ----------------------------------------------------------------------
@Client.on_chat_join_request()
async def auto_approve(client, join_request):
    chat_id = join_request.chat.id
    user_id = join_request.from_user.id
    for _ in range(3):
        try:
            await client.approve_chat_join_request(chat_id, user_id)
            return
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
        except Exception as e:
            # deleted account / already approved / user in too many channels etc. -> skip
            logger.info(f"AutoApprove skipped {user_id} in {chat_id}: {e}")
            return


# ----------------------------------------------------------------------
# 2) /approveall : approve ALL old pending requests (even 40,000+)
# ----------------------------------------------------------------------
async def _is_allowed(message):
    """Channel posts can only be made by channel admins, so they are allowed.
    In groups/private chat, only bot ADMINS can use it."""
    if message.chat.type == enums.ChatType.CHANNEL:
        return True
    if message.from_user and message.from_user.id in ADMINS:
        return True
    return False


def _input_user(user_id, users_map):
    u = users_map.get(user_id)
    access_hash = getattr(u, "access_hash", 0) or 0
    return raw.types.InputUser(user_id=user_id, access_hash=access_hash)


async def _approve_one(client, peer, user_id, users_map, sem, stats):
    async with sem:
        u = users_map.get(user_id)
        # Deleted account -> cannot be approved, skip
        if u is not None and getattr(u, "deleted", False):
            stats["skipped"] += 1
            return
        for _ in range(5):
            try:
                await client.invoke(
                    raw.functions.messages.HideChatJoinRequest(
                        peer=peer,
                        user_id=_input_user(user_id, users_map),
                        approved=True,
                    )
                )
                stats["approved"] += 1
                return
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
            except RPCError as e:
                # USER_CHANNELS_TOO_MUCH, HIDE_REQUESTER_MISSING, USER_ID_INVALID,
                # PEER_ID_INVALID ... -> cannot approve, skip and move on
                stats["skipped"] += 1
                logger.info(f"ApproveAll skipped {user_id}: {e}")
                return
            except Exception as e:
                stats["skipped"] += 1
                logger.info(f"ApproveAll skipped {user_id}: {e}")
                return
        stats["skipped"] += 1


async def _fast_approve_all(client, peer):
    """Try Telegram's one-shot 'approve all' first (very fast). Ignore if not allowed."""
    try:
        await client.invoke(
            raw.functions.messages.HideAllChatJoinRequests(peer=peer, approved=True)
        )
        return True
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
        return "FloodWait"
    except Exception as e:
        logger.info(f"Fast approve-all not available: {e}")
        return f"{type(e).__name__}: {e}"
    return None


async def approve_all_requests(client, chat_id, status_msg):
    peer = await client.resolve_peer(chat_id)
    stats = {"approved": 0, "skipped": 0}
    start = time.time()
    last_edit = 0

    # Step 1: quick bulk approve (if Telegram allows it for bots)
    stats["fast_error"] = await _fast_approve_all(client, peer)
    stats["fetch_error"] = None
    stats["pages"] = 0

    # Step 2: go through the remaining requests one by one,
    # page by page. Failed ones are skipped, never retried forever.
    sem = asyncio.Semaphore(CONCURRENCY)
    offset_date = 0
    offset_user = raw.types.InputUserEmpty()

    while True:
        try:
            res = await client.invoke(
                raw.functions.messages.GetChatInviteImporters(
                    peer=peer,
                    requested=True,
                    limit=PAGE_LIMIT,
                    offset_date=offset_date,
                    offset_user=offset_user,
                    q="",
                )
            )
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
            continue
        except Exception as e:
            logger.error(f"ApproveAll fetch error: {e}")
            stats["fetch_error"] = f"{type(e).__name__}: {e}"
            break

        importers = res.importers
        if not importers:
            break
        stats["pages"] += 1

        users_map = {u.id: u for u in res.users}
        await asyncio.gather(
            *[_approve_one(client, peer, i.user_id, users_map, sem, stats) for i in importers]
        )

        # move the page cursor to the last request of this page
        last = importers[-1]
        offset_date = last.date
        offset_user = _input_user(last.user_id, users_map)

        if time.time() - last_edit >= PROGRESS_EVERY:
            last_edit = time.time()
            try:
                await status_msg.edit_text(
                    f"<b>⏳ ᴀᴘᴘʀᴏᴠɪɴɢ...\n\n"
                    f"✅ Approved: <code>{stats['approved']}</code>\n"
                    f"⏭ Skipped: <code>{stats['skipped']}</code></b>"
                )
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
            except Exception:
                pass

        if len(importers) < PAGE_LIMIT:
            break

    took = int(time.time() - start)
    return stats, took


@Client.on_message(filters.command("approveall"))
async def approve_all_cmd(client, message):
    if not await _is_allowed(message):
        return

    # chat to work on: the current chat, or "/approveall -100xxxxxxxxxx" in private by an admin
    chat_id = message.chat.id
    if message.chat.type == enums.ChatType.PRIVATE:
        if len(message.command) < 2:
            return await message.reply_text(
                "<b>Usage:</b> <code>/approveall -100xxxxxxxxxx</code>\n"
                "Or send <code>/approveall</code> inside the channel."
            )
        try:
            chat_id = int(message.command[1])
        except ValueError:
            return await message.reply_text("<b>Invalid chat id.</b>")

    if chat_id in RUNNING:
        return await message.reply_text("<b>⚠️ Already running for this chat, please wait.</b>")

    RUNNING.add(chat_id)
    status = await client.send_message(
        message.chat.id, "<b>⏳ Starting to approve all pending join requests...</b>"
    )
    try:
        stats, took = await approve_all_requests(client, chat_id, status)
        await status.edit_text(
            f"<b>✅ ᴅᴏɴᴇ!\n\n"
            f"✅ Approved: <code>{stats['approved']}</code>\n"
            f"⏭ Skipped (deleted/blocked/failed): <code>{stats['skipped']}</code>\n"
            f"⏱ Time: <code>{took}s</code></b>"
            + (f"\n\n<b>Bulk approve error:</b> <code>{stats['fast_error']}</code>" if stats.get("fast_error") else "")
            + (f"\n\n<b>Fetch error:</b> <code>{stats['fetch_error']}</code>" if stats.get("fetch_error") else "")
            + ("\n\n<b>Telegram returned 0 pending requests to the bot.</b>" if stats.get("pages") == 0 and not stats.get("fetch_error") else "")
        )
    except Exception as e:
        logger.exception("approveall failed")
        await status.edit_text(
            f"<b>❌ Error:</b> <code>{e}</code>\n\n"
            "Make sure the bot is an admin with the <b>Invite Users</b> permission."
        )
    finally:
        RUNNING.discard(chat_id)
