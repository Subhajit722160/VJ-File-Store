# Auto Approve Join Requests + /approveall (login with your own account)
# Put this file in the "plugins" folder as plugins/autoapprove.py. No other file needs changes.
#
# 1) New join requests are approved automatically by the bot (bot must be channel admin
#    with "Invite Users via Link" permission).
# 2) Old pending requests: Telegram does NOT allow bots to do this, so /approveall in the
#    bot's PRIVATE chat lets the user log in (phone + OTP) and the approving is done
#    with that user's account. The login is saved in your MongoDB, so it is asked only once.

import asyncio
import logging
import re
import time

import motor.motor_asyncio
from pyrogram import Client, filters, enums, errors, raw
from config import API_ID, API_HASH, DB_URI, DB_NAME

logger = logging.getLogger(__name__)

_sessions = motor.motor_asyncio.AsyncIOMotorClient(DB_URI)[DB_NAME]["approver_sessions"]

STATE = {}              # user_id -> {"step": ..., "client": ..., "phone": ..., "hash": ..., "ts": ...}
RUNNING = set()         # user_ids with an approve job running
STATE_TTL = 600         # login flow expires after 10 minutes of silence

PAGE_LIMIT = 100
CONCURRENCY = 10
PROGRESS_EVERY = 10

WARNING = (
    "<b>⚠️ Read first</b>\n"
    "• Use a <b>secondary account</b>, not your main one.\n"
    "• That account must be <b>Admin/Owner</b> of the channel with the <b>Invite Users</b> permission.\n"
    "• Your login is saved so you log in only once. Send /logout to remove it.\n"
    "• Telegram blocks codes sent as plain text, so type the OTP <b>with spaces</b>: <code>1 2 3 4 5</code>\n\n"
)


# ----------------------------------------------------------------------
# 1) AUTO APPROVE new join requests (bot account)
# ----------------------------------------------------------------------
@Client.on_chat_join_request()
async def auto_approve(client, join_request):
    chat_id = join_request.chat.id
    user_id = join_request.from_user.id
    for _ in range(3):
        try:
            await client.approve_chat_join_request(chat_id, user_id)
            return
        except errors.FloodWait as e:
            await asyncio.sleep(e.value + 1)
        except Exception as e:
            logger.info(f"AutoApprove skipped {user_id} in {chat_id}: {e}")
            return


# ----------------------------------------------------------------------
# helpers: saved login
# ----------------------------------------------------------------------
async def _get_session(uid):
    doc = await _sessions.find_one({"_id": uid})
    return doc["session"] if doc else None


async def _save_session(uid, session):
    await _sessions.update_one({"_id": uid}, {"$set": {"session": session}}, upsert=True)


async def _drop_session(uid):
    await _sessions.delete_one({"_id": uid})


async def _cleanup(uid):
    st = STATE.pop(uid, None)
    if st and st.get("client"):
        try:
            await st["client"].disconnect()
        except Exception:
            pass


def _user_client(uid, session):
    return Client(f"approver_{uid}", api_id=API_ID, api_hash=API_HASH,
                  session_string=session, in_memory=True, no_updates=True)


# ----------------------------------------------------------------------
# commands
# ----------------------------------------------------------------------
@Client.on_message(filters.command("approveall"))
async def approveall_cmd(client, message):
    # Not private chat -> tell them to use the bot's private chat
    if message.chat.type != enums.ChatType.PRIVATE:
        me = await client.get_me()
        return await client.send_message(
            message.chat.id,
            f"ℹ️ Bots can't approve old requests. Send /approveall to @{me.username} in private chat."
        )

    uid = message.from_user.id
    if uid in RUNNING:
        return await message.reply_text("⏳ Your approve job is already running. Please wait.")

    await _cleanup(uid)
    session = await _get_session(uid)
    if session:
        STATE[uid] = {"step": "chat", "ts": time.time()}
        return await message.reply_text(
            "✅ You are logged in.\n\n"
            "Send the <b>channel ID</b> (<code>-100xxxxxxxxxx</code>) or <b>@username</b>.\n"
            "/cancel to stop."
        )

    STATE[uid] = {"step": "phone", "ts": time.time()}
    await message.reply_text(
        WARNING +
        "📱 Send your phone number with country code, e.g. <code>+919876543210</code>\n"
        "/cancel to stop."
    )


@Client.on_message(filters.command("logout") & filters.private)
async def logout_cmd(client, message):
    uid = message.from_user.id
    await _cleanup(uid)
    session = await _get_session(uid)
    if not session:
        return await message.reply_text("ℹ️ No saved login found.")
    uc = _user_client(uid, session)
    try:
        await uc.start()
        await uc.log_out()
    except Exception:
        try:
            await uc.stop()
        except Exception:
            pass
    await _drop_session(uid)
    await message.reply_text("✅ Logged out. Your saved login was removed.")


