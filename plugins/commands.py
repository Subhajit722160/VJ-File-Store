# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import os
import logging
import random
import asyncio
from validators import domain
from Script import script
from plugins.dbusers import db
from pyrogram import Client, filters, enums
from plugins.users_api import get_user, update_user_info
from plugins.database import get_file_details
from pyrogram.errors import ChatAdminRequired, FloodWait, UserNotParticipant
from pyrogram.types import *
from utils import verify_user, check_token, check_verification, get_token, get_verified_users_count_async, get_user_verify_expiry
from config import *
import re
import json
import base64
import pytz
from datetime import datetime, timedelta
from urllib.parse import quote_plus
from TechVJ.utils.file_properties import get_name, get_hash, get_media_file_size

logger = logging.getLogger(__name__)

BATCH_FILES = {}
IST = pytz.timezone('Asia/Kolkata')


def get_size(size):
    """Get size in readable format"""
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])


def format_time_remaining(seconds):
    """Format seconds into Xh Ym string."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m"


async def check_force_subscribe(client, message):
    """
    Check if user is subscribed to ALL force-sub channels.
    Returns list of channel IDs the user has NOT joined yet.
    Returns [] if all joined or FORCE_SUB_MODE is off.
    """
    if not FORCE_SUB_MODE or not FORCE_SUB_CHANNELS:
        return []

    not_joined = []
    for channel_id in FORCE_SUB_CHANNELS:
        try:
            member = await client.get_chat_member(channel_id, message.from_user.id)
            if member.status == enums.ChatMemberStatus.BANNED:
                await message.reply_text("<b>Sorry, you are banned from using this bot.</b>")
                return None  # None means banned
        except UserNotParticipant:
            not_joined.append(channel_id)
        except Exception as e:
            logger.error(f"Force Sub Error for channel {channel_id}: {e}")

    return not_joined


async def send_force_sub_message(client, message, not_joined_channels, start_param=""):
    """Send force subscribe message showing only unjoined channels."""
    buttons = []
    for channel_id in not_joined_channels:
        try:
            invite_link = await client.create_chat_invite_link(channel_id)
            try:
                chat = await client.get_chat(channel_id)
                channel_name = chat.title or f"Channel"
            except Exception:
                channel_name = "Channel"
            buttons.append([InlineKeyboardButton(f"📢 Join {channel_name}", url=invite_link.invite_link)])
        except Exception as e:
            logger.error(f"Could not create invite for {channel_id}: {e}")

    if start_param:
        buttons.append([InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{BOT_USERNAME}?start={start_param}")])
    else:
        buttons.append([InlineKeyboardButton("🔄 Retry", url=f"https://t.me/{BOT_USERNAME}?start=retry")])

    await message.reply_text(
        text="<b>⚠️ You must join our channel(s) to use this bot!\n\nPlease join all channels below and click Retry.</b>",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def handle_file_access(client, message, file_id, f_caption, pre="", is_batch=False):
    """
    Central function to handle file access with daily limit + verification + premium checks.
    Returns True if file was sent, False if blocked.
    """
    user_id = message.from_user.id
    username = (await client.get_me()).username

    # 1. Premium users get direct access
    if await db.is_premium(user_id):
        return True  # Caller sends the file

    # 2. Verified users (within 24h) get unlimited access
    if VERIFY_MODE and await check_verification(client, user_id):
        return True

    # 3. Daily free file limit check
    if DAILY_FILE_LIMIT_MODE:
        count = await db.get_daily_file_count(user_id)
        if count < DAILY_FILE_LIMIT:
            # Within free limit — allow
            await db.increment_daily_file_count(user_id)
            return True
        else:
            # Limit reached
            now = datetime.now(IST)
            # Time until IST midnight (next day reset)
            midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            remaining_seconds = (midnight - now).total_seconds()
            time_str = format_time_remaining(remaining_seconds)

            btn = []
            if VERIFY_MODE:
                btn.append([
                    InlineKeyboardButton(
                        "🔓 Verify Now - Unlimited Access",
                        url=await get_token(client, user_id, f"https://telegram.me/{username}?start=")
                    )
                ])
                btn.append([
                    InlineKeyboardButton("❓ How To Verify", url=VERIFY_TUTORIAL)
                ])
            btn.append([
                InlineKeyboardButton("👑 Buy Premium - Unlimited Access", callback_data="show_plan")
            ])

            await message.reply_text(
                text=(
                    f"<b>⚠️ Daily Free File Limit Reached!\n\n"
                    f"You can get <b>{DAILY_FILE_LIMIT}</b> free file(s) per day.\n"
                    f"⏳ Wait for next file: <b>{time_str}</b>\n\n"
                    f"🔓 For Unlimited files:\n"
                    f"• Verify (Free)\n"
                    f"• Or Buy Premium\n\n"
                    f"👇 Check /plan for Premium details</b>"
                ),
                reply_markup=InlineKeyboardMarkup(btn),
                protect_content=True
            )
            return False
    else:
        # DAILY_FILE_LIMIT_MODE is off — use verify mode
        if VERIFY_MODE:
            if not await check_verification(client, user_id):
                btn = [
                    [InlineKeyboardButton(
                        "🔓 Verify Now - Unlimited Access",
                        url=await get_token(client, user_id, f"https://telegram.me/{username}?start=")
                    )],
                    [InlineKeyboardButton("❓ How To Verify", url=VERIFY_TUTORIAL)],
                    [InlineKeyboardButton("👑 Buy Premium - Unlimited Access", callback_data="show_plan")]
                ]
                await message.reply_text(
                    text="<b>🔒 You are not verified!\nKindly verify to access this file.</b>",
                    protect_content=True,
                    reply_markup=InlineKeyboardMarkup(btn)
                )
                return False
        return True


# ─────────────────────────────────────────────────────────────
# /start Command
# ─────────────────────────────────────────────────────────────

@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, script.LOG_TEXT.format(message.from_user.id, message.from_user.mention))

    # --- Force Subscribe Logic (Multiple Channels) ---
    if FORCE_SUB_MODE and FORCE_SUB_CHANNELS:
        start_param = message.command[1] if len(message.command) > 1 else ""
        not_joined = await check_force_subscribe(client, message)
        if not_joined is None:
            return  # Banned
        if not_joined:
            await send_force_sub_message(client, message, not_joined, start_param)
            return
    # --- Force Subscribe End ---

    username = (await client.get_me()).username
    if len(message.command) != 2:
        buttons = [[
            InlineKeyboardButton('💝 sᴜʙsᴄʀɪʙᴇ ᴍʏ ʏᴏᴜᴛᴜʙᴇ ᴄʜᴀɴɴᴇʟ', url='https://t.me/SGBACKUP')
        ], [
            InlineKeyboardButton('🔍 sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ', url='https://t.me/SGBACKUP'),
            InlineKeyboardButton('🤖 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ', url='https://t.me/SGBACKUP')
        ], [
            InlineKeyboardButton('💁‍♀️ ʜᴇʟᴘ', callback_data='help'),
            InlineKeyboardButton('😊 ᴀʙᴏᴜᴛ', callback_data='about')
        ]]
        if CLONE_MODE:
            buttons.append([InlineKeyboardButton('🤖 ᴄʀᴇᴀᴛᴇ ʏᴏᴜʀ ᴏᴡɴ ᴄʟᴏɴᴇ ʙᴏᴛ', callback_data='clone')])
        reply_markup = InlineKeyboardMarkup(buttons)
        me2 = (await client.get_me()).mention
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=script.START_TXT.format(message.from_user.mention, me2),
            reply_markup=reply_markup
        )
        return

    data = message.command[1]
    try:
        pre, file_id = data.split('_', 1)
    except Exception:
        file_id = data
        pre = ""

    # --- Verify Token Handler ---
    if data.split("-", 1)[0] == "verify":
        userid = data.split("-", 2)[1]
        token = data.split("-", 3)[2]
        if str(message.from_user.id) != str(userid):
            return await message.reply_text(
                text="<b>Invalid link or Expired link!</b>",
                protect_content=True
            )
        is_valid = await check_token(client, userid, token)
        if is_valid:
            await verify_user(client, userid, token)
            await message.reply_text(
                text=(
                    f"<b>✅ Hey {message.from_user.mention}, you are successfully verified!\n\n"
                    f"You now have <b>unlimited access</b> for 24 hours.\n"
                    f"Your verification expires in 24 hours from now.</b>"
                ),
                protect_content=True
            )
        else:
            return await message.reply_text(
                text="<b>Invalid link or Expired link!</b>",
                protect_content=True
            )
        return

    # --- BATCH Handler ---
    elif data.split("-", 1)[0] == "BATCH":
        user_id = message.from_user.id
        username = (await client.get_me()).username

        # Premium users → full unlimited access
        is_prem = await db.is_premium(user_id)
        # Verified users → full unlimited access
        is_verified = VERIFY_MODE and await check_verification(client, user_id)

        # If NOT premium and NOT verified, check daily limit / verify requirement
        if not is_prem and not is_verified:
            if not DAILY_FILE_LIMIT_MODE:
                # No free limit mode → must verify or buy premium
                if VERIFY_MODE:
                    btn = [
                        [InlineKeyboardButton(
                            "🔓 Verify Now - Unlimited Access",
                            url=await get_token(client, user_id, f"https://telegram.me/{username}?start=")
                        )],
                        [InlineKeyboardButton("❓ How To Verify", url=VERIFY_TUTORIAL)],
                        [InlineKeyboardButton("👑 Buy Premium - Unlimited Access", callback_data="show_plan")]
                    ]
                    await message.reply_text(
                        text="<b>🔒 You are not verified!\nKindly verify to access this file.</b>",
                        protect_content=True,
                        reply_markup=InlineKeyboardMarkup(btn)
                    )
                    return

        sts = await message.reply("<b>🔺 Please wait...</b>")
        file_id = data.split("-", 1)[1]
        msgs = BATCH_FILES.get(file_id)
        if not msgs:
            file = await client.download_media(file_id)
            try:
                with open(file) as file_data:
                    msgs = json.loads(file_data.read())
            except Exception:
                await sts.edit("<b>❌ Failed to load batch file.</b>")
                return await client.send_message(LOG_CHANNEL, "UNABLE TO OPEN FILE.")
            os.remove(file)
            BATCH_FILES[file_id] = msgs

        total_files = len(msgs)

        # Determine how many files this user can receive right now
        if is_prem or is_verified:
            # Unlimited
            allowed_count = total_files
        elif DAILY_FILE_LIMIT_MODE:
            already_used = await db.get_daily_file_count(user_id)
            remaining_quota = max(0, DAILY_FILE_LIMIT - already_used)
            allowed_count = min(remaining_quota, total_files)
        else:
            allowed_count = total_files

        if allowed_count == 0:
            # Limit already hit before batch even starts
            now = datetime.now(IST)
            midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            time_str = format_time_remaining((midnight - now).total_seconds())
            btn = []
            if VERIFY_MODE:
                btn.append([InlineKeyboardButton(
                    "🔓 Verify Now - Unlimited Access",
                    url=await get_token(client, user_id, f"https://telegram.me/{username}?start=")
                )])
                btn.append([InlineKeyboardButton("❓ How To Verify", url=VERIFY_TUTORIAL)])
            btn.append([InlineKeyboardButton("👑 Buy Premium - Unlimited Access", callback_data="show_plan")])
            await sts.edit(
                f"<b>⚠️ Daily Free File Limit Reached!\n\n"
                f"You can get <b>{DAILY_FILE_LIMIT}</b> free file(s) per day.\n"
                f"⏳ Next reset in: <b>{time_str}</b>\n\n"
                f"📦 This batch contains <b>{total_files}</b> file(s).\n\n"
                f"🔓 To get all files:\n"
                f"• Verify for free (24h unlimited access)\n"
                f"• Or buy Premium for permanent access\n\n"
                f"👇 Check /plan for Premium details</b>",
                reply_markup=InlineKeyboardMarkup(btn)
            )
            return

        filesarr = []
        sent_count = 0
        for msg in msgs:
            # Stop sending once allowed quota is exhausted (for free users)
            if not (is_prem or is_verified) and DAILY_FILE_LIMIT_MODE and sent_count >= allowed_count:
                break

            title = msg.get("title")
            size = get_size(int(msg.get("size", 0)))
            f_caption = msg.get("caption", "")
            if BATCH_FILE_CAPTION:
                try:
                    f_caption = BATCH_FILE_CAPTION.format(
                        file_name='' if title is None else title,
                        file_size='' if size is None else size,
                        file_caption='' if f_caption is None else f_caption
                    )
                except Exception as e:
                    logger.exception(e)
            if f_caption is None:
                f_caption = f"{title}"
            try:
                if STREAM_MODE:
                    username_mention = message.from_user.mention
                    log_msg = await client.send_cached_media(
                        chat_id=LOG_CHANNEL,
                        file_id=msg.get("file_id"),
                    )
                    fileName = get_name(log_msg)
                    stream = f"{URL}watch/{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
                    download = f"{URL}{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
                    await log_msg.reply_text(
                        text=f"•• ʟɪɴᴋ ɢᴇɴᴇʀᴀᴛᴇᴅ ꜰᴏʀ ɪᴅ #{user_id} \n•• ᴜꜱᴇʀɴᴀᴍᴇ : {username_mention} \n\n•• ᖴᎥᒪᗴ Nᗩᗰᗴ : {fileName}",
                        quote=True,
                        disable_web_page_preview=True,
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("🚀 Fast Download 🚀", url=download),
                            InlineKeyboardButton('🖥️ Watch online 🖥️', url=stream)
                        ]])
                    )
                    button = [[
                        InlineKeyboardButton("🚀 Fast Download 🚀", url=download),
                        InlineKeyboardButton('🖥️ Watch online 🖥️', url=stream)
                    ], [
                        InlineKeyboardButton("• ᴡᴀᴛᴄʜ ɪɴ ᴡᴇʙ ᴀᴘᴘ •", web_app=WebAppInfo(url=stream))
                    ]]
                    reply_markup = InlineKeyboardMarkup(button)
                else:
                    reply_markup = None

                msg_sent = await client.send_cached_media(
                    chat_id=message.from_user.id,
                    file_id=msg.get("file_id"),
                    caption=f_caption,
                    protect_content=msg.get('protect', False),
                    reply_markup=reply_markup
                )
                filesarr.append(msg_sent)
                sent_count += 1
                # Count each file toward daily limit for free users
                if not (is_prem or is_verified) and DAILY_FILE_LIMIT_MODE:
                    await db.increment_daily_file_count(user_id)
            except FloodWait as e:
                await asyncio.sleep(e.x)
                msg_sent = await client.send_cached_media(
                    chat_id=message.from_user.id,
                    file_id=msg.get("file_id"),
                    caption=f_caption,
                    protect_content=msg.get('protect', False),
                    reply_markup=reply_markup
                )
                filesarr.append(msg_sent)
                sent_count += 1
                if not (is_prem or is_verified) and DAILY_FILE_LIMIT_MODE:
                    await db.increment_daily_file_count(user_id)
            except Exception as e:
                logger.warning(e, exc_info=True)
                continue
            await asyncio.sleep(1)

        await sts.delete()

        # If free user didn't receive all files, show limit-reached notice
        remaining_files = total_files - sent_count
        if remaining_files > 0 and not (is_prem or is_verified):
            now = datetime.now(IST)
            midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            time_str = format_time_remaining((midnight - now).total_seconds())
            btn = []
            if VERIFY_MODE:
                btn.append([InlineKeyboardButton(
                    "🔓 Verify Now - Unlimited Access",
                    url=await get_token(client, user_id, f"https://telegram.me/{username}?start=")
                )])
                btn.append([InlineKeyboardButton("❓ How To Verify", url=VERIFY_TUTORIAL)])
            btn.append([InlineKeyboardButton("👑 Buy Premium - Unlimited Access", callback_data="show_plan")])
            await client.send_message(
                chat_id=message.from_user.id,
                text=(
                    f"<b>⚠️ Daily Free File Limit Reached!\n\n"
                    f"✅ Files sent to you: <b>{sent_count}</b> out of {total_files}\n"
                    f"📦 Remaining files in this batch: <b>{remaining_files}</b>\n\n"
                    f"You have used all <b>{DAILY_FILE_LIMIT}</b> free file(s) for today.\n"
                    f"⏳ Next free reset in: <b>{time_str}</b>\n\n"
                    f"🔓 To receive the remaining <b>{remaining_files}</b> file(s), get unlimited access:\n"
                    f"• <b>Verify</b> — Free, valid for 24 hours\n"
                    f"• <b>Buy Premium</b> — Permanent unlimited access\n\n"
                    f"👇 Check /plan for Premium details</b>"
                ),
                reply_markup=InlineKeyboardMarkup(btn)
            )

        if AUTO_DELETE_MODE and filesarr:
            k = await client.send_message(
                chat_id=message.from_user.id,
                text=f"<b><u>❗️❗️❗️IMPORTANT❗️️❗️❗️</u></b>\n\nThis Movie File/Video will be deleted in <b><u>{AUTO_DELETE} minutes</u> 🫥 <i></b>(Due to Copyright Issues)</i>.\n\n<b><i>Please forward this File/Video to your Saved Messages and Start Download there</b>"
            )
            await asyncio.sleep(AUTO_DELETE_TIME)
            for x in filesarr:
                try:
                    await x.delete()
                except Exception:
                    pass
            await k.edit_text("<b>Your All Files/Videos is successfully deleted!!!</b>")
        return

    # --- File from DB ---
    files_ = await get_file_details(file_id)
    if not files_:
        try:
            pre, file_id = ((base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))).decode("ascii")).split("_", 1)

            # Check access
            allowed = await handle_file_access(client, message, file_id, None, pre)
            if not allowed:
                return

            msg = await client.send_cached_media(
                chat_id=message.from_user.id,
                file_id=file_id,
                protect_content=True if pre == 'filep' else False,
            )
            filetype = msg.media
            file = getattr(msg, filetype.value)
            title = '@SGBACKUP  ' + ' '.join(
                filter(lambda x: not x.startswith('[') and not x.startswith('@'), file.file_name.split())
            )
            size = get_size(file.file_size)
            f_caption = f"<code>{title}</code>"
            if CUSTOM_FILE_CAPTION:
                try:
                    f_caption = CUSTOM_FILE_CAPTION.format(
                        file_name='' if title is None else title,
                        file_size='' if size is None else size,
                        file_caption=''
                    )
                except Exception:
                    pass

            await msg.edit_caption(f_caption)
            if STREAM_MODE:
                g = await msg.reply_text(
                    text="**•• ʏᴏᴜ ᴄᴀɴ ɢᴇɴᴇʀᴀᴛᴇ ᴏɴʟɪɴᴇ sᴛʀᴇᴀᴍ ʟɪɴᴋ ᴏғ ʏᴏᴜʀ ғɪʟᴇ ᴀɴᴅ ᴀʟsᴏ ғᴀsᴛ ᴅᴏᴡɴʟᴏᴀᴅ ʟɪɴᴋ ғᴏʀ ʏᴏᴜʀ ғɪʟᴇ ᴄʟɪᴄᴋɪɴɢ ᴏɴ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ 👇**",
                    quote=True,
                    disable_web_page_preview=True,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton('🚀 Fast Download / Watch Online🖥️', callback_data=f'generate_stream_link:{file_id}')
                    ]])
                )
            if AUTO_DELETE_MODE:
                k = await client.send_message(
                    chat_id=message.from_user.id,
                    text=f"<b><u>❗️❗️❗️IMPORTANT❗️️❗️❗️</u></b>\n\nThis Movie File/Video will be deleted in <b><u>{AUTO_DELETE} minutes</u> 🫥 <i></b>(Due to Copyright Issues)</i>.\n\n<b><i>Please forward this File/Video to your Saved Messages and Start Download there</b>"
                )
                await asyncio.sleep(AUTO_DELETE_TIME)
                try:
                    await msg.delete()
                except Exception:
                    pass
                try:
                    await g.delete()
                except Exception:
                    pass
                await k.edit_text("<b>Your File/Video is successfully deleted!!!</b>")
            return
        except Exception:
            pass
        return await message.reply('No such file exists.')

    files = files_[0]
    title = files.file_name
    size = get_size(files.file_size)
    f_caption = files.caption
    if CUSTOM_FILE_CAPTION:
        try:
            f_caption = CUSTOM_FILE_CAPTION.format(
                file_name='' if title is None else title,
                file_size='' if size is None else size,
                file_caption='' if f_caption is None else f_caption
            )
        except Exception as e:
            logger.exception(e)
    if f_caption is None:
        f_caption = f"{files.file_name}"

    # Check access
    allowed = await handle_file_access(client, message, file_id, f_caption, pre)
    if not allowed:
        return

    x = await client.send_cached_media(
        chat_id=message.from_user.id,
        file_id=file_id,
        caption=f_caption,
        protect_content=True if pre == 'filep' else False,
    )
    if STREAM_MODE:
        g = await x.reply_text(
            text="**•• ʏᴏᴜ ᴄᴀɴ ɢᴇɴᴇʀᴀᴛᴇ ᴏɴʟɪɴᴇ sᴛʀᴇᴀᴍ ʟɪɴᴋ ᴏғ ʏᴏᴜʀ ғɪʟᴇ ᴀɴᴅ ᴀʟsᴏ ғᴀsᴛ ᴅᴏᴡɴʟᴏᴀᴅ ʟɪɴᴋ ғᴏʀ ʏᴏᴜʀ ғɪʟᴇ ᴄʟɪᴄᴋɪɴɢ ᴏɴ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ 👇**",
            quote=True,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🚀 Fast Download / Watch Online🖥️', callback_data=f'generate_stream_link:{file_id}')
            ]])
        )
    if AUTO_DELETE_MODE:
        k = await client.send_message(
            chat_id=message.from_user.id,
            text=f"<b><u>❗️❗️❗️IMPORTANT❗️️❗️❗️</u></b>\n\nThis Movie File/Video will be deleted in <b><u>{AUTO_DELETE} minutes</u> 🫥 <i></b>(Due to Copyright Issues)</i>.\n\n<b><i>Please forward this File/Video to your Saved Messages and Start Download there</b>"
        )
        await asyncio.sleep(AUTO_DELETE_TIME)
        try:
            await x.delete()
        except Exception:
            pass
        try:
            await g.delete()
        except Exception:
            pass
        await k.edit_text("<b>Your All Files/Videos is successfully deleted!!!</b>")


# ─────────────────────────────────────────────────────────────
# /plan Command - Show premium plans
# ─────────────────────────────────────────────────────────────

@Client.on_message(filters.command("plan") & filters.private)
async def plan_cmd(client, message):
    btn = [
            [InlineKeyboardButton("💳 Pay & Contact Admin", url="https://t.me/SubhajitGhosh0")],
            [InlineKeyboardButton("✅ Check My Plan", callback_data="check_myplan")]
    ]
    await message.reply_photo(
        photo=PAYMENT_QR,
        caption=PAYMENT_TEXT,
        reply_markup=InlineKeyboardMarkup(btn)
    )


# ─────────────────────────────────────────────────────────────
# /myplan Command - Show user's current plan
# ─────────────────────────────────────────────────────────────

@Client.on_message(filters.command("myplan") & filters.private)
async def myplan_cmd(client, message):
    user_id = message.from_user.id
    is_prem = await db.is_premium(user_id)
    is_verified = await check_verification(client, user_id)
    daily_count = await db.get_daily_file_count(user_id)

    if is_prem:
        expiry_str = await db.get_premium_expiry(user_id)
        text = (
            f"<b>👑 Your Plan: PREMIUM\n\n"
            f"✅ Status: Active\n"
            f"📅 Expires: {expiry_str}\n\n"
            f"🎁 Benefits:\n"
            f"• No verification needed\n"
            f"• Unlimited file access\n"
            f"• Ad-free experience</b>"
        )
    elif is_verified:
        remaining = await get_user_verify_expiry(user_id)
        text = (
            f"<b>✅ Your Plan: FREE (Verified)\n\n"
            f"🔓 Verification Status: Active\n"
            f"⏳ Expires in: {remaining}\n\n"
            f"You have unlimited access until verification expires.\n"
            f"After that, verify again or /plan for Premium.</b>"
        )
    else:
        text = (
            f"<b>📋 Your Plan: FREE\n\n"
            f"📂 Files used today: {daily_count}/{DAILY_FILE_LIMIT}\n"
            f"🔓 Verification: Not verified\n\n"
        )
        if DAILY_FILE_LIMIT_MODE:
            text += f"You get <b>{DAILY_FILE_LIMIT}</b> free file(s) per day.\n"
        text += "\nUse /plan to upgrade to Premium."

    btn = [[InlineKeyboardButton("👑 Buy Premium", callback_data="show_plan")]]
    await message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(btn))


# ─────────────────────────────────────────────────────────────
# /stats Command - Bot statistics (Admin only)
# ─────────────────────────────────────────────────────────────

@Client.on_message(filters.command("stats") & filters.user(ADMINS))
async def stats_cmd(client, message):
    sts = await message.reply("<b>📊 Fetching stats...</b>")
    try:
        file_stats = await db.get_file_stats()
        total_files = file_stats.get('total', 0)
        today_files = file_stats.get('today_count', 0)
        verified_count = await get_verified_users_count_async()
        total_users = await db.total_users_count()
        premium_count = await db.total_premium_count()

        now_ist = datetime.now(IST).strftime('%d %b %Y, %I:%M %p IST')

        text = (
            f"<b>📊 Bot Statistics\n"
            f"🕐 Updated: {now_ist}\n\n"
            f"📂 Total Files Stored: <code>{total_files}</code>\n"
            f"📅 Files Added Today (IST): <code>{today_files}</code>\n\n"
            f"👥 Total Users: <code>{total_users}</code>\n"
            f"✅ Currently Verified Users: <code>{verified_count}</code>\n"
            f"👑 Premium Users: <code>{premium_count}</code></b>"
        )
        await sts.edit(text)
    except Exception as e:
        await sts.edit(f"<b>Error fetching stats: {e}</b>")


# ─────────────────────────────────────────────────────────────
# /addpremium Command - Add premium user (Admin only)
# ─────────────────────────────────────────────────────────────

@Client.on_message(filters.command("addpremium") & filters.user(ADMINS))
async def add_premium_cmd(client, message):
    usage = "<b>Usage: /addpremium [user_id] [days]\nExample: /addpremium 123456789 30</b>"
    cmd = message.command
    if len(cmd) != 3:
        return await message.reply(usage)
    try:
        target_id = int(cmd[1])
        days = int(cmd[2])
    except ValueError:
        return await message.reply(usage)

    await db.add_premium(target_id, days)
    expiry = await db.get_premium_expiry(target_id)
    await message.reply(
        f"<b>✅ Premium Added!\n\n"
        f"👤 User ID: <code>{target_id}</code>\n"
        f"📅 Duration: {days} days\n"
        f"⏰ Expires: {expiry}</b>"
    )
    try:
        await client.send_message(
            chat_id=target_id,
            text=(
                f"<b>🎉 Congratulations! Your Premium has been activated!\n\n"
                f"📅 Duration: {days} days\n"
                f"⏰ Expires: {expiry}\n\n"
                f"Enjoy unlimited file access! 🚀</b>"
            )
        )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# /removepremium Command - Remove premium user (Admin only)
# ─────────────────────────────────────────────────────────────

@Client.on_message(filters.command("removepremium") & filters.user(ADMINS))
async def remove_premium_cmd(client, message):
    cmd = message.command
    if len(cmd) != 2:
        return await message.reply("<b>Usage: /removepremium [user_id]</b>")
    try:
        target_id = int(cmd[1])
    except ValueError:
        return await message.reply("<b>Invalid user ID.</b>")

    await db.remove_premium(target_id)
    await message.reply(f"<b>✅ Premium removed for user <code>{target_id}</code>.</b>")
    try:
        await client.send_message(
            chat_id=target_id,
            text="<b>⚠️ Your Premium access has been removed.\nContact admin for more info.</b>"
        )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# /api and /base_site Commands
# ─────────────────────────────────────────────────────────────

@Client.on_message(filters.command('api') & filters.private)
async def shortener_api_handler(client, m: Message):
    user_id = m.from_user.id
    user = await get_user(user_id)
    cmd = m.command
    if len(cmd) == 1:
        s = script.SHORTENER_API_MESSAGE.format(
            base_site=user["base_site"], shortener_api=user["shortener_api"]
        )
        return await m.reply(s)
    elif len(cmd) == 2:
        api = cmd[1].strip()
        await update_user_info(user_id, {"shortener_api": api})
        await m.reply("<b>Shortener API updated successfully to</b> " + api)


@Client.on_message(filters.command("base_site") & filters.private)
async def base_site_handler(client, m: Message):
    user_id = m.from_user.id
    user = await get_user(user_id)
    cmd = m.command
    text = (
        "`/base_site (base_site)`\n\n<b>Current base site: None\n\n EX:</b> "
        "`/base_site shortnerdomain.com`\n\nIf You Want To Remove Base Site Then Copy This And Send To Bot - `/base_site None`"
    )
    if len(cmd) == 1:
        return await m.reply(text=text, disable_web_page_preview=True)
    elif len(cmd) == 2:
        base_site = cmd[1].strip()
        if not domain(base_site):
            return await m.reply(text=text, disable_web_page_preview=True)
        await update_user_info(user_id, {"base_site": base_site})
        await m.reply("<b>Base Site updated successfully</b>")


# ─────────────────────────────────────────────────────────────
# Callback Query Handler
# ─────────────────────────────────────────────────────────────

@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    if query.data == "close_data":
        await query.message.delete()

    elif query.data == "show_plan":
        btn = [
            [InlineKeyboardButton("💳 Pay & Contact Admin", url="https://t.me/SubhajitGhosh0")],
            [InlineKeyboardButton("✅ Check My Plan", callback_data="check_myplan")]
        ]
        await query.message.reply_photo(
            photo=PAYMENT_QR,
            caption=PAYMENT_TEXT,
            reply_markup=InlineKeyboardMarkup(btn)
        )
        await query.answer()

    elif query.data == "check_myplan":
        await query.answer()
        fake_msg = query.message
        fake_msg.from_user = query.from_user
        await myplan_cmd(client, fake_msg)

    elif query.data == "about":
        buttons = [[
            InlineKeyboardButton('Hᴏᴍᴇ', callback_data='start'),
            InlineKeyboardButton('🔒 Cʟᴏsᴇ', callback_data='close_data')
        ]]
        await client.edit_message_media(
            query.message.chat.id,
            query.message.id,
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(buttons)
        me2 = (await client.get_me()).mention
        await query.message.edit_text(
            text=script.ABOUT_TXT.format(me2),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

    elif query.data == "start":
        buttons = [[
            InlineKeyboardButton('💝 sᴜʙsᴄʀɪʙᴇ ᴍʏ ʏᴏᴜᴛᴜʙᴇ ᴄʜᴀɴɴᴇʟ', url='https://t.me/SGBACKUP')
        ], [
            InlineKeyboardButton('🔍 sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ', url='https://t.me/SGBACKUP'),
            InlineKeyboardButton('🤖 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ', url='https://t.me/SGBACKUP')
        ], [
            InlineKeyboardButton('🤖 ᴄʀᴇᴀᴛᴇ ʏᴏᴜʀ ᴏᴡɴ ᴄʟᴏɴᴇ ʙᴏᴛ', callback_data='clone')
        ], [
            InlineKeyboardButton('💁‍♀️ ʜᴇʟᴘ', callback_data='help'),
            InlineKeyboardButton('😊 ᴀʙᴏᴜᴛ', callback_data='about')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id,
            query.message.id,
            InputMediaPhoto(random.choice(PICS))
        )
        me2 = (await client.get_me()).mention
        await query.message.edit_text(
            text=script.START_TXT.format(query.from_user.mention, me2),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

    elif query.data == "clone":
        buttons = [[
            InlineKeyboardButton('Hᴏᴍᴇ', callback_data='start'),
            InlineKeyboardButton('🔒 Cʟᴏsᴇ', callback_data='close_data')
        ]]
        await client.edit_message_media(
            query.message.chat.id,
            query.message.id,
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text="Clone feature is here.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif query.data == "help":
        buttons = [[
            InlineKeyboardButton('Hᴏᴍᴇ', callback_data='start'),
            InlineKeyboardButton('🔒 Cʟᴏsᴇ', callback_data='close_data')
        ]]
        await client.edit_message_media(
            query.message.chat.id,
            query.message.id,
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text=script.HELP_TXT,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=enums.ParseMode.HTML
        )
