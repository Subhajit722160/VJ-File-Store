# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re
import os
from os import environ
from Script import script

id_pattern = re.compile(r'^.\d+$')
def is_enabled(value, default):
    if value.lower() in ["true", "yes", "1", "enable", "y"]:
        return True
    elif value.lower() in ["false", "no", "0", "disable", "n"]:
        return False
    else:
        return default
      
# Bot Information
API_ID = int(environ.get("API_ID", "38945957"))
API_HASH = environ.get("API_HASH", "2ff2b98dc10045b2aa077e3d3e3e2ec8")
BOT_TOKEN = environ.get("BOT_TOKEN", "")

PICS = (environ.get('PICS', 'https://telegra.ph/file/755ae30020c5ddfd331e2.jpg')).split() # Bot Start Picture
ADMINS = [int(admin) if id_pattern.search(admin) else admin for admin in environ.get('ADMINS', '919169586 5745069321').split()]
BOT_USERNAME = environ.get("BOT_USERNAME", "Insta_Vip_Club_bot") # without @
PORT = environ.get("PORT", "8080")

# Force Subscribe Information (Multiple Channels Supported)
# Add multiple channel IDs separated by space. Example: "-1001234567890 -1009876543210"
FORCE_SUB_MODE = bool(environ.get('FORCE_SUB_MODE', False))  # Set True or False
FORCE_SUB_CHANNELS = [int(ch) for ch in environ.get('FORCE_SUB_CHANNELS', '-1001877309572').split() if ch.strip()]

# Clone Info :-
CLONE_MODE = bool(environ.get('CLONE_MODE', False)) # Set True or False

# If Clone Mode Is True Then Fill All Required Variable, If False Then Don't Fill.
CLONE_DB_URI = environ.get("CLONE_DB_URI", "")
CDB_NAME = environ.get("CDB_NAME", "clonetechvj")

# Database Information
DB_URI = environ.get("DB_URI", "mongodb+srv://k2l6zn_db_user:089dp84FnUfAiaGh@cluster0.7gya04k.mongodb.net/")
DB_NAME = environ.get("DB_NAME", "techvj")

# Auto Delete Information
AUTO_DELETE_MODE = bool(environ.get('AUTO_DELETE_MODE', True)) # Set True or False

# If Auto Delete Mode Is True Then Fill All Required Variable, If False Then Don't Fill.
AUTO_DELETE = int(environ.get("AUTO_DELETE", "10")) # Time in Minutes
AUTO_DELETE_TIME = int(environ.get("AUTO_DELETE_TIME", "600")) # Time in Seconds

# Channel Information
LOG_CHANNEL = int(environ.get("LOG_CHANNEL", "-1004415993500"))

# File Caption Information
CUSTOM_FILE_CAPTION = environ.get("CUSTOM_FILE_CAPTION", f"{script.CAPTION}")
BATCH_FILE_CAPTION = environ.get("BATCH_FILE_CAPTION", CUSTOM_FILE_CAPTION)

# Enable - True or Disable - False
PUBLIC_FILE_STORE = is_enabled((environ.get('PUBLIC_FILE_STORE', "True")), True)

# ============================================================
# Verify Info (Token / Link Shortener Verification)
# ============================================================
# VERIFY_MODE: Set True to enable verification, False to disable
VERIFY_MODE = bool(environ.get('VERIFY_MODE', True))  # Set True or False

# If Verify Mode Is True Then Fill All Required Variable, If False Then Don't Fill.
SHORTLINK_API = environ.get("SHORTLINK_API", "358784d7b7e190165b4f3d2982e8f336e35bcf14")  # shortlink api
SHORTLINK_URL = environ.get("SHORTLINK_URL", "liteshort.com")  # shortlink domain without https://
VERIFY_TUTORIAL = environ.get("VERIFY_TUTORIAL", "http://t.me/How_To_Watch_Liteshort_Links")  # how to open link

