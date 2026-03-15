"""
JANOVUM TELEGRAM BOT — SETUP
Run this ONCE after you:
  1. Created the bot with @BotFather
  2. Pasted the token in config.py
  3. Created "Janovum Alerts" channel
  4. Added the bot as admin to the channel
  5. Sent at least ONE message in the channel (any message)

This script finds your channel ID and saves it to config.py.
"""
import requests
import sys
import os

# Load config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import BOT_TOKEN, COMPANY_NAME

if BOT_TOKEN == "PASTE_YOUR_TOKEN_HERE" or not BOT_TOKEN:
    print("❌ You haven't pasted your bot token yet!")
    print("   Open config.py and paste the token from @BotFather")
    sys.exit(1)

API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Check bot is valid
print(f"🔍 Checking bot connection...")
r = requests.get(f"{API}/getMe")
if r.status_code != 200 or not r.json().get("ok"):
    print(f"❌ Invalid bot token. Double-check config.py")
    sys.exit(1)

bot_info = r.json()["result"]
print(f"✅ Connected to: @{bot_info['username']} ({bot_info['first_name']})")

# Get updates to find channel
print(f"🔍 Looking for your channel...")
r = requests.get(f"{API}/getUpdates")
data = r.json()

channel_id = None
channel_title = None

if data.get("ok"):
    for update in data.get("result", []):
        msg = update.get("message") or update.get("channel_post") or update.get("my_chat_member", {}).get("chat")
        if msg:
            chat = msg.get("chat") or msg
            if chat.get("type") in ("channel", "supergroup"):
                channel_id = chat["id"]
                channel_title = chat.get("title", "Unknown")
                break

if not channel_id:
    print("")
    print("⚠️  Couldn't find your channel automatically.")
    print("   Make sure you:")
    print("   1. Created the 'Janovum Alerts' channel")
    print("   2. Added the bot as an ADMIN")
    print("   3. Sent at least one message in the channel")
    print("")
    print("   Then run this script again.")
    print("")
    manual = input("   Or paste your channel ID manually (or press Enter to exit): ").strip()
    if manual:
        channel_id = manual
        channel_title = "Manual entry"
    else:
        sys.exit(1)

print(f"✅ Found channel: {channel_title} (ID: {channel_id})")

# Save to config
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.py")
with open(config_path, "r") as f:
    content = f.read()

content = content.replace('CHANNEL_ID = ""', f'CHANNEL_ID = "{channel_id}"')
with open(config_path, "w") as f:
    f.write(content)

print(f"✅ Channel ID saved to config.py")

# Send welcome message
welcome = f"""
◈ <b>JANOVUM ALERTS</b> — System Online

━━━━━━━━━━━━━━━━━━━━━━
🟢 Bot connected successfully
📡 Alerts channel is active
🔔 You'll receive notifications here:

  • System status alerts
  • Client updates
  • Payment notifications
  • Daily summaries
━━━━━━━━━━━━━━━━━━━━━━

<i>The Doorway to New Creation.</i>
"""

r = requests.post(f"{API}/sendMessage", json={
    "chat_id": channel_id,
    "text": welcome.strip(),
    "parse_mode": "HTML"
})

if r.status_code == 200 and r.json().get("ok"):
    print(f"✅ Welcome message sent to channel!")
    print(f"\n🎉 Setup complete! Your bot is ready.")
    print(f"   Run: python send_alert.py --test")
else:
    print(f"❌ Couldn't send message: {r.json()}")
    print(f"   Make sure the bot is an ADMIN in the channel")
