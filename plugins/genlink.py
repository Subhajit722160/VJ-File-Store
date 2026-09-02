# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re
from pyrogram import filters, Client, enums
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, UsernameInvalid, UsernameNotModified
from config import ADMINS, LOG_CHANNEL, PUBLIC_FILE_STORE, WEBSITE_URL, WEBSITE_URL_MODE
from plugins.database import unpack_new_file_id
from plugins.users_api import get_user, get_short_link
from plugins.dbusers import db
import re
import os
import json
import base64
import logging
import asyncio

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Collect mode sessions: stores files per user until /done
COLLECT_SESSIONS = {}


async def allowed(_, __, message):
    if PUBLIC_FILE_STORE:
        return True
    if message.from_user and message.from_user.id in ADMINS:
        return True
    return False

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def restore_batch_file(bot, message):
    """
    Batch.json ফাইলটি বটকে পাঠালে, তার ভেতরের সবগুলো
    ফাইল/ভিডিও ইউজারকে আবার একে একে ফেরত পাঠায়।
    """
    sts = await message.reply("⏳ <b>Batch.json পড়া হচ্ছে, একটু অপেক্ষা করুন...</b>")
    path = await message.download()
    try:
        with open(path, "r", encoding="utf-8") as f:
            files = json.load(f)
    except Exception as e:
        os.remove(path)
        return await sts.edit(f"❌ <b>Batch.json পড়া গেল না।</b>\n\nকারণ: <code>{e}</code>")
    os.remove(path)

    total = len(files)
    if total == 0:
        return await sts.edit("❌ <b>এই Batch.json ফাইলে কোনো ফাইল নেই।</b>")

    await sts.edit(f"📦 <b>মোট {total}টি ফাইল পাওয়া গেছে। পাঠানো শুরু হচ্ছে...</b>")

    sent, failed = 0, 0
    for item in files:
        file_id = item.get("file_id")
        caption = item.get("caption") or item.get("title") or ""
        if not file_id:
            failed += 1
            continue
        try:
            await bot.send_cached_media(
                chat_id=message.chat.id,
                file_id=file_id,
                caption=caption,
                protect_content=item.get("protect", False),
            )
            sent += 1
        except Exception as e:
            logger.exception(e)
            failed += 1
        await asyncio.sleep(1)  # flood-wait এড়াতে প্রতিটা ফাইলের মাঝে বিরতি

    await sts.edit(
        f"✅ <b>সম্পন্ন হয়েছে!</b>\n\n"
        f"পাঠানো হয়েছে: <b>{sent}</b>/{total}\n"
        f"ব্যর্থ হয়েছে: <b>{failed}</b>"
    )

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_message((filters.document | filters.video | filters.audio| filters.photo) & filters.private & filters.create(allowed))
async def incoming_gen_link(bot, message):
    user_id = message.from_user.id

    # ---- Batch.json পাঠালে সব ফাইল ফেরত পাঠানোর ফিচার ----
    if message.document and (message.document.file_name or "").lower() == "batch.json":
        return await restore_batch_file(bot, message)

    if user_id in COLLECT_SESSIONS:
        file_type = message.media
        file = getattr(message, file_type.value)
        raw_file_id = file.file_id
        raw_unique_id = file.file_unique_id
        existing_ids = {f["unique_id"] for f in COLLECT_SESSIONS[user_id]["files"]}
        if raw_unique_id in existing_ids:
            count = len(COLLECT_SESSIONS[user_id]["files"])
            return await message.reply(f"⚠️ <b>Duplicate file skipped!</b>\n\n📦 Total collected: <code>{count}</code> files\nSend /done to generate the link.")
        caption = (message.caption.html if message.caption else "")
        file_data = {
            "file_id": raw_file_id,
            "unique_id": raw_unique_id,
            "caption": caption,
            "title": getattr(file, "file_name", ""),
            "size": file.file_size,
            "protect": COLLECT_SESSIONS[user_id]["protect"],
        }
        COLLECT_SESSIONS[user_id]["files"].append(file_data)
        count = len(COLLECT_SESSIONS[user_id]["files"])
        return await message.reply(f"✅ <b>File #{count} added!</b>\n\nSend more files or /done to generate the combined link.")
    username = (await bot.get_me()).username
    file_type = message.media
    file_id, ref = unpack_new_file_id((getattr(message, file_type.value)).file_id)
    string = 'file_'
    string += file_id
    outstr = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
    user_id = message.from_user.id
    user = await get_user(user_id)
    if WEBSITE_URL_MODE:
        share_link = f"{WEBSITE_URL}?Tech_VJ={outstr}"
    else:
        share_link = f"https://t.me/{username}?start={outstr}"

    # Track file count stats
    await db.increment_total_file_count()

    if user["base_site"] and user["shortener_api"] is not None:
        short_link = await get_short_link(user, share_link)
        await message.reply(f"<b>⭕ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ:\n\n🖇️ sʜᴏʀᴛ ʟɪɴᴋ :- {short_link}</b>")
    else:
        await message.reply(f"<b>⭕ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ:\n\n🔗 ᴏʀɪɢɪɴᴀʟ ʟɪɴᴋ :- {share_link}</b>")


