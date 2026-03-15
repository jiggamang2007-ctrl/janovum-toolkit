"""
Janovum Module — Webhook Receiver
Receives data from external services (Zapier, IFTTT, CRMs, payment processors, etc.)
and routes it to the appropriate module for processing.

How it works:
  1. External service sends POST to our webhook endpoint
  2. Python validates the payload (optional secret/signature)
  3. Routes to correct handler based on source or type
  4. Claude processes if reasoning is needed
  5. Result stored or forwarded to client
"""

import json
import os
import sys
import hashlib
import hmac
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MODULE_NAME = "webhook_receiver"
MODULE_DESC = "Webhook Receiver — accept data from external services (Zapier, CRMs, etc.)"

# Store received webhooks
webhook_log = []


def verify_signature(payload_body, signature, secret):
    """Verify webhook signature (HMAC-SHA256)."""
    expected = hmac.new(secret.encode(), payload_body.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


def process_webhook(source, payload, client_config=None):
    """
    Process an incoming webhook.

    source: identifier for the sending service (zapier, stripe, crm, custom)
    payload: the JSON data received
    """
    entry = {
        "source": source,
        "payload": payload,
        "received_at": datetime.now().isoformat(),
        "processed": False
    }

    # Route based on source
    if source == "stripe" or source == "payment":
        result = handle_payment_webhook(payload, client_config)
    elif source == "crm" or source == "lead":
        result = handle_lead_webhook(payload, client_config)
    elif source == "zapier":
        result = handle_zapier_webhook(payload, client_config)
    elif source == "form":
        result = handle_form_submission(payload, client_config)
    else:
        result = handle_generic_webhook(payload, client_config)

    entry["result"] = result
    entry["processed"] = True
    webhook_log.append(entry)

    # Keep log manageable
    if len(webhook_log) > 1000:
        webhook_log.pop(0)

    return result


def handle_payment_webhook(payload, client_config=None):
    """Handle payment notifications (Stripe, PayPal, etc.)."""
    event_type = payload.get("type", "unknown")
    amount = payload.get("data", {}).get("object", {}).get("amount", 0)
    currency = payload.get("data", {}).get("object", {}).get("currency", "usd")

    return {
        "handler": "payment",
        "event_type": event_type,
        "amount": amount / 100 if amount else 0,
        "currency": currency,
        "action": "logged"
    }


def handle_lead_webhook(payload, client_config=None):
    """Handle new lead notifications from CRM."""
    lead = {
        "name": payload.get("name", payload.get("contact_name", "Unknown")),
        "email": payload.get("email", ""),
        "phone": payload.get("phone", ""),
        "source": payload.get("source", "webhook"),
        "message": payload.get("message", payload.get("notes", ""))
    }

    # Route to lead responder if available
    try:
        from modules.lead_responder import qualify_lead
        qualification = qualify_lead(lead)
        lead["qualification"] = qualification
    except Exception:
        lead["qualification"] = "unprocessed"

    return {"handler": "lead", "lead": lead}


def handle_zapier_webhook(payload, client_config=None):
    """Handle Zapier webhook data."""
    return {
        "handler": "zapier",
        "data": payload,
        "action": "received_and_logged"
    }


def handle_form_submission(payload, client_config=None):
    """Handle form submission webhooks."""
    return {
        "handler": "form",
        "fields": payload,
        "action": "received"
    }


def handle_generic_webhook(payload, client_config=None):
    """Handle any unrecognized webhook."""
    return {
        "handler": "generic",
        "data": payload,
        "action": "logged"
    }


def get_webhook_log(limit=50, source_filter=None):
    """Get recent webhook entries."""
    entries = webhook_log
    if source_filter:
        entries = [e for e in entries if e["source"] == source_filter]
    return entries[-limit:]


# ── TOOL DEFINITIONS ──
TOOLS = [
    {
        "name": "list_webhooks",
        "description": "List recently received webhooks",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max entries to return", "default": 20},
                "source": {"type": "string", "description": "Filter by source (stripe, crm, zapier, etc.)"}
            }
        }
    },
    {
        "name": "process_webhook_data",
        "description": "Manually trigger processing of webhook data",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Source identifier"},
                "data": {"type": "object", "description": "The webhook payload to process"}
            },
            "required": ["source", "data"]
        }
    }
]


def execute_tool(tool_name, tool_input):
    if tool_name == "list_webhooks":
        entries = get_webhook_log(tool_input.get("limit", 20), tool_input.get("source"))
        return json.dumps(entries, default=str)
    elif tool_name == "process_webhook_data":
        result = process_webhook(tool_input["source"], tool_input["data"])
        return json.dumps(result, default=str)
    return json.dumps({"error": f"Unknown tool: {tool_name}"})