# ----------------------------------------------------------------------
# login / input flow (runs before other handlers, only for users in a flow)
# ----------------------------------------------------------------------
async def _in_flow(_, __, m):
    if not m.from_user or not m.text:
        return False
    st = STATE.get(m.from_user.id)
    if not st:
        return False
    if time.time() - st["ts"] > STATE_TTL:
        await _cleanup(m.from_user.id)
        return False
    return True

in_flow = filters.create(_in_flow)


@Client.on_message(filters.private & filters.text & in_flow, group=-1)
async def flow_handler(client, message):
    text = message.text.strip()
    if text.startswith("/"):
        if text.split()[0].lower().split("@")[0] == "/cancel":
            await _cleanup(message.from_user.id)
            await message.reply_text("🚫 Cancelled.")
            message.stop_propagation()
        return  # other commands work normally
    try:
        await _flow(client, message, text)
    except Exception as e:
        logger.exception("approveall flow error")
        await _cleanup(message.from_user.id)
        await message.reply_text(f"❌ Error: <code>{e}</code>\nSend /approveall to try again.")
    message.stop_propagation()


async def _safe_delete(message):
    try:
        await message.delete()
    except Exception:
        pass


async def _flow(client, message, text):
    uid = message.from_user.id
    st = STATE[uid]
    st["ts"] = time.time()
    step = st["step"]

    # ---- phone number ----
    if step == "phone":
        phone = text.replace(" ", "")
        if not phone.startswith("+") or not phone[1:].isdigit():
            return await message.reply_text("❌ Send the number like <code>+919876543210</code>")
        uc = Client(f"login_{uid}", api_id=API_ID, api_hash=API_HASH, in_memory=True, no_updates=True)
        await uc.connect()
        try:
            sent = await uc.send_code(phone)
        except errors.PhoneNumberInvalid:
            await uc.disconnect()
            return await message.reply_text("❌ Invalid phone number. Try again.")
        except errors.FloodWait as e:
            await uc.disconnect()
            await _cleanup(uid)
            return await message.reply_text(f"⏳ Too many attempts. Try again after {e.value} seconds.")
        except Exception as e:
            await uc.disconnect()
            await _cleanup(uid)
            return await message.reply_text(f"❌ Could not send code: <code>{e}</code>\nSend /approveall to retry.")
        st.update(step="code", client=uc, phone=phone, hash=sent.phone_code_hash)
        return await message.reply_text(
            "📩 Code sent to your Telegram app.\n"
            "Send it <b>with spaces</b>, e.g. <code>1 2 3 4 5</code>"
        )

    # ---- OTP ----
    if step == "code":
        await _safe_delete(message)
        code = re.sub(r"\D", "", text)
        uc = st["client"]
        try:
            await uc.sign_in(st["phone"], st["hash"], code)
        except errors.SessionPasswordNeeded:
            st["step"] = "password"
            return await client.send_message(
                uid, "🔐 Two-step verification is on. Send your <b>password</b>.")
        except errors.PhoneCodeInvalid:
            return await client.send_message(uid, "❌ Wrong code. Send it again (with spaces).")
        except errors.PhoneCodeExpired:
            await _cleanup(uid)
            return await client.send_message(uid, "⏰ Code expired. Send /approveall to start again.")
        return await _login_done(client, uid)

    # ---- 2-step password ----
    if step == "password":
        await _safe_delete(message)
        try:
            await st["client"].check_password(text)
        except errors.PasswordHashInvalid:
            return await client.send_message(uid, "❌ Wrong password. Try again.")
        return await _login_done(client, uid)

    # ---- channel ----
    if step == "chat":
        session = await _get_session(uid)
        if not session:
            await _cleanup(uid)
            return await message.reply_text(
                "⚠️ No saved login found. Send /approveall and log in again.")
        STATE.pop(uid, None)
        status = await message.reply_text("⏳ Starting...")
        RUNNING.add(uid)
        asyncio.create_task(_run_job(client, uid, session, text, status))


async def _login_done(client, uid):
    st = STATE[uid]
    uc = st["client"]
    session = await uc.export_session_string()
    await _save_session(uid, session)
    try:
        await uc.disconnect()
    except Exception:
        pass
    st.update(step="chat", client=None, ts=time.time())
    await client.send_message(
        uid,
        "✅ Logged in!\n\nNow send the <b>channel ID</b> (<code>-100xxxxxxxxxx</code>) or <b>@username</b>.\n"
        "/cancel to stop."
    )


# ----------------------------------------------------------------------
# approve job (done with the user's own account)
# ----------------------------------------------------------------------
def _input_user(user_id, users_map):
    u = users_map.get(user_id)
    return raw.types.InputUser(user_id=user_id, access_hash=getattr(u, "access_hash", 0) or 0)