@Client.on_message(filters.command(['link', 'plink']) & filters.create(allowed))
async def gen_link_s(bot, message):
    username = (await bot.get_me()).username
    replied = message.reply_to_message
    if not replied:
        return await message.reply('Reply to a message to get a shareable link.')
    file_type = replied.media
    if file_type not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT]:
        return await message.reply("**ʀᴇᴘʟʏ ᴛᴏ ᴀ sᴜᴘᴘᴏʀᴛᴇᴅ ᴍᴇᴅɪᴀ**")
    if message.has_protected_content and message.chat.id not in ADMINS:
        return await message.reply("okDa")

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

    file_id, ref = unpack_new_file_id((getattr(replied, file_type.value)).file_id)
    string = 'filep_' if message.text.lower().strip() == "/plink" else 'file_'
    string += file_id
    outstr = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
    user_id = message.from_user.id
    user = await get_user(user_id)
    if WEBSITE_URL_MODE:
        share_link = f"{WEBSITE_URL}?Tech_VJ={outstr}"
    else:
        share_link = f"https://t.me/{username}?start={outstr}"

    # Track file count stats
    await db.increment_total_file_count()

    if user["base_site"] and user["shortener_api"] is not None:
        short_link = await get_short_link(user, share_link)
        await message.reply(f"<b>⭕ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ:\n\n🖇️ sʜᴏʀᴛ ʟɪɴᴋ :- {short_link}</b>")
    else:
        await message.reply(f"<b>⭕ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ:\n\n🔗 ᴏʀɪɢɪɴᴀʟ ʟɪɴᴋ :- {share_link}</b>")


# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_message(filters.command(['batch', 'pbatch']) & filters.create(allowed))
async def gen_link_batch(bot, message):
    username = (await bot.get_me()).username
    if " " not in message.text:
        return await message.reply("Use correct format.\nExample /batch https://t.me/SGBACKUP/2 https://t.me/SGBACKUP/5.")
    links = message.text.strip().split(" ")
    if len(links) != 3:
        return await message.reply("Use correct format.\nExample /batch https://t.me/SGBACKUP/2 https://t.me/SGBACKUP/5.")
    cmd, first, last = links
    regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
    match = regex.match(first)
    if not match:
        return await message.reply('Invalid link')
    f_chat_id = match.group(4)
    f_msg_id = int(match.group(5))
    if f_chat_id.isnumeric():
        f_chat_id = int(("-100" + f_chat_id))

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

    match = regex.match(last)
    if not match:
        return await message.reply('Invalid link')
    l_chat_id = match.group(4)
    l_msg_id = int(match.group(5))
    if l_chat_id.isnumeric():
        l_chat_id = int(("-100" + l_chat_id))

    if f_chat_id != l_chat_id:
        return await message.reply("Chat ids not matched.")
    try:
        chat_id = (await bot.get_chat(f_chat_id)).id
    except ChannelInvalid:
        return await message.reply('This may be a private channel / group. Make me an admin over there to index the files.')
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply('Invalid Link specified.')
    except Exception as e:
        return await message.reply(f'Errors - {e}')

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

    sts = await message.reply("**ɢᴇɴᴇʀᴀᴛɪɴɢ ʟɪɴᴋ ғᴏʀ ʏᴏᴜʀ ᴍᴇssᴀɢᴇ**.\n**ᴛʜɪs ᴍᴀʏ ᴛᴀᴋᴇ ᴛɪᴍᴇ ᴅᴇᴘᴇɴᴅɪɴɢ ᴜᴘᴏɴ ɴᴜᴍʙᴇʀ ᴏғ ᴍᴇssᴀɢᴇs**")
    FRMT = "**ɢᴇɴᴇʀᴀᴛɪɴɢ ʟɪɴᴋ...**\n**ᴛᴏᴛᴀʟ ᴍᴇssᴀɢᴇs:** {total}\n**ᴅᴏɴᴇ:** {current}\n**ʀᴇᴍᴀɪɴɪɴɢ:** {rem}\n**sᴛᴀᴛᴜs:** {sts}"

    outlist = []

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

    og_msg = 0
    tot = 0
    async for msg in bot.iter_messages(f_chat_id, l_msg_id, f_msg_id):
        tot += 1
        if msg.empty or msg.service:
            continue
        if not msg.media:
            continue
        try:
            file_type = msg.media
            file = getattr(msg, file_type.value)
            caption = getattr(msg, 'caption', '')
            if caption:
                caption = caption.html
            if file:
                file = {
                    "file_id": file.file_id,
                    "caption": caption,
                    "title": getattr(file, "file_name", ""),
                    "size": file.file_size,
                    "protect": cmd.lower().strip() == "/pbatch",
                }
                og_msg += 1
                outlist.append(file)
        except Exception:
            pass
        if not og_msg % 20:
            try:
                await sts.edit(FRMT.format(total=l_msg_id - f_msg_id, current=tot, rem=((l_msg_id - f_msg_id) - tot), sts="Saving Messages"))
            except Exception:
                pass

    with open(f"batchmode_{message.from_user.id}.json", "w+") as out:
        json.dump(outlist, out)
    post = await bot.send_document(LOG_CHANNEL, f"batchmode_{message.from_user.id}.json", file_name="Batch.json", caption="⚠️Generated for filestore.")
    os.remove(f"batchmode_{message.from_user.id}.json")
    file_id, ref = unpack_new_file_id(post.document.file_id)
    user_id = message.from_user.id
    user = await get_user(user_id)

    # Track file count stats (batch counts as 1 link)
    await db.increment_total_file_count()

    if WEBSITE_URL_MODE:
        share_link = f"{WEBSITE_URL}?Tech_VJ=BATCH-{file_id}"
    else:
        share_link = f"https://t.me/{username}?start=BATCH-{file_id}"
    if user["base_site"] and user["shortener_api"] is not None:
        short_link = await get_short_link(user, share_link)
        await sts.edit(f"<b>⭕ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ:\n\nContains `{og_msg}` files.\n\n🖇️ sʜᴏʀᴛ ʟɪɴᴋ :- {short_link}</b>")
    else:
        await sts.edit(f"<b>⭕ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ:\n\nContains `{og_msg}` files.\n\n🔗 ᴏʀɪɢɪɴᴀʟ ʟɪɴᴋ :- {share_link}</b>")


