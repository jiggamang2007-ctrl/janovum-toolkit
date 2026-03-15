"""
Janovum Module — Discord Bot
Connects to Discord for client communication and team coordination.
Same director pattern as Telegram — routes messages to modules.

How it works:
  1. Client/team sends message in Discord channel or DM
  2. Bot receives message
  3. Routes to correct module based on command or context
  4. Claude processes and responds in Discord

Requirements:
  pip install discord.py
"""

import json
import os
import sys
import asyncio
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engine import call_claude, load_skill, build_system_prompt

MODULE_NAME = "discord_bot"
MODULE_DESC = "Discord Bot — client/team communication via Discord"


async def run_bot(token, client_config):
    """Start the Discord bot."""
    import discord
    from discord import Intents

    intents = Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"[discord] Bot ready as {client.user}")

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return

        text = message.content
        print(f"[discord] {message.author}: {text}")

        # Parse commands
        if text.lower().startswith("!"):
            cmd = text[1:].strip().lower()
            if cmd == "status":
                await message.channel.send("All systems operational.")
                return
            elif cmd == "help":
                await message.channel.send(
                    "Commands: !status, !search <query>, !scan, !help\n"
                    "Or just chat normally and I'll respond."
                )
                return
            elif cmd.startswith("search "):
                query = cmd[7:]
                try:
                    from modules.web_search import search
                    results = search(query, max_results=3)
                    reply = "\n".join([f"**{r['title']}**\n{r['url']}" for r in results if 'title' in r])
                    await message.channel.send(reply or "No results found.")
                except Exception as e:
                    await message.channel.send(f"Search error: {e}")
                return

        # Regular message — send to Claude
        skill = load_skill("discord_bot")
        system_prompt = build_system_prompt(skill, client_config)
        messages = [{"role": "user", "content": text}]
        result = call_claude(messages, system_prompt=system_prompt)
        reply = result.get("text", "I couldn't process that.")

        # Discord has 2000 char limit
        if len(reply) > 1900:
            chunks = [reply[i:i+1900] for i in range(0, len(reply), 1900)]
            for chunk in chunks:
                await message.channel.send(chunk)
        else:
            await message.channel.send(reply)

    await client.start(token)


def send_message(token, channel_id, message):
    """Send a message to a Discord channel via REST API."""
    import requests
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
    payload = {"content": message}
    try:
        resp = requests.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return {"status": "sent", "message_id": resp.json().get("id")}
    except Exception as e:
        return {"error": str(e)}


# ── TOOL DEFINITIONS ──
TOOLS = [
    {
        "name": "discord_send",
        "description": "Send a message to a Discord channel",
        "input_schema": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "Discord channel ID"},
                "message": {"type": "string", "description": "Message to send"}
            },
            "required": ["channel_id", "message"]
        }
    }
]


def execute_tool(tool_name, tool_input, client_config=None):
    if tool_name == "discord_send":
        token = (client_config or {}).get("discord", {}).get("bot_token", "")
        if not token:
            return json.dumps({"error": "No Discord bot token configured"})
        return json.dumps(send_message(token, tool_input["channel_id"], tool_input["message"]))
    return json.dumps({"error": f"Unknown tool: {tool_name}"})
