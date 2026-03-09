# 📁 VJ File Store Bot

A powerful Telegram File Store Bot with Premium System, Verification, Daily Limits, Force Subscribe, and much more.

---

## ✨ Features

### 🔐 Verification System
- Link Shortener based token verification
- Once verified, valid for exactly **24 hours** from the time of verification
- Can be turned **ON / OFF** via config
- Verified users get unlimited file access for 24 hours

### 👑 Premium System
- Admin can grant premium access for any number of days
- Premium users get **unlimited file access** with no verification needed
- No ads, no daily limits, no shortlinks
- Expiry tracked in MongoDB — restart-safe

### 📂 Daily Free File Limit
- Free users get a set number of files per day (configurable)
- Resets every day at **12:00 AM IST**
- Can be turned **ON / OFF** via config
- When limit is reached, user gets options to Verify or Buy Premium

### 📦 Batch File Support
- Generate a single link for multiple files
- Free users receive files up to their daily limit
- After limit is reached, bot shows how many files are remaining and prompts to Verify or Buy Premium

### 📢 Force Subscribe (Multiple Channels)
- Add unlimited Force Subscribe channels
- Bot checks each channel separately
- Only shows **unjoined** channel buttons to the user
- Includes a Retry button after joining

### 🔗 File Link Generation
- Generate shareable links for any file
- Protected links supported (file cannot be forwarded)
- Batch links for multiple files
- Optional personal URL shortener support per user

### 🗑️ Auto Delete
- Files auto-delete after a set time (configurable)
- Prevents copyright issues

### 📊 Stats (Admin)
- Total files stored
- Files added today (IST)
- Currently verified users
- Total users
- Total premium users

### 📡 Stream & Download (Optional)
- Online streaming support
- Fast download link generation

---

## ⚙️ Configuration Variables

| Variable | Description | Default |
|---|---|---|
| `API_ID` | Telegram API ID | - |
| `API_HASH` | Telegram API Hash | - |
| `BOT_TOKEN` | Bot Token from BotFather | - |
| `ADMINS` | Admin User IDs (space separated) | - |
| `BOT_USERNAME` | Bot username without @ | - |
| `DB_URI` | MongoDB connection URI | - |
| `DB_NAME` | MongoDB database name | `techvj` |
| `LOG_CHANNEL` | Channel ID for logs | - |
| `FORCE_SUB_MODE` | Enable Force Subscribe | `True` |
| `FORCE_SUB_CHANNELS` | Channel IDs (space separated) | - |
| `VERIFY_MODE` | Enable Verification | `True` |
| `SHORTLINK_API` | Shortlink API key | - |
| `SHORTLINK_URL` | Shortlink domain (without https://) | - |
| `VERIFY_TUTORIAL` | Tutorial link for verification | - |
| `DAILY_FILE_LIMIT_MODE` | Enable daily free file limit | `True` |
| `DAILY_FILE_LIMIT` | Number of free files per day | `1` |
| `PAYMENT_QR` | Payment QR code image URL | - |
| `PAYMENT_TEXT` | Premium plans text | - |
| `AUTO_DELETE_MODE` | Enable auto delete | `True` |
| `AUTO_DELETE` | Delete time in minutes | `30` |
| `AUTO_DELETE_TIME` | Delete time in seconds | `1800` |
| `STREAM_MODE` | Enable stream/download links | `False` |
| `PUBLIC_FILE_STORE` | Allow all users to generate links | `True` |
| `CLONE_MODE` | Enable clone bot feature | `False` |
| `PICS` | Start message photo URLs | - |

---

## 📋 Commands

### User Commands
| Command | Description |
|---|---|
| `/start` | Start the bot |
| `/plan` | View premium plans and pricing |
| `/myplan` | Check your current active plan |
| `/link` | Reply to a file to generate a shareable link |
| `/plink` | Reply to a file to generate a protected link |
| `/batch` | Generate a batch link for multiple files |
| `/pbatch` | Generate a protected batch link |
| `/api` | Set your personal shortener API key |
| `/base_site` | Set your personal shortener domain |

### Admin Commands
| Command | Description |
|---|---|
| `/stats` | View bot statistics |
| `/broadcast` | Broadcast a message to all users |
| `/addpremium [user_id] [days]` | Grant premium access |
| `/removepremium [user_id]` | Remove premium access |

---

## 🔄 How Verification Works

1. User clicks **Verify Now** button
2. Bot generates a shortlink (with ads)
3. User opens the shortlink and completes it
4. User gets redirected back to the bot and gets verified
5. Verification stays valid for **exactly 24 hours**
6. After 24 hours, user needs to verify again

---

## 💎 Free vs Premium

| Feature | Free | Premium |
|---|---|---|
| Files per day | Limited (configurable) | Unlimited |
| Verification required | Yes (every 24h) | Never |
| Ads / Shortlinks | Yes | No |
| Direct file access | No | Yes |
| Fast download & streaming | Yes | Yes |

---

## 🚀 Deployment

### Using Docker
```bash
docker build -t vj-file-store .
docker run vj-file-store
```

### Using Python
```bash
pip3 install -r requirements.txt
python3 bot.py
```

---

## 📌 Notes

- MongoDB is required for all data storage including users, premium, verification, and stats
- All times are based on **IST (Asia/Kolkata)**
- Daily file limit resets at **12:00 AM IST**
- Verification expiry is **exactly 24 hours** from the time of verification, not midnight
- Bot restart does **not** reset verification or premium — all data is in MongoDB
