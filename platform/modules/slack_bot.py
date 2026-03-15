"""
Janovum Module — Slack Bot
Connects to Slack workspaces for business client communication.
Uses Slack Bot Token + Events API.

How it works:
  1. Client sends message in Slack channel or DM
  2. Events API webhook delivers message to our server
  3. Routes to Claude for processing
  4. Bot responds in the same channel/thread

Requirements:
  pip install slack-sdk (optional, can use REST API directly)
"""

import json
import os
import sys
import requests
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engine import call_claude, load_skill, build_system_prompt

MODULE_NAME = "slack_bot"
MODULE_DESC = "Slack Bot — business communication via Slack workspaces"


def send_message(bot_token, channel, text, thread_ts=None):
    """Send a message to a Slack channel."""
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {bot_token}",
        "Content-Type": "application/json"
    }
    payload = {"channel": channel, "text": text}
    if thread_ts:
        payload["thread_ts"] = thread_ts

    try:
        resp = requests.post(url, headers=headers, json=payload)
        data = resp.json()
        if data.get("ok"):
            return {"status": "sent", "ts": data.get("ts"), "channel": channel}
        return {"error": data.get("error", "Unknown Slack error")}
    except Exception as e:
        return {"error": str(e)}


def handle_event(event_data, client_config):
    """
    Handle a Slack event (message, app_mention, etc.)
    Called by the webhook receiver / server.
    """
    event = event_data.get("event", {})
    event_type = event.get("type", "")

    if event_type in ("message", "app_mention"):
        text = event.get("text", "")
        channel = event.get("channel", "")
        user = event.get("user", "")
        thread_ts = event.get("thread_ts") or event.get("ts")

        # Skip bot messages
        if event.get("bot_id"):
            return {"action": "skipped_bot_message"}

        print(f"[slack] {user} in {channel}: {text}")

        # Process with Claude
        skill = load_skill("slack_bot")
        system_prompt = build_system_prompt(skill, client_config)
        messages = [{"role": "user", "content": text}]
        result = call_claude(messages, system_prompt=system_prompt)
        reply = result.get("text", "I couldn't process that.")

        # Reply in thread
        bot_token = client_config.get("slack", {}).get("bot_token", "")
        if bot_token:
            send_result = send_message(bot_token, channel, reply, thread_ts)
            return {"reply": reply, "send_result": send_result}

        return {"reply": reply, "send_result": {"error": "No bot token"}}

    return {"action": "unhandled_event", "type": event_type}


def handle_slash_command(command, text, client_config):
    """Handle Slack slash commands (/janovum, etc.)."""
    if command == "/status":
        return {"response_type": "ephemeral", "text": "All Janovum systems operational."}
    elif command == "/search":
        try:
            from modules.web_search import search
            results = search(text, max_results=3)
            formatted = "\n".join([f"*{r['title']}*\n{r['url']}" for r in results if 'title' in r])
            return {"response_type": "in_channel", "text": formatted or "No results found."}
        except Exception as e:
            return {"response_type": "ephemeral", "text": f"Search error: {e}"}

    return {"response_type": "ephemeral", "text": f"Unknown command: {command}"}


# ── TOOL DEFINITIONS ──
TOOLS = [
    {
        "name": "slack_send",
        "description": "Send a message to a Slack channel",
        "input_schema": {
            "type": "object",
            "properties": {
                "channel": {"type": "string", "description": "Slack channel ID or name"},
                "message": {"type": "string", "description": "Message to send"},
                "thread_ts": {"type": "string", "description": "Thread timestamp to reply in thread"}
            },
            "required": ["channel", "message"]
        }
    }
]


def execute_tool(tool_name, tool_input, client_config=None):
    if tool_name == "slack_send":
        bot_token = (client_config or {}).get("slack", {}).get("bot_token", "")
        if not bot_token:
            return json.dumps({"error": "No Slack bot token configured"})
        return json.dumps(send_message(bot_token, tool_input["channel"],
                                       tool_input["message"], tool_input.get("thread_ts")))
    return json.dumps({"error": f"Unknown tool: {tool_name}"})
