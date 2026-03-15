"""
Discord Assistant Bot
AI assistant that responds in Discord channels using Pollinations text API.
Requires a Discord bot token in config.
"""

import sys
import os
import json
import time
import logging
import urllib.parse
import asyncio
import threading
from pathlib import Path
from datetime import datetime

PLATFORM_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLATFORM_DIR))

try:
    from core.api_router import generate_text_free
except ImportError:
    generate_text_free = None

import requests

BOT_INFO = {
    "name": "Discord Assistant",
    "category": "messaging",
    "description": "AI assistant that responds in Discord channels",
    "icon": "\U0001f4ac",
    "version": "1.0",
    "author": "Janovum",
    "config_schema": {
        "discord_bot_token": {"type": "str", "default": ""},
        "command_prefix": {"type": "str", "default": "!"},
        "ai_trigger": {"type": "str", "default": "!ask"},
        "respond_to_mentions": {"type": "bool", "default": True},
        "allowed_channels": {"type": "list", "default": []},
        "max_response_length": {"type": "int", "default": 1900},
        "system_prompt": {"type": "str", "default": "You are a helpful AI assistant in a Discord server. Be concise, friendly, and helpful. Keep responses under 300 words."},
        "conversation_memory": {"type": "int", "default": 5},
        "cooldown_seconds": {"type": "int", "default": 3},
    }
}

_running = False
_status = {"state": "stopped", "messages_handled": 0, "last_message": None, "errors": [], "connected": False}
_logger = logging.getLogger("DiscordAssistant")
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    _logger.addHandler(logging.StreamHandler())

DATA_DIR = PLATFORM_DIR / "data" / "bots" / "discord_assistant"
CONVERSATION_LOG = DATA_DIR / "conversation_log.json"

# Simple in-memory conversation history per channel
_channel_history = {}
_last_response_time = {}


def _ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _call_ai(prompt, system_prompt=""):
    """Call Pollinations text API for AI response."""
    full_prompt = f"{system_prompt}\n\nUser: {prompt}\n\nAssistant:" if system_prompt else prompt

    try:
        if generate_text_free:
            result = generate_text_free(full_prompt)
            return result.get("text", "").strip()
        else:
            encoded = urllib.parse.quote(full_prompt)
            url = f"https://text.pollinations.ai/{encoded}"
            resp = requests.get(url, headers={"User-Agent": "Janovum/1.0"}, timeout=60)
            if resp.status_code == 200:
                return resp.text.strip()
    except Exception as e:
        _logger.error(f"AI call failed: {e}")

    return "Sorry, I'm having trouble thinking right now. Please try again in a moment."


def _build_context(channel_id, new_message, config):
    """Build conversation context from channel history."""
    memory_size = config.get("conversation_memory", 5)
    history = _channel_history.get(channel_id, [])

    context_parts = []
    for entry in history[-memory_size:]:
        context_parts.append(f"User ({entry['author']}): {entry['content']}")
        if entry.get("response"):
            context_parts.append(f"Assistant: {entry['response']}")

    context_parts.append(f"User: {new_message}")
    return "\n".join(context_parts)


def _log_conversation(channel_id, author, content, response):
    """Log a conversation exchange."""
    if channel_id not in _channel_history:
        _channel_history[channel_id] = []

    _channel_history[channel_id].append({
        "author": author,
        "content": content,
        "response": response,
        "timestamp": datetime.now().isoformat(),
    })

    # Keep history manageable
    if len(_channel_history[channel_id]) > 50:
        _channel_history[channel_id] = _channel_history[channel_id][-50:]


def _save_conversation_log():
    """Save all conversation history to disk."""
    _ensure_dirs()
    try:
        # Flatten all channel histories
        all_convos = []
        for channel_id, history in _channel_history.items():
            for entry in history:
                entry["channel_id"] = channel_id
                all_convos.append(entry)

        CONVERSATION_LOG.write_text(json.dumps(all_convos[-500:], indent=2, default=str), encoding="utf-8")
    except Exception as e:
        _logger.error(f"Failed to save conversation log: {e}")