async def _approve_one(uc, peer, user_id, users_map, sem, stats):
    async with sem:
        u = users_map.get(user_id)
        if u is not None and getattr(u, "deleted", False):
            stats["skipped"] += 1           # deleted account -> skip
            return
        for _ in range(5):
            try:
                await uc.invoke(raw.functions.messages.HideChatJoinRequest(
                    peer=peer, user_id=_input_user(user_id, users_map), approved=True))
                stats["approved"] += 1
                return
            except errors.FloodWait as e:
                await asyncio.sleep(e.value + 1)
            except Exception as e:
                stats["skipped"] += 1       # cannot approve -> skip
                logger.info(f"ApproveAll skipped {user_id}: {e}")
                return
        stats["skipped"] += 1


async def _approve_all(uc, peer, status):
    stats = {"approved": 0, "skipped": 0}
    start = time.time()
    last_edit = 0

    # quick bulk approve first (works for user accounts)
    try:
        await uc.invoke(raw.functions.messages.HideAllChatJoinRequests(peer=peer, approved=True))
    except errors.FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except Exception as e:
        logger.info(f"Bulk approve not done: {e}")

    # then the rest one by one (failed ones are skipped)
    sem = asyncio.Semaphore(CONCURRENCY)
    offset_date, offset_user = 0, raw.types.InputUserEmpty()
    while True:
        try:
            res = await uc.invoke(raw.functions.messages.GetChatInviteImporters(
                peer=peer, requested=True, limit=PAGE_LIMIT,
                offset_date=offset_date, offset_user=offset_user, q=""))
        except errors.FloodWait as e:
            await asyncio.sleep(e.value + 1)
            continue
        if not res.importers:
            break
        users_map = {u.id: u for u in res.users}
        await asyncio.gather(*[_approve_one(uc, peer, i.user_id, users_map, sem, stats)
                               for i in res.importers])
        last = res.importers[-1]
        offset_date, offset_user = last.date, _input_user(last.user_id, users_map)

        if time.time() - last_edit >= PROGRESS_EVERY:
            last_edit = time.time()
            try:
                await status.edit_text(
                    f"<b>⏳ Approving...\n\n✅ Approved: <code>{stats['approved']}</code>\n"
                    f"⏭ Skipped: <code>{stats['skipped']}</code></b>")
            except errors.FloodWait as e:
                await asyncio.sleep(e.value + 1)
            except Exception:
                pass
        if len(res.importers) < PAGE_LIMIT:
            break
    return stats, int(time.time() - start)


async def _resolve_chat(uc, target):
    target = target.strip()
    target = re.sub(r"^https?://t\.me/", "", target).lstrip("@")
    ref = int(target) if re.fullmatch(r"-?\d+", target) else target
    try:
        return await uc.get_chat(ref)
    except (KeyError, errors.PeerIdInvalid):
        # peer not cached yet -> load the account's chats once, then retry
        async for _ in uc.get_dialogs():
            pass
        return await uc.get_chat(ref)


async def _run_job(client, uid, session, target, status):
    uc = _user_client(uid, session)
    try:
        try:
            await uc.start()
        except errors.Unauthorized:
            await _drop_session(uid)
            return await status.edit_text(
                "⚠️ Your login is no longer valid (logged out or session ended).\n"
                "Send /approveall and log in again.")

        try:
            chat = await _resolve_chat(uc, target)
        except Exception:
            return await status.edit_text(
                "❌ Channel not found. Check the ID/username, and make sure this account is "
                "a member/admin of it. Send /approveall to retry.")

        try:
            me = await uc.get_chat_member(chat.id, "me")
        except Exception:
            return await status.edit_text("❌ This account is not a member of that channel.")
        if me.status not in (enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR):
            return await status.edit_text(
                "❌ This account is not an admin there. Make it Admin with the "
                "<b>Invite Users</b> permission, then send /approveall again.")
        if me.privileges and not me.privileges.can_invite_users:
            return await status.edit_text(
                "❌ Admin has no <b>Invite Users</b> permission. Enable it, then send /approveall again.")

        peer = await uc.resolve_peer(chat.id)
        stats, took = await _approve_all(uc, peer, status)
        note = ""
        if stats["approved"] == 0 and stats["skipped"] == 0:
            note = "\n\nℹ️ No pending requests found."
        await status.edit_text(
            f"<b>✅ Done!\n\n✅ Approved: <code>{stats['approved']}</code>\n"
            f"⏭ Skipped (deleted/failed): <code>{stats['skipped']}</code>\n"
            f"⏱ Time: <code>{took}s</code></b>{note}")
    except errors.Unauthorized:
        await _drop_session(uid)
        await status.edit_text(
            "⚠️ Your login is no longer valid. Send /approveall and log in again.")
    except Exception as e:
        logger.exception("approve job failed")
        await status.edit_text(
            f"❌ Something went wrong: <code>{e}</code>\n"
            "If it keeps happening, send /logout, then /approveall and log in again.")
    finally:
        RUNNING.discard(uid)
        try:
            await uc.stop()
        except Exception:
            pass
