"""
Janovum Module — AI Lead Responder
Monitors website forms / incoming leads. Responds instantly,
qualifies the lead, and books appointments.

This is the #1 service AI agencies sell — $500-2000/month per client.
Speed matters: first to respond usually wins the client.

How it works:
  1. Python watches for new form submissions (webhook or email)
  2. New lead comes in
  3. Claude qualifies the lead and drafts a personalized response
  4. Python sends the response (email, SMS, or Telegram)
  5. If qualified, Claude suggests booking a meeting
  6. Back to watching (free)

Requirements:
  Client config needs: notification method (email/telegram), business details
"""

import time
import json
import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engine import quick_ask, call_claude

MODULE_NAME = "lead_responder"
MODULE_DESC = "AI Lead Responder — instant lead qualification and response"


LEAD_SYSTEM_PROMPT = """You are a professional AI sales assistant created by Janovum.
Your job is to respond to new leads quickly and professionally.

When a new lead comes in, you:
1. Greet them warmly and personally
2. Acknowledge what they're asking about
3. Briefly highlight the value of the service
4. Ask a qualifying question (budget, timeline, specific needs)
5. Suggest booking a call or meeting

Keep it short (3-5 sentences), friendly, and professional.
Don't be pushy — be helpful."""


def qualify_lead(lead_data, client_config):
    """
    Use Claude to analyze and respond to a lead.

    lead_data should have:
      - name: lead's name
      - email: lead's email
      - message: what they asked about
      - source: where they came from (website, referral, etc.)

    Returns dict with:
      - response: the drafted reply
      - qualification: hot/warm/cold
      - suggested_action: what to do next
    """
    client_name = client_config.get("client_name", "")
    client_services = client_config.get("services", "")
    client_context = client_config.get("client_context", "")

    prompt = f"""New lead just came in for {client_name}.

Lead Info:
- Name: {lead_data.get('name', 'Unknown')}
- Email: {lead_data.get('email', 'N/A')}
- Source: {lead_data.get('source', 'Website')}
- Message: {lead_data.get('message', 'No message')}

Business: {client_name}
Services: {client_services}
Context: {client_context}

Please provide:
1. RESPONSE: A personalized reply to send to this lead (3-5 sentences)
2. QUALIFICATION: Rate as HOT (ready to buy), WARM (interested, needs nurturing), or COLD (probably not a fit)
3. NEXT_ACTION: What should the business owner do next?

Format your response exactly like:
RESPONSE: [your reply here]
QUALIFICATION: [HOT/WARM/COLD]
NEXT_ACTION: [suggested action]"""

    result = quick_ask(prompt, system_prompt=LEAD_SYSTEM_PROMPT)

    if "[ERROR]" in result:
        return {"error": result}

    # Parse the structured response
    parsed = {"response": "", "qualification": "WARM", "suggested_action": "Follow up"}

    for line in result.split("\n"):
        line = line.strip()
        if line.startswith("RESPONSE:"):
            parsed["response"] = line[9:].strip()
        elif line.startswith("QUALIFICATION:"):
            parsed["qualification"] = line[14:].strip()
        elif line.startswith("NEXT_ACTION:"):
            parsed["suggested_action"] = line[12:].strip()

    # If parsing didn't work cleanly, use full text
    if not parsed["response"]:
        parsed["response"] = result

    return parsed


def send_lead_response(lead_data, response_text, client_config):
    """Send the response to the lead via email."""
    smtp_config = {
        "email": client_config.get("email", ""),
        "email_password": client_config.get("email_password", ""),
        "smtp_server": client_config.get("smtp_server", "smtp.gmail.com"),
        "smtp_port": client_config.get("smtp_port", 587)
    }

    if not smtp_config["email"] or not smtp_config["email_password"]:
        print("[lead_responder] No email credentials — can't send response.")
        return False

    lead_email = lead_data.get("email", "")
    if not lead_email:
        print("[lead_responder] No lead email — can't send response.")
        return False

    msg = MIMEMultipart()
    msg["From"] = smtp_config["email"]
    msg["To"] = lead_email
    msg["Subject"] = f"Thanks for reaching out to {client_config.get('client_name', 'us')}!"
    msg.attach(MIMEText(response_text, "plain"))

    try:
        with smtplib.SMTP(smtp_config["smtp_server"], smtp_config["smtp_port"]) as server:
            server.starttls()
            server.login(smtp_config["email"], smtp_config["email_password"])
            server.send_message(msg)
        print(f"[lead_responder] Response sent to {lead_email}")
        return True
    except Exception as e:
        print(f"[lead_responder] Failed to send: {e}")
        return False


def process_lead(lead_data, client_config):
    """Full pipeline: qualify lead, draft response, send it."""
    print(f"\n[lead_responder] New lead: {lead_data.get('name', 'Unknown')} ({lead_data.get('email', 'N/A')})")

    result = qualify_lead(lead_data, client_config)

    if "error" in result:
        print(f"[lead_responder] Error: {result['error']}")
        return result

    print(f"[lead_responder] Qualification: {result['qualification']}")
    print(f"[lead_responder] Response: {result['response'][:150]}...")
    print(f"[lead_responder] Next action: {result['suggested_action']}")

    auto_send = client_config.get("auto_send_leads", False)
    if auto_send:
        send_lead_response(lead_data, result["response"], client_config)
    else:
        print("[lead_responder] Auto-send OFF — response drafted but not sent.")

    return result


# ── API endpoint handler (called by server.py) ──
def handle_webhook(data, client_config):
    """Handle incoming webhook from a website form."""
    lead = {
        "name": data.get("name", ""),
        "email": data.get("email", ""),
        "message": data.get("message", ""),
        "source": data.get("source", "website")
    }
    return process_lead(lead, client_config)


if __name__ == "__main__":
    # Test with a fake lead
    test_lead = {
        "name": "John Smith",
        "email": "john@example.com",
        "message": "I'm interested in getting AI automation for my restaurant. Can you help?",
        "source": "Website Contact Form"
    }
    test_config = {
        "client_name": "Pizza Palace",
        "services": "AI automation for restaurants — ordering, reservations, customer service",
        "client_context": "Local pizza restaurant, 2 locations, 15 employees",
        "auto_send_leads": False
    }
    result = process_lead(test_lead, test_config)
    print(f"\nFull result: {json.dumps(result, indent=2)}")