# ============================================================
# Daily Free File Limit Settings
# ============================================================
# DAILY_FILE_LIMIT_MODE = True  : Free users get DAILY_FILE_LIMIT files per day for free (no verify needed).
#                                  After limit is reached, they must verify or buy premium.
# DAILY_FILE_LIMIT_MODE = False : No free daily limit. User must verify (if VERIFY_MODE=True) or buy premium.
DAILY_FILE_LIMIT_MODE = bool(environ.get('DAILY_FILE_LIMIT_MODE', False))  # Set True or False
DAILY_FILE_LIMIT = int(environ.get('DAILY_FILE_LIMIT', 2))  # Daily free file limit count for free users

# ============================================================
# Premium / Payment Settings
# ============================================================
PAYMENT_QR = environ.get('PAYMENT_QR', 'https://i.ibb.co/43K0xSy/IMG-20261025-185144-904.jpg')  # Payment QR code picture URL
PAYMENT_TEXT = environ.get('PAYMENT_TEXT', '<b>- ᴀᴠᴀɪʟᴀʙʟᴇ ᴘʟᴀɴs - \n\n- 15ʀs - 1 ᴍᴏɴᴛʜ\n- 30ʀs - 2 ᴍᴏɴᴛʜ\n- 45ʀs - 3 ᴍᴏɴᴛʜs\n- 90ʀs - 6 ᴍᴏɴᴛʜs\n\n🎁 ᴘʀᴇᴍɪᴜᴍ ғᴇᴀᴛᴜʀᴇs 🎁\n\n○ 🔐 ɴᴏ ɴᴇᴇᴅ ᴛᴏ ᴠᴇʀɪғʏ\n○ 📂 ᴅɪʀᴇᴄᴛ ғɪʟᴇ ᴀᴄᴄᴇss\n○ 📢 ᴇxᴄʟᴜsɪᴠᴇ ᴘʀᴇᴍɪᴜᴍ ᴄʜᴀɴɴᴇʟ\n○ 🛠 ᴘʀɪᴏʀɪᴛʏ ᴀᴅᴍɪɴ sᴜᴘᴘᴏʀᴛ\n\n✨ ᴜᴘɪ ɪᴅ - <code>BHARATPE09912258040@yesbankltd</code>\n\nᴄʟɪᴄᴋ ᴛᴏ ᴄʜᴇᴄᴋ ʏᴏᴜʀ ᴀᴄᴛɪᴠᴇ ᴘʟᴀɴ /myplan\n\n💢 ᴍᴜsᴛ sᴇɴᴅ sᴄʀᴇᴇɴsʜᴏᴛ ᴀғᴛᴇʀ ᴘᴀʏᴍᴇɴᴛ\n\n‼️ ᴀғᴛᴇʀ sᴇɴᴅɪɴɢ ᴀ sᴄʀᴇᴇɴsʜᴏᴛ ᴘʟᴇᴀsᴇ ɢɪᴠᴇ ᴜs sᴏᴍᴇ ᴛɪᴍᴇ ᴛᴏ ᴀᴅᴅ ʏᴏᴜ ɪɴ ᴛʜᴇ ᴘʀᴇᴍɪᴜᴍ</b>')

# Website Info:
WEBSITE_URL_MODE = bool(environ.get('WEBSITE_URL_MODE', False)) # Set True or False

# If Website Url Mode Is True Then Fill All Required Variable, If False Then Don't Fill.
WEBSITE_URL = environ.get("WEBSITE_URL", "") # For More Information Check Video On Yt - @Tech_VJ

# File Stream Config
STREAM_MODE = bool(environ.get('STREAM_MODE', False)) # Set True or False

# If Stream Mode Is True Then Fill All Required Variable, If False Then Don't Fill.
MULTI_CLIENT = False
SLEEP_THRESHOLD = int(environ.get('SLEEP_THRESHOLD', '60'))
PING_INTERVAL = int(environ.get("PING_INTERVAL", "1200"))  # 20 minutes
if 'DYNO' in environ:
    ON_HEROKU = True
else:
    ON_HEROKU = False
URL = environ.get("URL", "https://ltd-daffy-subhajitghoshbotggg-6b1cf758.koyeb.app/")


# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01
