"""
Janovum Module — WhatsApp Bot
Connects to WhatsApp Business API (or Twilio) to communicate with clients.
Huge for business clients — WhatsApp has 2B+ users.

How it works:
  1. Client sends message via WhatsApp
  2. Webhook receives the message
  3. Routes to correct module (like Telegram director)
  4. Claude processes and responds
  5. Reply sent back via WhatsApp API

Requirements:
  pip install twilio (for Twilio WhatsApp)
  OR use WhatsApp Business Cloud API directly
"""

import json
import os
import sys
import requests
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engine import call_claude, load_skill, build_system_prompt

MODULE_NAME = "whatsapp_bot"
MODULE_DESC = "WhatsApp Bot — client communication via WhatsApp Business API"


class WhatsAppBot:
    def __init__(self, config):
        """
        config should include:
          - provider: "twilio" or "cloud_api"
          - For Twilio: account_sid, auth_token, from_number
          - For Cloud API: phone_number_id, access_token
        """
        self.config = config
        self.provider = config.get("provider", "twilio")

    def send_message(self, to_number, message):
        """Send a WhatsApp message."""
        if self.provider == "twilio":
            return self._send_twilio(to_number, message)
        elif self.provider == "cloud_api":
            return self._send_cloud_api(to_number, message)
        return {"error": f"Unknown provider: {self.provider}"}

    def _send_twilio(self, to_number, message):
        """Send via Twilio WhatsApp API."""
        try:
            from twilio.rest import Client
            client = Client(self.config["account_sid"], self.config["auth_token"])
            msg = client.messages.create(
                from_=f'whatsapp:{self.config["from_number"]}',
                body=message,
                to=f'whatsapp:{to_number}'
            )
            return {"status": "sent", "sid": msg.sid}
        except ImportError:
            return self._send_twilio_http(to_number, message)
        except Exception as e:
            return {"error": str(e)}

    def _send_twilio_http(self, to_number, message):
        """Send via Twilio REST API without SDK."""
        url = f'https://api.twilio.com/2010-04-01/Accounts/{self.config["account_sid"]}/Messages.json'
        data = {
            "From": f'whatsapp:{self.config["from_number"]}',
            "Body": message,
            "To": f'whatsapp:{to_number}'
        }
        try:
            resp = requests.post(url, data=data,
                                 auth=(self.config["account_sid"], self.config["auth_token"]))
            resp.raise_for_status()
            return {"status": "sent", "sid": resp.json().get("sid")}
        except Exception as e:
            return {"error": str(e)}

    def _send_cloud_api(self, to_number, message):
        """Send via WhatsApp Business Cloud API (Meta)."""
        url = f'https://graph.facebook.com/v18.0/{self.config["phone_number_id"]}/messages'
        headers = {
            "Authorization": f'Bearer {self.config["access_token"]}',
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {"body": message}
        }
        try:
            resp = requests.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return {"status": "sent", "message_id": resp.json().get("messages", [{}])[0].get("id")}
        except Exception as e:
            return {"error": str(e)}


def handle_incoming(message_data, client_config):
    """
    Handle an incoming WhatsApp message.
    Called by the webhook receiver.
    """
    sender = message_data.get("from", "unknown")
    text = message_data.get("text", "")
    timestamp = message_data.get("timestamp", datetime.now().isoformat())

    print(f"[whatsapp] Message from {sender}: {text}")

    # Build context
    skill = load_skill("whatsapp_bot")
    system_prompt = build_system_prompt(skill, client_config)

    messages = [{"role": "user", "content": text}]
    result = call_claude(messages, system_prompt=system_prompt)

    reply = result.get("text", "Sorry, I couldn't process that.")

    # Send reply
    bot = WhatsAppBot(client_config.get("whatsapp", {}))
    send_result = bot.send_message(sender, reply)

    return {
        "incoming": {"from": sender, "text": text, "timestamp": timestamp},
        "reply": reply,
        "send_result": send_result
    }


# ── TOOL DEFINITIONS ──
TOOLS = [
    {
        "name": "whatsapp_send",
        "description": "Send a WhatsApp message to a phone number",
        "input_schema": {
            "type": "object",
            "properties": {
                "to_number": {"type": "string", "description": "Phone number with country code (e.g. +1234567890)"},
                "message": {"type": "string", "description": "Message text to send"}
            },
            "required": ["to_number", "message"]
        }
    },
    {
        "name": "whatsapp_reply",
        "description": "Reply to the current WhatsApp conversation",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Reply message"}
            },
            "required": ["message"]
        }
    }
]


def execute_tool(tool_name, tool_input, client_config=None):
    if tool_name == "whatsapp_send":
        if not client_config:
            return json.dumps({"error": "No WhatsApp config provided"})
        bot = WhatsAppBot(client_config.get("whatsapp", {}))
        return json.dumps(bot.send_message(tool_input["to_number"], tool_input["message"]))
    elif tool_name == "whatsapp_reply":
        return json.dumps({"status": "queued", "message": tool_input["message"]})
    return json.dumps({"error": f"Unknown tool: {tool_name}"})
