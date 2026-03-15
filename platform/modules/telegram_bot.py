"""
Janovum Module — Telegram Bot Agent (Director)
This is the main entry point for clients. They talk to this bot on Telegram
and it routes their requests — including starting/stopping other modules.

How it works:
  1. Python bot listens 24/7 (free — just polling Telegram)
  2. Client sends a message
  3. If it's a command (start/stop a module), Python handles it directly
  4. If it's a question or task, sends to Claude API (pennies)
  5. Claude decides what to do, bot replies
  6. Back to listening (free)

Commands the client can send:
  "Start scanner"      → starts the ROI scanner module
  "Stop scanner"       → stops it
  "Start email"        → starts email auto-responder
  "Stop email"         → stops it
  "Status"             → shows which modules are running
  Any other message    → routed to Claude for a response

Requirements:
  pip install python-telegram-bot
  Set TELEGRAM_BOT_TOKEN in client config
"""

import asyncio
import json
import os
import sys
import threading
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engine import call_claude, agent_loop
from core.config import load_config

MODULE_NAME = "telegram_bot"
MODULE_DESC = "Telegram Bot Agent — the director that routes everything"


# ── MODULE REGISTRY ──
# Maps friendly names to module info so clients can say "start scanner"
MODULE_ALIASES = {
    "scanner": "roi_scanner",
    "roi": "roi_scanner",
    "roi scanner": "roi_scanner",
    "deal scanner": "roi_scanner",
    "email": "email_responder",
    "email responder": "email_responder",
    "auto reply": "email_responder",
    "lead": "lead_responder",
    "leads": "lead_responder",
    "lead responder": "lead_responder",
    "listing": "listing_poster",
    "listings": "listing_poster",
    "listing poster": "listing_poster",
}

# Track running modules: { module_name: { "thread": Thread, "running": bool, "started_at": timestamp } }
running_modules = {}


def get_system_prompt(client_name="", client_context="", active_modules=None):
    modules_text = ""
    if active_modules:
        modules_text = "\n\nCurrently active modules:\n" + "\n".join(f"  - {m}" for m in active_modules)

    return f"""You are a professional AI assistant created by Janovum.
You help manage business operations for the client.
Client: {client_name}
Context: {client_context}
{modules_text}

The client can control their AI tools through this chat:
- "Start [module name]" — starts a background module
- "Stop [module name]" — stops it
- "Status" — shows what's running

Available modules they can start/stop:
- Scanner / ROI Scanner — scans for best real estate deals 24/7
- Email / Email Responder — monitors inbox and auto-replies
- Lead / Lead Responder — instant lead qualification
- Listing / Listing Poster — create property listings from a message

For anything else, just help them with whatever they need.
Be helpful, professional, and concise."""


def parse_command(text):
    """
    Parse a message for start/stop/status commands.
    Returns (command, module_name) or (None, None) if not a command.
    """
    text = text.strip().lower()

    # Status check
    if text in ["status", "what's running", "whats running", "modules", "running"]:
        return ("status", None)

    # Start/Stop commands
    for prefix in ["start ", "stop ", "turn on ", "turn off ", "enable ", "disable "]:
        if text.startswith(prefix):
            action = "start" if prefix.strip() in ["start", "turn on", "enable"] else "stop"
            module_text = text[len(prefix):].strip().rstrip(".")

            # Look up the module name
            if module_text in MODULE_ALIASES:
                return (action, MODULE_ALIASES[module_text])

            # Try partial match
            for alias, mod_name in MODULE_ALIASES.items():
                if module_text in alias or alias in module_text:
                    return (action, mod_name)

            return (action, module_text)  # Unknown module, we'll handle it

    return (None, None)


def get_status_text():
    """Generate a status message showing which modules are running."""
    if not running_modules:
        return "No modules are currently running.\n\nYou can start one by saying:\n- \"Start scanner\"\n- \"Start email\"\netc."

    lines = ["Currently running modules:\n"]
    for name, info in running_modules.items():
        if info.get("running"):
            elapsed = time.time() - info.get("started_at", time.time())
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
            lines.append(f"  {name} — running for {time_str}")

    lines.append("\nSay \"Stop [name]\" to stop any module.")
    return "\n".join(lines)


def start_background_module(module_name, client_config, send_message_fn):
    """Start a module in a background thread."""
    if module_name in running_modules and running_modules[module_name].get("running"):
        return f"{module_name} is already running."

    def run_module():
        try:
            if module_name == "roi_scanner":
                from modules.roi_scanner import run_scan
                while running_modules.get(module_name, {}).get("running"):
                    results = run_scan(client_config)
                    deals = results.get("deals", [])
                    if deals:
                        top = deals[0]
                        msg = f"ROI Scanner found {len(deals)} deals!\n\nTop deal: {top.get('address', 'N/A')}\nPrice: ${top.get('price', 0):,.0f}\nCap Rate: {top.get('roi', {}).get('cap_rate', 'N/A')}%"
                        asyncio.run_coroutine_threadsafe(send_message_fn(msg), loop)
                    # Wait before next scan (default: every 30 minutes)
                    interval = client_config.get("scan_interval", 1800)
                    for _ in range(interval):
                        if not running_modules.get(module_name, {}).get("running"):
                            break
                        time.sleep(1)

            elif module_name == "email_responder":
                from modules.email_responder import run_loop
                # Patch the loop to check running state
                run_loop(client_config, check_interval=60)

            else:
                print(f"[telegram_bot] Unknown module to run: {module_name}")

        except Exception as e:
            print(f"[telegram_bot] Module {module_name} error: {e}")
        finally:
            running_modules[module_name] = {"running": False}

    running_modules[module_name] = {
        "running": True,
        "started_at": time.time(),
        "thread": threading.Thread(target=run_module, daemon=True)
    }
    running_modules[module_name]["thread"].start()

    return f"Started {module_name}! It's now running in the background. Say \"Stop {module_name.replace('_', ' ')}\" whenever you want to stop it."