@Client.on_message(filters.command(['collect', 'pcollect']) & filters.create(allowed))
async def start_collect_mode(bot, message):
    user_id = message.from_user.id
    protect = "pcollect" in message.text.lower()
    COLLECT_SESSIONS[user_id] = {"files": [], "protect": protect}
    await message.reply("✅ <b>Collect mode started!</b>\n\nNow send me all the files one by one.\nWhen you're done, send /done to get a combined link.\n\n🔍 Duplicate files will be filtered automatically.")


@Client.on_message(filters.command(['done']) & filters.create(allowed))
async def finish_collect_mode(bot, message):
    user_id = message.from_user.id
    if user_id not in COLLECT_SESSIONS:
        return await message.reply("❌ You are not in collect mode. Send /collect first.")
    session = COLLECT_SESSIONS.pop(user_id)
    outlist = session["files"]
    total = len(outlist)
    if total == 0:
        return await message.reply("❌ No files collected. Please send files after /collect command.")
    sts = await message.reply(f"⏳ <b>Generating combined link for {total} files...</b>")
    username = (await bot.get_me()).username
    with open(f"collectmode_{user_id}.json", "w+") as out:
        json.dump(outlist, out)
    post = await bot.send_document(LOG_CHANNEL, f"collectmode_{user_id}.json", file_name="Batch.json", caption="⚠️Generated for filestore collect mode.")
    os.remove(f"collectmode_{user_id}.json")
    file_id, ref = unpack_new_file_id(post.document.file_id)
    user = await get_user(user_id)
    await db.increment_total_file_count()
    if WEBSITE_URL_MODE:
        share_link = f"{WEBSITE_URL}?Tech_VJ=BATCH-{file_id}"
    else:
        share_link = f"https://t.me/{username}?start=BATCH-{file_id}"
    if user["base_site"] and user["shortener_api"] is not None:
        short_link = await get_short_link(user, share_link)
        await sts.edit(f"<b>✅ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ᴄᴏᴍʙɪɴᴇᴅ ʟɪɴᴋ:\n\nContains `{total}` files.\n\n🖇️ sʜᴏʀᴛ ʟɪɴᴋ :- {short_link}</b>")
    else:
        await sts.edit(f"<b>✅ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ᴄᴏᴍʙɪɴᴇᴅ ʟɪɴᴋ:\n\nContains `{total}` files.\n\n🔗 ᴏʀɪɢɪɴᴀʟ ʟɪɴᴋ :- {share_link}</b>")
