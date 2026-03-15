"""
Janovum Module — Email Auto-Responder
Monitors a client's inbox via IMAP. When new email arrives,
sends it to Claude for a draft reply, then sends via SMTP.

How it works:
  1. Python checks inbox every 60 seconds (free — just IMAP polling)
  2. New email detected
  3. Sends email content to Claude API (pennies)
  4. Claude drafts a professional reply
  5. Python sends the reply via SMTP
  6. Back to checking (free)

Requirements:
  Client config needs: email, email_password, imap_server, smtp_server
"""

import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engine import quick_ask

MODULE_NAME = "email_responder"
MODULE_DESC = "Email Auto-Responder — monitors inbox, drafts replies with Claude"


def check_inbox(imap_conn):
    """Check for unread emails. Returns list of (sender, subject, body)."""
    imap_conn.select("INBOX")
    status, messages = imap_conn.search(None, "UNSEEN")
    if status != "OK":
        return []

    emails = []
    for num in messages[0].split():
        status, data = imap_conn.fetch(num, "(RFC822)")
        if status != "OK":
            continue

        msg = email.message_from_bytes(data[0][1])
        sender = msg.get("From", "Unknown")
        subject = msg.get("Subject", "No Subject")

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                    break
        else:
            body = msg.get_payload(decode=True).decode("utf-8", errors="replace")

        emails.append({"sender": sender, "subject": subject, "body": body[:2000]})

    return emails


def draft_reply(email_data, client_name, client_context):
    """Use Claude to draft a reply to an email."""
    prompt = f"""You are replying to an email on behalf of {client_name}.
Business context: {client_context}

The email is from: {email_data['sender']}
Subject: {email_data['subject']}
Body:
{email_data['body']}

Draft a professional, helpful reply. Be concise and friendly.
Sign off as {client_name}.
Return ONLY the email body text, no subject line."""

    system = f"You are a professional email assistant for {client_name}, powered by Janovum."
    return quick_ask(prompt, system_prompt=system)


def send_reply(smtp_config, to_addr, subject, body):
    """Send an email reply via SMTP."""
    msg = MIMEMultipart()
    msg["From"] = smtp_config["email"]
    msg["To"] = to_addr
    msg["Subject"] = f"Re: {subject}"
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(smtp_config["smtp_server"], smtp_config.get("smtp_port", 587)) as server:
        server.starttls()
        server.login(smtp_config["email"], smtp_config["email_password"])
        server.send_message(msg)


def extract_email_address(sender_str):
    """Extract email address from 'Name <email@example.com>' format."""
    if "<" in sender_str and ">" in sender_str:
        return sender_str.split("<")[1].split(">")[0]
    return sender_str


def run_loop(client_config, check_interval=60):
    """
    Main loop — checks inbox, drafts replies, sends them.

    client_config needs:
      - email: the email address
      - email_password: app password
      - imap_server: e.g., imap.gmail.com
      - smtp_server: e.g., smtp.gmail.com
      - smtp_port: e.g., 587
      - client_name: business name
      - client_context: what the business does
      - auto_send: True to send automatically, False to just log drafts
    """
    email_addr = client_config.get("email", "")
    email_pass = client_config.get("email_password", "")
    imap_server = client_config.get("imap_server", "imap.gmail.com")
    client_name = client_config.get("client_name", "")
    client_context = client_config.get("client_context", "")
    auto_send = client_config.get("auto_send", False)

    if not email_addr or not email_pass:
        print("[email_responder] Missing email or email_password in config.")
        return

    print(f"[email_responder] Monitoring {email_addr} for {client_name}...")
    print(f"[email_responder] Auto-send: {'ON' if auto_send else 'OFF (draft only)'}")
    print(f"[email_responder] Checking every {check_interval}s...")

    while True:
        try:
            imap = imaplib.IMAP4_SSL(imap_server)
            imap.login(email_addr, email_pass)

            new_emails = check_inbox(imap)

            for em in new_emails:
                print(f"\n[email_responder] New email from {em['sender']}: {em['subject']}")

                reply = draft_reply(em, client_name, client_context)

                if "[ERROR]" in reply:
                    print(f"[email_responder] Claude error: {reply}")
                    continue

                print(f"[email_responder] Draft reply:\n{reply[:200]}...")

                if auto_send:
                    to_addr = extract_email_address(em["sender"])
                    send_reply(
                        {"email": email_addr, "email_password": email_pass,
                         "smtp_server": client_config.get("smtp_server", "smtp.gmail.com"),
                         "smtp_port": client_config.get("smtp_port", 587)},
                        to_addr, em["subject"], reply
                    )
                    print(f"[email_responder] Reply sent to {to_addr}")
                else:
                    print("[email_responder] Auto-send OFF — reply drafted but not sent.")

            imap.logout()

        except Exception as e:
            print(f"[email_responder] Error: {e}")

        time.sleep(check_interval)


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "../clients/example.json"
    if os.path.exists(config_path):
        with open(config_path) as f:
            cfg = json.load(f)
        run_loop(cfg)
    else:
        print(f"Config not found: {config_path}")