def stop_background_module(module_name):
    """Stop a running background module."""
    if module_name not in running_modules or not running_modules[module_name].get("running"):
        return f"{module_name} is not currently running."

    elapsed = time.time() - running_modules[module_name].get("started_at", time.time())
    hours = int(elapsed // 3600)
    minutes = int((elapsed % 3600) // 60)
    time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

    running_modules[module_name]["running"] = False
    return f"Stopped {module_name}. It ran for {time_str}."


# Global event loop reference for cross-thread messaging
loop = None


async def run(client_config):
    """
    Start the Telegram bot for a specific client.

    client_config should have:
      - telegram_token: the bot token from BotFather
      - client_name: business name
      - client_context: what the business does
    """
    global loop
    loop = asyncio.get_event_loop()

    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    except ImportError:
        print("[telegram_bot] python-telegram-bot not installed. Run: pip install python-telegram-bot")
        return

    token = client_config.get("telegram_token", "")
    if not token:
        print("[telegram_bot] No telegram_token in client config.")
        return

    client_name = client_config.get("client_name", "Client")
    client_context = client_config.get("client_context", "")

    # Conversation history per chat
    conversations = {}

    # Function to send messages from background threads
    app = Application.builder().token(token).build()
    bot = app.bot
    notify_chat_id = client_config.get("notify_chat_id", None)

    async def send_notification(text):
        if notify_chat_id:
            await bot.send_message(chat_id=notify_chat_id, text=text)

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        nonlocal notify_chat_id
        chat_id = update.effective_chat.id
        user_msg = update.message.text

        # Save chat_id for notifications
        if not notify_chat_id:
            notify_chat_id = chat_id
            client_config["notify_chat_id"] = chat_id

        # Check for start/stop/status commands first
        command, module_name = parse_command(user_msg)

        if command == "status":
            await update.message.reply_text(get_status_text())
            return

        if command == "start" and module_name:
            result = start_background_module(module_name, client_config, send_notification)
            await update.message.reply_text(result)
            return

        if command == "stop" and module_name:
            result = stop_background_module(module_name)
            await update.message.reply_text(result)
            return

        # Check if this is a listing request
        listing_keywords = ["list ", "post listing", "create listing", "add listing"]
        if any(user_msg.lower().startswith(k) for k in listing_keywords):
            await update.message.reply_text("Creating listing... one moment.")
            try:
                from modules.listing_poster import create_listing
                result = create_listing(user_msg, client_config)
                if "error" in result:
                    await update.message.reply_text(f"Error: {result['error']}")
                else:
                    await update.message.reply_text(
                        f"Listing created!\n\n"
                        f"Address: {result['listing_data'].get('address', 'N/A')}\n"
                        f"Price: ${result['listing_data'].get('price', 0):,.0f}\n"
                        f"File: {result.get('filename', 'saved')}\n\n"
                        f"{result.get('description', '')}"
                    )
            except Exception as e:
                await update.message.reply_text(f"Error creating listing: {str(e)}")
            return

        # Regular message — send to Claude
        if chat_id not in conversations:
            conversations[chat_id] = []

        conversations[chat_id].append({"role": "user", "content": user_msg})

        # Keep last 20 messages
        if len(conversations[chat_id]) > 20:
            conversations[chat_id] = conversations[chat_id][-20:]

        active = [n for n, i in running_modules.items() if i.get("running")]
        system_prompt = get_system_prompt(client_name, client_context, active)

        result = call_claude(conversations[chat_id], system_prompt=system_prompt)

        if "error" in result:
            reply = f"Sorry, I'm having a technical issue: {result['error']}"
        else:
            reply = result.get("text", "I didn't get a response. Try again.")
            conversations[chat_id].append({"role": "assistant", "content": reply})

        await update.message.reply_text(reply)

    async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        nonlocal notify_chat_id
        notify_chat_id = update.effective_chat.id
        client_config["notify_chat_id"] = notify_chat_id

        await update.message.reply_text(
            f"Hey! I'm the AI assistant for {client_name}, powered by Janovum.\n\n"
            f"You can:\n"
            f"  - Ask me anything\n"
            f"  - \"Start scanner\" — start the ROI deal scanner\n"
            f"  - \"Stop scanner\" — stop it\n"
            f"  - \"Start email\" — start email auto-responder\n"
            f"  - \"Status\" — see what's running\n"
            f"  - \"List [address] for [price]\" — create a property listing\n\n"
            f"Send me any message and I'll help you out!"
        )

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print(f"[telegram_bot] Running for {client_name}...")
    print(f"[telegram_bot] Clients can start/stop modules via Telegram messages")
    await app.run_polling()


def start(client_config):
    """Synchronous entry point."""
    asyncio.run(run(client_config))


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "../clients/example.json"
    if os.path.exists(config_path):
        with open(config_path) as f:
            cfg = json.load(f)
        start(cfg)
    else:
        print(f"Config not found: {config_path}")
        print("Create a client config with telegram_token, client_name, client_context")
