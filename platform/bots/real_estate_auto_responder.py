"""
Real Estate Auto-Responder Bot
Monitors a leads JSON file and auto-responds to new leads via email.
Uses Pollinations AI for generating personalized response messages.
"""

import sys
import os
import json
import time
import logging
import smtplib
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

PLATFORM_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLATFORM_DIR))

try:
    from core.api_router import generate_text_free
except ImportError:
    generate_text_free = None

import requests

BOT_INFO = {
    "name": "Real Estate Auto-Responder",
    "category": "real_estate",
    "description": "Auto-responds to new property leads via email with AI-generated messages",
    "icon": "\U0001f4e7",
    "version": "1.0",
    "author": "Janovum",
    "config_schema": {
        "gmail_address": {"type": "str", "default": ""},
        "gmail_app_password": {"type": "str", "default": ""},
        "sender_name": {"type": "str", "default": "Janovum Real Estate"},
        "leads_file": {"type": "str", "default": ""},
        "check_interval_seconds": {"type": "int", "default": 300},
        "max_emails_per_run": {"type": "int", "default": 10},
        "dry_run": {"type": "bool", "default": True},
        "response_template": {"type": "str", "default": ""},
        "company_info": {"type": "str", "default": "We are a real estate technology company helping people find their perfect home."},
    }
}

_running = False
_status = {"state": "stopped", "emails_sent": 0, "last_check": None, "errors": []}
_logger = logging.getLogger("RealEstateAutoResponder")
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    _logger.addHandler(logging.StreamHandler())

DATA_DIR = PLATFORM_DIR / "data" / "bots" / "real_estate_auto_responder"
SENT_LOG = DATA_DIR / "sent_log.json"
DEFAULT_LEADS_FILE = PLATFORM_DIR / "data" / "bots" / "real_estate_lead_scraper" / "leads.json"


