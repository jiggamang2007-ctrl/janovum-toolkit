"""
Janovum Module — SMS / Signal Bot
Send and receive SMS via Twilio.
Can also integrate with Signal via signal-cli.

How it works:
  1. Client sends SMS to Twilio number
  2. Twilio webhook forwards to our server
  3. Claude processes the message
  4. Reply sent back via SMS

Requirements:
  pip install twilio (optional, can use REST API)
"""

import json
import os
import sys
import requests
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engine import call_claude, load_skill, build_system_prompt

MODULE_NAME = "sms_bot"
MODULE_DESC = "SMS Bot — client communication via text messages (Twilio)"


def send_sms(account_sid, auth_token, from_number, to_number, message):
    """Send an SMS via Twilio."""
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    data = {
        "From": from_number,
        "To": to_number,
        "Body": message
    }
    try:
        resp = requests.post(url, data=data, auth=(account_sid, auth_token))
        resp.raise_for_status()
        result = resp.json()
        return {"status": "sent", "sid": result.get("sid"), "to": to_number}
    except Exception as e:
        return {"error": str(e)}


def handle_incoming_sms(sms_data, client_config):
    """
    Handle incoming SMS from Twilio webhook.
    sms_data contains: From, Body, To, MessageSid
    """
    sender = sms_data.get("From", "unknown")
    text = sms_data.get("Body", "")

    print(f"[sms] Message from {sender}: {text}")

    # Process with Claude
    skill = load_skill("sms_bot")
    system_prompt = build_system_prompt(skill, client_config)
    messages = [{"role": "user", "content": text}]
    result = call_claude(messages, system_prompt=system_prompt)
    reply = result.get("text", "Sorry, I couldn't process that.")

    # SMS has 1600 char limit
    if len(reply) > 1500:
        reply = reply[:1500] + "..."

    # Send reply
    sms_config = client_config.get("sms", {})
    if sms_config.get("account_sid"):
        send_result = send_sms(
            sms_config["account_sid"],
            sms_config["auth_token"],
            sms_config["from_number"],
            sender,
            reply
        )
    else:
        send_result = {"error": "No SMS config"}

    return {
        "incoming": {"from": sender, "text": text},
        "reply": reply,
        "send_result": send_result
    }


# ── TOOL DEFINITIONS ──
TOOLS = [
    {
        "name": "sms_send",
        "description": "Send an SMS text message",
        "input_schema": {
            "type": "object",
            "properties": {
                "to_number": {"type": "string", "description": "Phone number to text (e.g. +1234567890)"},
                "message": {"type": "string", "description": "Message to send"}
            },
            "required": ["to_number", "message"]
        }
    }
]


def execute_tool(tool_name, tool_input, client_config=None):
    if tool_name == "sms_send":
        sms_config = (client_config or {}).get("sms", {})
        if not sms_config.get("account_sid"):
            return json.dumps({"error": "No SMS/Twilio config"})
        return json.dumps(send_sms(
            sms_config["account_sid"],
            sms_config["auth_token"],
            sms_config["from_number"],
            tool_input["to_number"],
            tool_input["message"]
        ))
    return json.dumps({"error": f"Unknown tool: {tool_name}"})
