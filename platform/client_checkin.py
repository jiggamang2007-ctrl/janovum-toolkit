#!/usr/bin/env python3
"""
Janovum Client Check-In Email System
Sends automated, rotating check-in emails to clients from the agent account.
"""

import argparse
import json
import os
import smtplib
import sys
import random
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENTS_INDEX = os.path.join(BASE_DIR, "data", "clients", "clients_index.json")
CLIENTS_DIR = os.path.join(BASE_DIR, "data", "clients")
CHECKIN_LOG = os.path.join(BASE_DIR, "data", "checkin_log.json")

# ─── SMTP Config ──────────────────────────────────────────────────────────────
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = "myfriendlyagent12@gmail.com"
SMTP_APP_PASSWORD = "pdcvjroclstugncx"

# ─── Colors ───────────────────────────────────────────────────────────────────
class C:
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    DIM = "\033[2m"

# ─── Email Templates ─────────────────────────────────────────────────────────

TEMPLATES = {
    1: {
        "subject": "How's everything going? — Janovum",
        "body": """Hey {business_name} team,

Just wanted to check in and see how everything's going with your AI receptionist. Is it working well for you? Any questions or adjustments needed?

We're always looking to make things better, so if there's anything on your mind, just reply to this email or give us a call.

Talk soon,
Jaden
Janovum
+1 (833) 958-9975
janovum.com"""
    },
    2: {
        "subject": "Did you know your AI can do this? — Janovum",
        "body": """Hey {business_name} team,

Quick heads up — your AI receptionist can do more than just answer calls. Here are a few things you might not be using yet:

• Custom knowledge updates — We can teach it new info about your business anytime
• SMS follow-ups — Automatic texts after appointments
• After-hours handling — Different greetings for nights and weekends

Want us to set any of these up for you? Just reply and we'll take care of it.

Best,
Jaden
Janovum
+1 (833) 958-9975"""
    },
    3: {
        "subject": "Quick question for you — Janovum",
        "body": """Hey {business_name} team,

I wanted to ask — how has the AI receptionist been working out for your business?

Are there any calls it's not handling the way you'd like? Anything you wish it could do differently?

Your feedback helps us make it better for you. Just hit reply with any thoughts.

Thanks,
Jaden
Janovum
+1 (833) 958-9975"""
    },
    4: {
        "subject": "Your AI receptionist this month — Janovum",
        "body": """Hey {business_name} team,

Just a quick update — your AI receptionist has been answering calls 24/7 so you don't have to.

Remember, every call it picks up is a customer that might have gone to your competitor. We're making sure that doesn't happen.

If you need any changes or want to add new features, we're here. Just reply or call.

Best,
Jaden
Janovum
+1 (833) 958-9975
janovum.com"""
    }
}


def load_json(path):
    """Load a JSON file, return empty list/dict on failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_json(path, data):
    """Save data to a JSON file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def load_clients_index():
    """Load the clients index."""
    clients = load_json(CLIENTS_INDEX)
    if not clients:
        print(f"{C.RED}  ERROR: No clients found in {CLIENTS_INDEX}{C.RESET}")
        sys.exit(1)
    return clients


def load_client_config(client_id):
    """Load a client's full config JSON."""
    path = os.path.join(CLIENTS_DIR, f"{client_id}.json")
    if not os.path.exists(path):
        return None
    return load_json(path)


def load_checkin_log():
    """Load the check-in log."""
    data = load_json(CHECKIN_LOG)
    return data if isinstance(data, list) else []


def save_checkin_log(log):
    """Save the check-in log."""
    save_json(CHECKIN_LOG, log)


def was_emailed_this_week(client_id, log):
    """Check if a client was emailed in the last 7 days."""
    one_week_ago = datetime.now() - timedelta(days=7)
    for entry in reversed(log):
        if entry.get("client_id") == client_id:
            try:
                sent_at = datetime.fromisoformat(entry["sent_at"])
                if sent_at > one_week_ago:
                    return True, sent_at
            except (KeyError, ValueError):
                continue
    return False, None


def pick_template(client_id, log, force_template=None):
    """Pick a template, rotating so it doesn't repeat the last one used."""
    if force_template and force_template in TEMPLATES:
        return force_template

    # Find last template used for this client
    last_template = None
    for entry in reversed(log):
        if entry.get("client_id") == client_id:
            last_template = entry.get("template_id")
            break

    available = [t for t in TEMPLATES if t != last_template]
    if not available:
        available = list(TEMPLATES.keys())
    return random.choice(available)


def build_email(business_name, to_email, template_id):
    """Build the email message."""
    template = TEMPLATES[template_id]
    subject = template["subject"]
    body = template["body"].format(business_name=business_name)

    msg = MIMEMultipart("alternative")
    msg["From"] = f"Janovum <{SMTP_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg["Reply-To"] = SMTP_EMAIL
    msg.attach(MIMEText(body, "plain", "utf-8"))
    return msg, subject, body


def send_email(msg):
    """Send an email via SMTP."""
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
        server.send_message(msg)