def _ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_sent_log():
    if SENT_LOG.exists():
        try:
            return json.loads(SENT_LOG.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_sent_log(log):
    _ensure_dirs()
    SENT_LOG.write_text(json.dumps(log, indent=2, default=str), encoding="utf-8")


def _load_leads(leads_file):
    lf = Path(leads_file) if leads_file else DEFAULT_LEADS_FILE
    if lf.exists():
        try:
            return json.loads(lf.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_leads(leads, leads_file):
    lf = Path(leads_file) if leads_file else DEFAULT_LEADS_FILE
    lf.write_text(json.dumps(leads, indent=2, default=str), encoding="utf-8")


def _generate_ai_response(lead, company_info):
    """Generate a personalized email response using Pollinations AI."""
    prompt = (
        f"Write a professional, friendly email response to a real estate lead. "
        f"Keep it under 150 words. Do not use markdown formatting. "
        f"Property: {lead.get('title', 'a property listing')}. "
        f"Price: {lead.get('price', 'not listed')}. "
        f"Location: {lead.get('city', 'unknown')}. "
        f"Company info: {company_info}. "
        f"The email should express interest, provide value, and invite the lead to connect. "
        f"Sign off with 'Best regards, The Janovum Real Estate Team'."
    )

    try:
        if generate_text_free:
            result = generate_text_free(prompt)
            return result.get("text", "").strip()
        else:
            import urllib.parse
            encoded = urllib.parse.quote(prompt)
            url = f"https://text.pollinations.ai/{encoded}"
            resp = requests.get(url, headers={"User-Agent": "Janovum/1.0"}, timeout=60)
            if resp.status_code == 200:
                return resp.text.strip()
    except Exception as e:
        _logger.error(f"AI text generation failed: {e}")

    # Fallback template
    return (
        f"Hello,\n\n"
        f"I came across your listing for \"{lead.get('title', 'a property')}\" "
        f"in {lead.get('city', 'your area')} and I'm very interested.\n\n"
        f"{company_info}\n\n"
        f"I'd love to learn more about this property. Could we schedule a time to discuss?\n\n"
        f"Best regards,\nThe Janovum Real Estate Team"
    )


def _send_email(to_email, subject, body, config):
    """Send an email via Gmail SMTP."""
    gmail_addr = config.get("gmail_address") or os.environ.get("GMAIL_ADDRESS", "")
    gmail_pass = config.get("gmail_app_password") or os.environ.get("GMAIL_APP_PASSWORD", "")
    sender_name = config.get("sender_name", "Janovum Real Estate")

    if not gmail_addr or not gmail_pass:
        raise Exception("Gmail credentials not configured. Set gmail_address and gmail_app_password in config.")

    msg = MIMEMultipart()
    msg["From"] = f"{sender_name} <{gmail_addr}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(gmail_addr, gmail_pass)
        server.send_message(msg)

    return True


def _process_leads(config):
    """Check for new uncontacted leads and respond."""
    global _status

    leads_file = config.get("leads_file", "")
    leads = _load_leads(leads_file)
    sent_log = _load_sent_log()
    sent_ids = {entry["lead_id"] for entry in sent_log}

    company_info = config.get("company_info", "We are a real estate technology company.")
    max_emails = config.get("max_emails_per_run", 10)
    dry_run = config.get("dry_run", True)
    emails_sent_this_run = 0

    for lead in leads:
        if emails_sent_this_run >= max_emails:
            break

        lead_id = lead.get("id", "")
        contact_email = lead.get("contact_email", "")

        # Skip if already contacted or no email
        if lead_id in sent_ids or not contact_email or lead.get("contacted", False):
            continue

        try:
            # Generate personalized response
            _logger.info(f"Generating response for lead: {lead.get('title', 'unknown')}")
            email_body = _generate_ai_response(lead, company_info)
            subject = f"Re: {lead.get('title', 'Your Property Listing')}"

            if dry_run:
                _logger.info(f"[DRY RUN] Would send to {contact_email}:\nSubject: {subject}\n{email_body[:200]}...")
                # Save draft instead
                draft_file = DATA_DIR / f"draft_{lead_id[:8]}.txt"
                draft_file.write_text(f"To: {contact_email}\nSubject: {subject}\n\n{email_body}", encoding="utf-8")
            else:
                _send_email(contact_email, subject, email_body, config)
                _logger.info(f"Email sent to {contact_email}")

            # Record in sent log
            sent_log.append({
                "lead_id": lead_id,
                "to_email": contact_email,
                "subject": subject,
                "body_preview": email_body[:200],
                "sent_at": datetime.now().isoformat(),
                "dry_run": dry_run,
            })

            # Mark lead as contacted
            lead["contacted"] = True
            lead["contacted_at"] = datetime.now().isoformat()

            emails_sent_this_run += 1
            _status["emails_sent"] += 1

            time.sleep(5)  # Rate limit between emails

        except Exception as e:
            _logger.error(f"Error processing lead {lead_id}: {e}")
            _status["errors"].append(str(e))

    # Save updates
    _save_sent_log(sent_log)
    _save_leads(leads, leads_file)
    return emails_sent_this_run


def run(config=None):
    """Start the auto-responder bot loop."""
    global _running, _status
    _running = True
    _ensure_dirs()

    if config is None:
        config = {v: s["default"] for v, s in BOT_INFO["config_schema"].items()}

    _status = {"state": "running", "emails_sent": 0, "last_check": None, "errors": []}
    _logger.info(f"Real Estate Auto-Responder started (dry_run={config.get('dry_run', True)})")

    interval = config.get("check_interval_seconds", 300)

    while _running:
        try:
            _status["state"] = "checking"
            count = _process_leads(config)
            _status["last_check"] = datetime.now().isoformat()
            _status["state"] = "waiting"
            _logger.info(f"Processed {count} leads. Next check in {interval}s...")
        except Exception as e:
            _logger.error(f"Responder cycle error: {e}")
            _status["errors"].append(str(e))
            _status["state"] = "error"

        for _ in range(interval):
            if not _running:
                break
            time.sleep(1)

    _status["state"] = "stopped"
    _logger.info("Real Estate Auto-Responder stopped.")


def stop():
    """Stop the bot."""
    global _running
    _running = False
    _status["state"] = "stopping"


def get_status():
    """Get current bot status."""
    sent_count = len(_load_sent_log()) if SENT_LOG.exists() else 0
    return {**_status, "total_emails_in_log": sent_count}


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        stop()
