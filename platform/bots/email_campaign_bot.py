"""
Email Campaign Bot
Sends AI-personalized email campaigns from a contact list.
Uses Pollinations for content generation and Gmail SMTP for sending.
Rate-limited to avoid spam flags. Tracks delivery status.
"""

import sys
import os
import json
import time
import logging
import smtplib
import uuid
import urllib.parse
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
    "name": "Email Campaign Bot",
    "category": "marketing",
    "description": "AI-powered email campaigns with personalized content",
    "icon": "\u2709\ufe0f",
    "version": "1.0",
    "author": "Janovum",
    "config_schema": {
        "gmail_address": {"type": "str", "default": ""},
        "gmail_app_password": {"type": "str", "default": ""},
        "sender_name": {"type": "str", "default": "Janovum"},
        "contacts_file": {"type": "str", "default": ""},
        "campaign_name": {"type": "str", "default": "Default Campaign"},
        "campaign_subject": {"type": "str", "default": ""},
        "campaign_prompt": {"type": "str", "default": "Write a professional outreach email introducing our services."},
        "company_info": {"type": "str", "default": "We provide AI-powered automation solutions for businesses."},
        "interval_seconds": {"type": "int", "default": 1800},
        "emails_per_batch": {"type": "int", "default": 5},
        "delay_between_emails_seconds": {"type": "int", "default": 30},
        "dry_run": {"type": "bool", "default": True},
        "track_opens": {"type": "bool", "default": True},
    }
}

_running = False
_status = {"state": "stopped", "emails_sent": 0, "emails_failed": 0, "last_batch": None, "errors": []}
_logger = logging.getLogger("EmailCampaignBot")
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    _logger.addHandler(logging.StreamHandler())

DATA_DIR = PLATFORM_DIR / "data" / "bots" / "email_campaign_bot"
CAMPAIGN_LOG = DATA_DIR / "campaign_log.json"
DEFAULT_CONTACTS = DATA_DIR / "contacts.json"


def _ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_contacts(contacts_file):
    cf = Path(contacts_file) if contacts_file else DEFAULT_CONTACTS
    if cf.exists():
        try:
            return json.loads(cf.read_text(encoding="utf-8"))
        except Exception:
            return []

    # Also try loading from lead_hunter leads
    hunter_leads = PLATFORM_DIR / "data" / "bots" / "lead_hunter" / "leads.json"
    if hunter_leads.exists():
        try:
            leads = json.loads(hunter_leads.read_text(encoding="utf-8"))
            contacts = []
            for lead in leads:
                for email in lead.get("emails", []):
                    contacts.append({
                        "email": email,
                        "name": lead.get("name", ""),
                        "company": "",
                        "industry": lead.get("industry", ""),
                        "source": "lead_hunter",
                    })
            return contacts
        except Exception:
            pass

    return []


