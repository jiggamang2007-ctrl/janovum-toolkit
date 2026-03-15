"""
Janovum Module — Multi-Channel Support
Unifies conversations across Telegram, WhatsApp, Discord, Slack, SMS, Email.
Same client, same conversation — any channel.

How it works:
  1. Message comes in from any channel
  2. Multi-channel identifies the client (by phone, email, or user ID)
  3. Loads their full conversation history (across all channels)
  4. Claude gets the full context regardless of which channel the client uses
  5. Reply goes back through the same channel it came from
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MODULE_NAME = "multi_channel"
MODULE_DESC = "Multi-Channel — unified conversations across Telegram, WhatsApp, Discord, Slack, SMS, Email"

# In-memory conversation store (production would use a database)
conversations = {}


def identify_client(channel, sender_id, client_config=None):
    """
    Identify a client across channels.
    Maps channel-specific IDs to a unified client ID.
    """
    # Check client config for identity mappings
    if client_config:
        identity_map = client_config.get("identity_map", {})
        for client_id, identities in identity_map.items():
            if identities.get(channel) == sender_id:
                return client_id
            # Also check by phone/email
            if channel in ("whatsapp", "sms") and identities.get("phone") == sender_id:
                return client_id
            if channel == "email" and identities.get("email") == sender_id:
                return client_id

    # Fallback: use channel:sender_id as client ID
    return f"{channel}:{sender_id}"


def get_conversation(client_id, limit=20):
    """Get a client's conversation history across all channels."""
    if client_id not in conversations:
        conversations[client_id] = []
    return conversations[client_id][-limit:]


def add_message(client_id, channel, role, content):
    """Add a message to a client's unified conversation."""
    if client_id not in conversations:
        conversations[client_id] = []

    entry = {
        "channel": channel,
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    }
    conversations[client_id].append(entry)

    # Keep conversations manageable
    if len(conversations[client_id]) > 200:
        conversations[client_id] = conversations[client_id][-100:]

    return entry


def build_claude_messages(client_id, limit=20):
    """
    Build Claude-compatible message list from unified conversation.
    Includes channel info so Claude knows where messages came from.
    """
    history = get_conversation(client_id, limit)
    messages = []

    for entry in history:
        channel_tag = f"[via {entry['channel']}] " if entry["channel"] else ""
        messages.append({
            "role": entry["role"],
            "content": f"{channel_tag}{entry['content']}"
        })

    return messages


def route_message(channel, sender_id, text, client_config=None):
    """
    Main entry point — route an incoming message through multi-channel.
    Returns the client_id and conversation context for Claude.
    """
    client_id = identify_client(channel, sender_id, client_config)

    # Add incoming message
    add_message(client_id, channel, "user", text)

    # Build context for Claude
    claude_messages = build_claude_messages(client_id)

    return {
        "client_id": client_id,
        "channel": channel,
        "messages": claude_messages,
        "history_length": len(conversations.get(client_id, []))
    }


def record_reply(client_id, channel, reply_text):
    """Record the bot's reply in the unified conversation."""
    add_message(client_id, channel, "assistant", reply_text)


def get_client_channels(client_id):
    """Get all channels a client has used."""
    history = conversations.get(client_id, [])
    channels = set(entry["channel"] for entry in history)
    return list(channels)


# ── TOOL DEFINITIONS ──
TOOLS = [
    {
        "name": "get_conversation_history",
        "description": "Get a client's unified conversation history across all channels",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "The client identifier"},
                "limit": {"type": "integer", "description": "Max messages to return", "default": 20}
            },
            "required": ["client_id"]
        }
    },
    {
        "name": "get_client_channels",
        "description": "See which channels a client has used",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "The client identifier"}
            },
            "required": ["client_id"]
        }
    }
]


def execute_tool(tool_name, tool_input):
    if tool_name == "get_conversation_history":
        history = get_conversation(tool_input["client_id"], tool_input.get("limit", 20))
        return json.dumps(history, default=str)
    elif tool_name == "get_client_channels":
        channels = get_client_channels(tool_input["client_id"])
        return json.dumps({"client_id": tool_input["client_id"], "channels": channels})
    return json.dumps({"error": f"Unknown tool: {tool_name}"})