def process_client(client_entry, log, args):
    """Process a single client for check-in."""
    client_id = client_entry["client_id"]
    business_name = client_entry.get("business_name", client_id)

    print(f"\n{C.CYAN}{'-' * 60}{C.RESET}")
    print(f"{C.BOLD}  Client: {C.MAGENTA}{business_name}{C.RESET} ({client_id})")

    # Check weekly limit
    emailed, last_date = was_emailed_this_week(client_id, log)
    if emailed and not args.force:
        print(f"{C.YELLOW}  SKIPPED — Already emailed on {last_date.strftime('%b %d, %Y')}{C.RESET}")
        return False

    # Load client config to get email
    config = load_client_config(client_id)
    if not config:
        print(f"{C.YELLOW}  WARNING — No config file found for '{client_id}'{C.RESET}")
        return False

    to_email = config.get("notification_email", "").strip()
    if not to_email:
        print(f"{C.YELLOW}  WARNING — No notification_email set, skipping{C.RESET}")
        return False

    # Pick template
    template_id = pick_template(client_id, log, args.template)
    msg, subject, body = build_email(business_name, to_email, template_id)

    print(f"{C.BLUE}  To:       {to_email}{C.RESET}")
    print(f"{C.BLUE}  Subject:  {subject}{C.RESET}")
    print(f"{C.BLUE}  Template: #{template_id}{C.RESET}")

    if not args.send:
        print(f"\n{C.DIM}  --- PREVIEW (body) ---{C.RESET}")
        for line in body.split("\n"):
            print(f"{C.DIM}  | {line}{C.RESET}")
        print(f"{C.YELLOW}  (dry run — use --send to actually send){C.RESET}")
        return False

    # Send
    try:
        send_email(msg)
        print(f"{C.GREEN}  SENT successfully!{C.RESET}")

        # Log it
        log.append({
            "client_id": client_id,
            "business_name": business_name,
            "email": to_email,
            "template_id": template_id,
            "subject": subject,
            "sent_at": datetime.now().isoformat(),
            "status": "sent"
        })
        save_checkin_log(log)
        return True

    except smtplib.SMTPException as e:
        print(f"{C.RED}  SMTP ERROR — {e}{C.RESET}")
        log.append({
            "client_id": client_id,
            "business_name": business_name,
            "email": to_email,
            "template_id": template_id,
            "subject": subject,
            "sent_at": datetime.now().isoformat(),
            "status": f"failed: {e}"
        })
        save_checkin_log(log)
        return False


def safe_print(text):
    """Print with fallback for Windows encoding issues."""
    try:
        print(text)
    except UnicodeEncodeError:
        import re
        cleaned = re.sub(r'[^\x00-\x7f]', '', text)
        print(cleaned)


def main():
    parser = argparse.ArgumentParser(
        description="Janovum Client Check-In Email System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python client_checkin.py --all                    Preview all clients
  python client_checkin.py --send --all             Send to all clients
  python client_checkin.py --send --client janovum  Send to specific client
  python client_checkin.py --all --template 2       Preview with template #2
  python client_checkin.py --send --all --force     Send even if emailed this week
        """
    )
    parser.add_argument("--send", action="store_true",
                        help="Actually send emails (without this, preview only)")
    parser.add_argument("--all", action="store_true",
                        help="Email all clients")
    parser.add_argument("--client", type=str, metavar="CLIENT_ID",
                        help="Email a specific client by ID")
    parser.add_argument("--template", type=int, choices=[1, 2, 3, 4],
                        help="Force a specific template (1-4)")
    parser.add_argument("--force", action="store_true",
                        help="Override the once-per-week limit")

    args = parser.parse_args()

    if not args.all and not args.client:
        parser.print_help()
        print(f"\n{C.RED}  Error: Specify --all or --client <client_id>{C.RESET}")
        sys.exit(1)

    # Header
    safe_print(f"\n{C.BOLD}{C.CYAN}+{'=' * 58}+{C.RESET}")
    safe_print(f"{C.BOLD}{C.CYAN}|         JANOVUM -- Client Check-In Email System          |{C.RESET}")
    safe_print(f"{C.BOLD}{C.CYAN}+{'=' * 58}+{C.RESET}")

    mode = "LIVE SEND" if args.send else "PREVIEW ONLY"
    mode_color = C.GREEN if args.send else C.YELLOW
    print(f"\n{C.BOLD}  Mode: {mode_color}{mode}{C.RESET}")
    print(f"{C.DIM}  Time: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}{C.RESET}")

    # Load data
    clients_index = load_clients_index()
    log = load_checkin_log()

    # Filter clients
    if args.client:
        targets = [c for c in clients_index if c["client_id"] == args.client]
        if not targets:
            print(f"\n{C.RED}  Error: Client '{args.client}' not found in index{C.RESET}")
            sys.exit(1)
    else:
        targets = clients_index

    print(f"{C.DIM}  Clients to process: {len(targets)}{C.RESET}")

    # Process
    sent_count = 0
    for client in targets:
        if process_client(client, log, args):
            sent_count += 1

    # Summary
    print(f"\n{C.CYAN}{'-' * 60}{C.RESET}")
    if args.send:
        print(f"{C.BOLD}{C.GREEN}  Done! Sent {sent_count}/{len(targets)} check-in emails.{C.RESET}")
    else:
        print(f"{C.BOLD}{C.YELLOW}  Preview complete. Use --send to send emails.{C.RESET}")
    print()


if __name__ == "__main__":
    main()
