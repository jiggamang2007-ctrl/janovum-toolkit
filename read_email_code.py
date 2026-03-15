"""Read verification code from Gmail inbox."""
import imaplib
import email
from email.header import decode_header
import re

EMAIL = "myfriendlyagent12@gmail.com"
APP_PASSWORD = "pdcvjroclstugncx"

def get_latest_code():
    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    mail.login(EMAIL, APP_PASSWORD)
    mail.select("inbox")

    # Search for recent emails from Cartesia/Clerk
    status, messages = mail.search(None, '(UNSEEN)')
    if status != "OK" or not messages[0]:
        # Try all recent
        status, messages = mail.search(None, '(SINCE "14-Mar-2026")')

    email_ids = messages[0].split()
    print(f"Found {len(email_ids)} emails")

    for eid in reversed(email_ids[-10:]):  # Check last 10
        status, msg_data = mail.fetch(eid, "(RFC822)")
        if status != "OK":
            continue

        msg = email.message_from_bytes(msg_data[0][1])
        subject = str(decode_header(msg["Subject"])[0][0])
        if isinstance(subject, bytes):
            subject = subject.decode()
        sender = msg["From"]
        print(f"  From: {sender}")
        print(f"  Subject: {subject}")

        # Get body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                ct = part.get_content_type()
                if ct == "text/plain":
                    body = part.get_payload(decode=True).decode(errors="ignore")
                    break
                elif ct == "text/html":
                    body = part.get_payload(decode=True).decode(errors="ignore")
        else:
            body = msg.get_payload(decode=True).decode(errors="ignore")

        # Look for verification code (usually 6 digits)
        codes = re.findall(r'\b(\d{6})\b', body)
        if codes:
            print(f"  CODE FOUND: {codes[0]}")
            mail.logout()
            return codes[0]

        # Also check subject
        codes = re.findall(r'\b(\d{6})\b', subject)
        if codes:
            print(f"  CODE IN SUBJECT: {codes[0]}")
            mail.logout()
            return codes[0]

    mail.logout()
    return None

code = get_latest_code()
if code:
    print(f"\nVerification code: {code}")
else:
    print("\nNo verification code found")