def _run_with_discord_py(config):
    """Run using discord.py library."""
    try:
        import discord
    except ImportError:
        raise Exception("discord.py not installed. Run: pip install discord.py")

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    token = config.get("discord_bot_token") or os.environ.get("DISCORD_BOT_TOKEN", "")
    if not token:
        raise Exception("Discord bot token not configured. Set discord_bot_token in config or DISCORD_BOT_TOKEN env var.")

    prefix = config.get("command_prefix", "!")
    ai_trigger = config.get("ai_trigger", "!ask")
    respond_to_mentions = config.get("respond_to_mentions", True)
    allowed_channels = config.get("allowed_channels", [])
    max_length = config.get("max_response_length", 1900)
    system_prompt = config.get("system_prompt", "")
    cooldown = config.get("cooldown_seconds", 3)

    @client.event
    async def on_ready():
        global _status
        _status["connected"] = True
        _status["state"] = "connected"
        _logger.info(f"Discord bot connected as {client.user}")
        _logger.info(f"Serving {len(client.guilds)} guild(s)")

    @client.event
    async def on_message(message):
        global _status

        # Don't respond to self
        if message.author == client.user:
            return

        if not _running:
            return

        channel_id = str(message.channel.id)

        # Check channel restrictions
        if allowed_channels and channel_id not in allowed_channels:
            return

        content = message.content.strip()
        should_respond = False
        query = ""

        # Check if it's an AI trigger command
        if content.lower().startswith(ai_trigger.lower()):
            query = content[len(ai_trigger):].strip()
            should_respond = True

        # Check if the bot was mentioned
        elif respond_to_mentions and client.user.mentioned_in(message):
            query = content.replace(f"<@{client.user.id}>", "").replace(f"<@!{client.user.id}>", "").strip()
            should_respond = True

        # Built-in commands
        elif content.lower() == f"{prefix}help":
            help_text = (
                f"**AI Assistant Commands:**\n"
                f"`{ai_trigger} <question>` - Ask me anything\n"
                f"`{prefix}help` - Show this help\n"
                f"`{prefix}status` - Bot status\n"
                f"`{prefix}clear` - Clear conversation history\n"
                f"You can also mention me to ask a question!"
            )
            await message.channel.send(help_text)
            return

        elif content.lower() == f"{prefix}status":
            uptime = _status.get("state", "unknown")
            msgs = _status.get("messages_handled", 0)
            await message.channel.send(f"Status: {uptime} | Messages handled: {msgs}")
            return

        elif content.lower() == f"{prefix}clear":
            _channel_history[channel_id] = []
            await message.channel.send("Conversation history cleared!")
            return

        if not should_respond or not query:
            return

        # Cooldown check
        now = time.time()
        last = _last_response_time.get(channel_id, 0)
        if now - last < cooldown:
            return

        _last_response_time[channel_id] = now

        try:
            # Show typing indicator
            async with message.channel.typing():
                # Build context with conversation history
                context = _build_context(channel_id, query, config)
                full_prompt = f"{system_prompt}\n\n{context}\n\nAssistant:" if system_prompt else context

                # Call AI (in thread to not block event loop)
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, _call_ai, full_prompt, "")

                # Truncate if needed
                if len(response) > max_length:
                    response = response[:max_length - 3] + "..."

                # Send response
                await message.channel.send(response)

                # Log conversation
                _log_conversation(channel_id, str(message.author), query, response)
                _status["messages_handled"] += 1
                _status["last_message"] = datetime.now().isoformat()

                _logger.info(f"Responded to {message.author} in #{message.channel.name}")

        except Exception as e:
            _logger.error(f"Error handling message: {e}")
            _status["errors"].append(str(e))
            try:
                await message.channel.send("Sorry, I encountered an error. Please try again.")
            except Exception:
                pass

    # Run the bot
    async def _start():
        try:
            await client.start(token)
        except Exception as e:
            _logger.error(f"Discord connection error: {e}")
            _status["errors"].append(str(e))
            _status["state"] = "error"

    # Handle graceful shutdown
    async def _stop_client():
        _save_conversation_log()
        await client.close()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(_start())
    except KeyboardInterrupt:
        loop.run_until_complete(_stop_client())
    finally:
        _save_conversation_log()
        loop.close()


def _run_polling_fallback(config):
    """
    Fallback mode without discord.py: polls a webhook or local command file.
    Useful for testing without a Discord connection.
    """
    global _status
    _logger.info("Running in polling/local mode (no Discord connection)")
    _status["state"] = "polling_mode"

    commands_file = DATA_DIR / "pending_commands.json"

    while _running:
        try:
            if commands_file.exists():
                commands = json.loads(commands_file.read_text(encoding="utf-8"))
                new_commands = []

                for cmd in commands:
                    if cmd.get("processed"):
                        continue

                    query = cmd.get("query", "")
                    if query:
                        _logger.info(f"Processing command: {query[:50]}...")
                        system_prompt = config.get("system_prompt", "")
                        response = _call_ai(query, system_prompt)

                        cmd["response"] = response
                        cmd["processed"] = True
                        cmd["processed_at"] = datetime.now().isoformat()
                        _status["messages_handled"] += 1

                        _logger.info(f"Response: {response[:100]}...")

                    new_commands.append(cmd)

                commands_file.write_text(json.dumps(new_commands, indent=2, default=str), encoding="utf-8")

        except Exception as e:
            _logger.error(f"Polling error: {e}")

        for _ in range(5):
            if not _running:
                break
            time.sleep(1)


def run(config=None):
    """Start the Discord assistant bot."""
    global _running, _status
    _running = True
    _ensure_dirs()

    if config is None:
        config = {v: s["default"] for v, s in BOT_INFO["config_schema"].items()}

    _status = {"state": "starting", "messages_handled": 0, "last_message": None, "errors": [], "connected": False}
    _logger.info("Discord Assistant starting...")

    token = config.get("discord_bot_token") or os.environ.get("DISCORD_BOT_TOKEN", "")

    if token:
        try:
            _run_with_discord_py(config)
        except ImportError:
            _logger.warning("discord.py not installed. Falling back to polling mode.")
            _run_polling_fallback(config)
        except Exception as e:
            _logger.error(f"Discord bot error: {e}")
            _status["errors"].append(str(e))
            _logger.info("Falling back to polling mode...")
            _run_polling_fallback(config)
    else:
        _logger.warning("No Discord bot token configured. Running in local polling mode.")
        _run_polling_fallback(config)

    _status["state"] = "stopped"
    _save_conversation_log()
    _logger.info("Discord Assistant stopped.")


def stop():
    """Stop the bot."""
    global _running
    _running = False
    _status["state"] = "stopping"


def get_status():
    return {**_status}


# ── Helper for local testing ──

def ask(question):
    """Ask the AI directly without Discord, for testing."""
    _ensure_dirs()
    system_prompt = BOT_INFO["config_schema"]["system_prompt"]["default"]
    response = _call_ai(question, system_prompt)
    print(f"Q: {question}")
    print(f"A: {response}")
    return response


if __name__ == "__main__":
    # If run directly with an argument, use ask mode
    if len(sys.argv) > 1 and sys.argv[1] == "--ask":
        question = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Hello, how are you?"
        ask(question)
    else:
        try:
            run()
        except KeyboardInterrupt:
            stop()
