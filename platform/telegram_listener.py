"""
Janovum — Telegram Listener
Listens for messages on Telegram, forwards them to the Director agent.
The Director analyzes each message and routes it to the right bot.

Flow:
  Telegram message → This listener → Director.process_message() → Bot runs → Reply sent back

Usage:
  python telegram_listener.py                    (standalone mode — direct Director calls)
  python telegram_listener.py --server           (server mode — sends to Flask API)

Requires: pip install requests
"""

import os
import sys
import json
import time
import requests
from datetime import datetime

# Setup paths
PLATFORM_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(PLATFORM_DIR)
TELEGRAM_DIR = os.path.join(PARENT_DIR, "telegram_bot")
sys.path.insert(0, PLATFORM_DIR)
sys.path.insert(0, TELEGRAM_DIR)

# Load Telegram config
from config import BOT_TOKEN, CHANNEL_ID, OWNER_NAME

API = f"https://api.telegram.org/bot{BOT_TOKEN}"
SERVER_URL = "http://localhost:5050"


def get_updates(offset=None, timeout=30):
    """Long-poll Telegram for new messages."""
    params = {"timeout": timeout, "allowed_updates": '["message"]'}
    if offset:
        params["offset"] = offset
    try:
        resp = requests.get(f"{API}/getUpdates", params=params, timeout=timeout + 5)
        if resp.status_code == 200:
            return resp.json().get("result", [])
    except Exception as e:
        print(f"[telegram] Poll error: {e}")
        time.sleep(3)
    return []


def send_reply(chat_id, text, reply_to=None):
    """Send a reply back to Telegram."""
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    try:
        resp = requests.post(f"{API}/sendMessage", json=payload, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


def send_channel_alert(text):
    """Send an alert to the Janovum Alerts channel."""
    if not CHANNEL_ID:
        return
    try:
        requests.post(f"{API}/sendMessage", json={
            "chat_id": CHANNEL_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }, timeout=10)
    except Exception:
        pass


def format_director_response(result):
    """Format Director's response for Telegram (HTML)."""
    action = result.get("action", "")
    response = result.get("response", "No response")
    bot_id = result.get("bot_id", "")
    confidence = result.get("confidence")

    # Add action indicator
    if action == "auto_started":
        header = f"🤖 <b>Director → {bot_id.replace('_', ' ').title()}</b>"
        if confidence:
            header += f" ({int(confidence * 100)}% match)"
        return f"{header}\n\n{response}"
    elif action in ("started", "stopped"):
        icon = "▶️" if action == "started" else "⏹"
        return f"{icon} {response}"
    elif action == "status":
        return f"📊 {response}"
    elif action == "list_bots":
        return f"📋 {response}"
    elif action == "help":
        return f"ℹ️ {response}"
    elif action == "ai_response":
        return f"💬 {response}"
    else:
        return response


def process_via_director(message_text, chat_id, source="telegram"):
    """Process message directly through the Director (standalone mode)."""
    from core.director import get_director
    director = get_director()
    result = director.process_message(message_text, source=source, metadata={"chat_id": chat_id})
    return result


def process_via_server(message_text, chat_id, source="telegram"):
    """Process message through the Flask server API (server mode)."""
    try:
        resp = requests.post(f"{SERVER_URL}/api/director/process", json={
            "message": message_text,
            "source": source,
            "metadata": {"chat_id": chat_id}
        }, timeout=60)
        if resp.status_code == 200:
            return resp.json()
        return {"response": f"Server error: {resp.status_code}", "action": "error"}
    except requests.ConnectionError:
        return {"response": "Server offline. Start it with: python server_v5.py", "action": "error"}
    except Exception as e:
        return {"response": f"Error: {e}", "action": "error"}


def run_listener(use_server=False):
    """Main listener loop — polls Telegram and routes messages through Director."""
    print()
    print("=" * 55)
    print("  JANOVUM TELEGRAM LISTENER")
    print("=" * 55)
    print(f"  Mode:    {'Server API' if use_server else 'Direct (standalone)'}")
    print(f"  Bot:     {BOT_TOKEN[:20]}...")
    print(f"  Channel: {CHANNEL_ID}")
    print(f"  Owner:   {OWNER_NAME}")
    print()
    print("  Listening for messages... (Ctrl+C to stop)")
    print("=" * 55)
    print()

    # Notify channel that listener is online
    send_channel_alert(f"""
🟢 <b>DIRECTOR ONLINE</b>
━━━━━━━━━━━━━━━━━━━━━━
🧠 Janovum Director is listening
📱 Send messages here or DM the bot
🕐 {datetime.now().strftime("%m/%d/%Y %I:%M %p")}
━━━━━━━━━━━━━━━━━━━━━━
◈ <i>Janovum</i>
""")

    offset = None
    message_count = 0

    while True:
        try:
            updates = get_updates(offset=offset)

            for update in updates:
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                text = msg.get("text", "").strip()
                chat_id = msg.get("chat", {}).get("id")
                user = msg.get("from", {})
                username = user.get("username", user.get("first_name", "Unknown"))

                if not text or not chat_id:
                    continue

                message_count += 1
                print(f"[{datetime.now().strftime('%H:%M:%S')}] #{message_count} @{username}: {text[:80]}")

                # Route through Director
                if use_server:
                    result = process_via_server(text, chat_id)
                else:
                    result = process_via_director(text, chat_id)

                # Format and send reply
                reply = format_director_response(result)
                send_reply(chat_id, reply, reply_to=msg.get("message_id"))

                action = result.get("action", "")
                bot_id = result.get("bot_id", "")
                print(f"  → Action: {action}" + (f" | Bot: {bot_id}" if bot_id else ""))

                # Alert channel about bot activations
                if action in ("auto_started", "started"):
                    send_channel_alert(f"""
🤖 <b>BOT ACTIVATED</b>
━━━━━━━━━━━━━━━━━━━━━━
▶️ <b>{bot_id.replace('_', ' ').title()}</b>
👤 Triggered by: @{username}
💬 "{text[:100]}"
🕐 {datetime.now().strftime("%m/%d/%Y %I:%M %p")}
━━━━━━━━━━━━━━━━━━━━━━
◈ <i>Janovum</i>
""")

        except KeyboardInterrupt:
            print("\n[telegram] Shutting down...")
            send_channel_alert(f"""
🔴 <b>DIRECTOR OFFLINE</b>
━━━━━━━━━━━━━━━━━━━━━━
📴 Listener stopped
📊 Messages processed: {message_count}
🕐 {datetime.now().strftime("%m/%d/%Y %I:%M %p")}
━━━━━━━━━━━━━━━━━━━━━━
◈ <i>Janovum</i>
""")
            break
        except Exception as e:
            print(f"[telegram] Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Janovum Telegram Listener")
    parser.add_argument("--server", action="store_true", help="Use Flask server API instead of direct Director calls")
    args = parser.parse_args()
    run_listener(use_server=args.server)