def _load_campaign_log():
    if CAMPAIGN_LOG.exists():
        try:
            return json.loads(CAMPAIGN_LOG.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_campaign_log(log):
    _ensure_dirs()
    CAMPAIGN_LOG.write_text(json.dumps(log, indent=2, default=str), encoding="utf-8")


def _generate_personalized_email(contact, config):
    """Generate a personalized email using Pollinations AI."""
    name = contact.get("name", "")
    company = contact.get("company", "")
    industry = contact.get("industry", "")

    prompt = (
        f"{config.get('campaign_prompt', 'Write a professional outreach email.')} "
        f"Personalize for: {f'name: {name}, ' if name else ''}"
        f"{f'company: {company}, ' if company else ''}"
        f"{f'industry: {industry}, ' if industry else ''}"
        f"Company info: {config.get('company_info', '')}. "
        f"Keep under 200 words. Professional tone. No markdown formatting. "
        f"Include a clear call-to-action. Sign off with the sender name."
    )

    try:
        if generate_text_free:
            result = generate_text_free(prompt)
            return result.get("text", "").strip()
        else:
            encoded = urllib.parse.quote(prompt)
            url = f"https://text.pollinations.ai/{encoded}"
            resp = requests.get(url, headers={"User-Agent": "Janovum/1.0"}, timeout=60)
            if resp.status_code == 200:
                return resp.text.strip()
    except Exception as e:
        _logger.error(f"AI email generation failed: {e}")

    # Fallback
    greeting = f"Dear {name},\n\n" if name else "Hello,\n\n"
    return (
        f"{greeting}"
        f"I hope this message finds you well. "
        f"{config.get('company_info', 'We provide innovative solutions.')}\n\n"
        f"I believe we could add significant value to {'your work at ' + company if company else 'your business'}. "
        f"Would you be open to a brief conversation?\n\n"
        f"Best regards,\n{config.get('sender_name', 'Janovum')}"
    )


def _generate_subject(contact, config):
    """Generate or use a campaign subject line."""
    subject = config.get("campaign_subject", "")
    if subject:
        # Personalize static subject
        name = contact.get("name", "")
        company = contact.get("company", "")
        subject = subject.replace("{name}", name).replace("{company}", company)
        return subject

    # Generate with AI
    prompt = (
        f"Write a single short email subject line (under 60 characters) for a business outreach email. "
        f"Make it engaging but professional. No quotes or punctuation at the end. "
        f"Topic: {config.get('campaign_prompt', 'business outreach')}"
    )

    try:
        if generate_text_free:
            result = generate_text_free(prompt)
            text = result.get("text", "").strip().strip('"').strip("'")
            return text[:60] if text else "A Quick Introduction"
        else:
            encoded = urllib.parse.quote(prompt)
            url = f"https://text.pollinations.ai/{encoded}"
            resp = requests.get(url, headers={"User-Agent": "Janovum/1.0"}, timeout=30)
            if resp.status_code == 200:
                text = resp.text.strip().strip('"').strip("'")
                return text[:60] if text else "A Quick Introduction"
    except Exception:
        pass

    return "A Quick Introduction from Janovum"


def _send_email(to_email, subject, body, config, tracking_id=""):
    """Send a single email via Gmail SMTP."""
    gmail_addr = config.get("gmail_address") or os.environ.get("GMAIL_ADDRESS", "")
    gmail_pass = config.get("gmail_app_password") or os.environ.get("GMAIL_APP_PASSWORD", "")
    sender_name = config.get("sender_name", "Janovum")

    if not gmail_addr or not gmail_pass:
        raise Exception("Gmail credentials not configured.")

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{sender_name} <{gmail_addr}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg["X-Campaign-ID"] = tracking_id

    # Plain text version
    msg.attach(MIMEText(body, "plain"))

    # HTML version with optional tracking pixel
    html_body = body.replace("\n", "<br>")
    if config.get("track_opens", True) and tracking_id:
        # Simple tracking pixel (requires a webhook endpoint to actually work)
        html_body += f'<img src="https://httpbin.org/get?track={tracking_id}" width="1" height="1" />'
    msg.attach(MIMEText(f"<html><body>{html_body}</body></html>", "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(gmail_addr, gmail_pass)
        server.send_message(msg)

    return True


def _run_batch(config):
    """Send one batch of campaign emails."""
    global _status

    contacts = _load_contacts(config.get("contacts_file", ""))
    if not contacts:
        _logger.info("No contacts found. Add contacts to contacts.json or link a leads file.")
        return 0

    campaign_log = _load_campaign_log()
    sent_emails = {entry["email"] for entry in campaign_log if entry.get("campaign") == config.get("campaign_name", "")}

    batch_size = config.get("emails_per_batch", 5)
    delay = config.get("delay_between_emails_seconds", 30)
    dry_run = config.get("dry_run", True)
    sent_count = 0

    for contact in contacts:
        if sent_count >= batch_size:
            break
        if not _running:
            break

        email = contact.get("email", "")
        if not email or email in sent_emails:
            continue

        try:
            tracking_id = str(uuid.uuid4())[:8]

            # Generate personalized content
            _logger.info(f"Generating email for {email}...")
            subject = _generate_subject(contact, config)
            body = _generate_personalized_email(contact, config)

            if dry_run:
                _logger.info(f"[DRY RUN] Would send to {email}:\n  Subject: {subject}\n  Body: {body[:100]}...")
                draft_dir = DATA_DIR / "drafts"
                draft_dir.mkdir(exist_ok=True)
                draft_file = draft_dir / f"draft_{tracking_id}.txt"
                draft_file.write_text(f"To: {email}\nSubject: {subject}\n\n{body}", encoding="utf-8")
                status = "drafted"
            else:
                _send_email(email, subject, body, config, tracking_id)
                status = "sent"
                _logger.info(f"Sent to {email}")

            campaign_log.append({
                "email": email,
                "name": contact.get("name", ""),
                "subject": subject,
                "body_preview": body[:150],
                "tracking_id": tracking_id,
                "campaign": config.get("campaign_name", ""),
                "status": status,
                "sent_at": datetime.now().isoformat(),
            })

            sent_count += 1
            _status["emails_sent"] += 1

            if sent_count < batch_size:
                _logger.info(f"Waiting {delay}s before next email...")
                for _ in range(delay):
                    if not _running:
                        break
                    time.sleep(1)

        except Exception as e:
            _logger.error(f"Failed to send to {email}: {e}")
            _status["emails_failed"] += 1
            _status["errors"].append(f"{email}: {str(e)}")

            campaign_log.append({
                "email": email,
                "campaign": config.get("campaign_name", ""),
                "status": "failed",
                "error": str(e),
                "sent_at": datetime.now().isoformat(),
            })

    _save_campaign_log(campaign_log)
    return sent_count


def run(config=None):
    """Start the email campaign bot loop."""
    global _running, _status
    _running = True
    _ensure_dirs()

    if config is None:
        config = {v: s["default"] for v, s in BOT_INFO["config_schema"].items()}

    _status = {"state": "running", "emails_sent": 0, "emails_failed": 0, "last_batch": None, "errors": []}
    _logger.info(f"Email Campaign Bot started: {config.get('campaign_name', 'Default')} (dry_run={config.get('dry_run', True)})")

    interval = config.get("interval_seconds", 1800)

    while _running:
        try:
            _status["state"] = "sending"
            count = _run_batch(config)
            _status["last_batch"] = datetime.now().isoformat()
            _status["state"] = "waiting"
            _logger.info(f"Batch complete: {count} emails. Next batch in {interval}s...")
        except Exception as e:
            _logger.error(f"Campaign cycle error: {e}")
            _status["errors"].append(str(e))
            _status["state"] = "error"

        for _ in range(interval):
            if not _running:
                break
            time.sleep(1)

    _status["state"] = "stopped"
    _logger.info("Email Campaign Bot stopped.")


def stop():
    global _running
    _running = False
    _status["state"] = "stopping"


def get_status():
    log = _load_campaign_log() if CAMPAIGN_LOG.exists() else []
    return {**_status, "total_in_log": len(log)}


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        stop()
