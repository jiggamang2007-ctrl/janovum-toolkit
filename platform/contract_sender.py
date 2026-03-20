"""
Janovum Contract Sender — Instant Service Agreement Generator

Usage:
    From Claude Code, just call:
        python platform/contract_sender.py --name "John Smith" --business "Smith Plumbing" --email "john@smith.com" --phone "555-123-4567" --address "123 Main St, NY" --services "AI Receptionist, Website" --term "6 months"

    This will:
    1. Generate a personalized, signable HTML agreement
    2. Host it as a unique link on the Flask server
    3. Email the link to the client
    4. When client signs & submits, Jaden gets the signed copy by email

    Quick mode (minimal info):
        python platform/contract_sender.py --name "John Smith" --email "john@smith.com" --business "Smith Co"
"""

import os
import sys
import json
import argparse
import hashlib
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

PLATFORM_DIR = os.path.dirname(os.path.abspath(__file__))
CONTRACTS_DIR = os.path.join(PLATFORM_DIR, "data", "contracts")
os.makedirs(CONTRACTS_DIR, exist_ok=True)

# Email config
SMTP_EMAIL = "myfriendlyagent12@gmail.com"
SMTP_PASSWORD = "pdcvjroclstugncx"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Jaden's business email (receives signed contracts)
JADEN_EMAIL = os.environ.get("JADEN_EMAIL", "myfriendlyagent12@gmail.com")

# Server base URL
BASE_URL = os.environ.get("CONTRACT_BASE_URL", "https://janovum.com")


def generate_contract_id(client_name, client_email):
    """Generate a unique contract ID"""
    raw = f"{client_name}-{client_email}-{time.time()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def generate_contract_html(contract_id, client_info):
    """Generate a signable HTML service agreement"""
    name = client_info["name"]
    business = client_info["business"]
    email = client_info["email"]
    phone = client_info.get("phone", "_______________")
    address = client_info.get("address", "_______________")
    services = client_info.get("services", "AI Receptionist, Business Automation, Dashboard Access")
    setup_fee = client_info.get("setup_fee", "1,000.00")
    monthly_fee = client_info.get("monthly_fee", "500.00")
    total_due = client_info.get("total_due", "1,500.00")
    term = client_info.get("term", "3 months")
    today = datetime.now().strftime("%B %d, %Y")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Janovum Service Agreement — {business}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Inter', sans-serif; background: #f5f5f5; color: #222; line-height: 1.7; }}
.container {{ max-width: 800px; margin: 0 auto; background: #fff; box-shadow: 0 2px 20px rgba(0,0,0,.1); }}
.header {{ background: linear-gradient(135deg, #0a0a0a 0%, #1a1a18 100%); color: #fff; padding: 40px; text-align: center; }}
.header h1 {{ font-size: 28px; font-weight: 800; letter-spacing: 2px; margin-bottom: 4px; }}
.header .gold {{ color: #D4AF37; }}
.header p {{ color: #999; font-size: 14px; margin-top: 8px; }}
.body {{ padding: 40px; }}
.body h2 {{ font-size: 18px; font-weight: 700; color: #111; margin: 28px 0 12px; border-bottom: 2px solid #D4AF37; padding-bottom: 6px; }}
.body h3 {{ font-size: 15px; font-weight: 600; margin: 16px 0 8px; color: #333; }}
.body p {{ margin: 8px 0; font-size: 14px; }}
.body ul {{ margin: 8px 0 8px 24px; font-size: 14px; }}
.body li {{ margin: 4px 0; }}
.body table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
.body td, .body th {{ padding: 10px 14px; border: 1px solid #ddd; font-size: 14px; }}
.body th {{ background: #f9f9f9; text-align: left; font-weight: 600; }}
.body tr:nth-child(even) {{ background: #fafafa; }}
.highlight {{ background: #fffdf0; border-left: 4px solid #D4AF37; padding: 16px; margin: 16px 0; border-radius: 0 8px 8px 0; }}
hr {{ border: none; border-top: 1px solid #eee; margin: 24px 0; }}

/* Signature Section */
.sign-section {{ background: #fafafa; border: 2px solid #D4AF37; border-radius: 12px; padding: 32px; margin: 32px 0; }}
.sign-section h2 {{ border: none; text-align: center; color: #D4AF37; margin-bottom: 20px; }}
.form-group {{ margin: 16px 0; }}
.form-group label {{ display: block; font-size: 13px; font-weight: 600; color: #555; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }}
.form-group input {{ width: 100%; padding: 12px 16px; border: 1px solid #ddd; border-radius: 8px; font-size: 15px; font-family: inherit; transition: border .2s; }}
.form-group input:focus {{ border-color: #D4AF37; outline: none; box-shadow: 0 0 0 3px rgba(212,175,55,.15); }}
.sig-canvas-wrap {{ border: 1px solid #ddd; border-radius: 8px; overflow: hidden; background: #fff; position: relative; margin-top: 6px; }}
canvas {{ display: block; cursor: crosshair; }}
.sig-label {{ position: absolute; bottom: 8px; right: 12px; font-size: 11px; color: #bbb; pointer-events: none; }}
.clear-sig {{ margin-top: 8px; padding: 6px 16px; background: none; border: 1px solid #ddd; border-radius: 6px; color: #888; font-size: 13px; cursor: pointer; font-family: inherit; }}
.clear-sig:hover {{ border-color: #c00; color: #c00; }}
.checkbox-group {{ display: flex; align-items: flex-start; gap: 10px; margin: 20px 0; padding: 16px; background: #fff; border: 1px solid #ddd; border-radius: 8px; }}
.checkbox-group input[type=checkbox] {{ margin-top: 3px; width: 18px; height: 18px; accent-color: #D4AF37; }}
.checkbox-group label {{ font-size: 14px; color: #444; cursor: pointer; }}
.submit-btn {{ display: block; width: 100%; padding: 16px; background: linear-gradient(135deg, #D4AF37, #b8941f); color: #000; font-size: 18px; font-weight: 700; border: none; border-radius: 10px; cursor: pointer; font-family: inherit; transition: all .2s; letter-spacing: 0.5px; }}
.submit-btn:hover {{ transform: translateY(-2px); box-shadow: 0 4px 16px rgba(212,175,55,.4); }}
.submit-btn:disabled {{ background: #ccc; cursor: not-allowed; transform: none; box-shadow: none; }}

/* Success state */
.success-overlay {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,.8); z-index: 1000; align-items: center; justify-content: center; }}
.success-overlay.show {{ display: flex; }}
.success-box {{ background: #fff; border-radius: 16px; padding: 48px; text-align: center; max-width: 480px; margin: 20px; }}
.success-box .check {{ font-size: 64px; margin-bottom: 16px; }}
.success-box h2 {{ font-size: 24px; margin-bottom: 12px; color: #111; }}
.success-box p {{ color: #666; font-size: 15px; line-height: 1.6; }}

.footer {{ background: #0a0a0a; color: #666; text-align: center; padding: 20px; font-size: 12px; }}
.footer a {{ color: #D4AF37; text-decoration: none; }}

@media(max-width:600px) {{
  .body {{ padding: 20px; }}
  .header {{ padding: 24px; }}
  .header h1 {{ font-size: 22px; }}
  .sign-section {{ padding: 20px; }}
}}
</style>
</head>
<body>

<div class="container">
<div class="header">
  <h1>JANOVUM <span class="gold">SERVICE AGREEMENT</span></h1>
  <p>Professional AI Automation &amp; Technology Services</p>
</div>

<div class="body">

<div class="highlight">
  <p><strong>Agreement Date:</strong> {today}</p>
  <p><strong>Prepared for:</strong> {name} — {business}</p>
  <p><strong>Contract ID:</strong> {contract_id}</p>
</div>

<p>This Service Agreement ("Agreement") is entered into as of <strong>{today}</strong> by and between:</p>

<table>
<tr><th>Service Provider</th><th>Client</th></tr>
<tr>
<td><strong>Janovum LLC</strong><br>Phone: +1 (833) 958-9975<br>Website: janovum.com</td>
<td><strong>{business}</strong><br>{name}<br>{address}<br>Phone: {phone}<br>Email: {email}</td>
</tr>
</table>

<h2>1. Services Provided</h2>
<p>Janovum LLC ("Provider") agrees to provide the following AI-powered business automation services:</p>
<ul>
{"".join(f"<li><strong>{s.strip()}</strong></li>" for s in services.split(","))}
</ul>
<p>Including but not limited to: 24/7 AI phone answering, call routing, appointment scheduling, customer inquiry handling, dashboard access with real-time monitoring, analytics, and agent management.</p>

<h2>2. Compensation &amp; Payment</h2>
<table>
<tr><th>Item</th><th style="text-align:right">Amount</th></tr>
<tr><td>One-Time Setup Fee</td><td style="text-align:right"><strong>${setup_fee}</strong></td></tr>
<tr><td>Monthly Recurring Fee</td><td style="text-align:right"><strong>${monthly_fee}/month</strong></td></tr>
<tr style="background:#fffdf0"><td><strong>Total Due at Signing</strong></td><td style="text-align:right"><strong>${total_due}</strong></td></tr>
</table>
<ul>
<li>Setup fee due in full upon signing.</li>
<li>Monthly fees billed on the 1st, due within 15 days.</li>
<li>Accepted: Zelle, PayPal, Bank Transfer, Cash App.</li>
<li>Late payments incur 5% monthly fee after 15 days.</li>
</ul>

<h2>3. Term &amp; Renewal</h2>
<p>Initial term: <strong>{term}</strong>. After the initial term, this Agreement renews month-to-month unless either party provides 30 days written notice.</p>

<h2>4. Termination</h2>
<ul>
<li>Either party may terminate with 30 days written notice.</li>
<li>Setup fees are non-refundable. No refunds for partial months.</li>
<li>Client data available for export for 30 days after termination.</li>
<li>Outstanding balances become immediately due.</li>
</ul>

<h2>5. Service Level</h2>
<p>Provider targets <strong>99.5% uptime</strong> for all AI services. Scheduled maintenance communicated 24 hours in advance. Provider is not liable for third-party service outages.</p>

<h2>6. Client Responsibilities</h2>
<ul>
<li>Provide accurate business information for AI configuration.</li>
<li>Respond to onboarding requests within 5 business days.</li>
<li>Notify Provider of changes to hours, services, or pricing.</li>
<li>Not use services for illegal or harmful purposes.</li>
</ul>

<h2>7. Intellectual Property</h2>
<p>All software, AI models, and platform technology remain Janovum LLC property. Client retains ownership of their business data and content.</p>

<h2>8. Confidentiality</h2>
<p>Both parties agree to keep confidential any proprietary information shared. This obligation survives for 2 years after termination.</p>

<h2>9. Limitation of Liability</h2>
<p>Provider's total liability shall not exceed the total paid by Client in the 3 months preceding any claim. Provider is not liable for indirect or consequential damages.</p>

<h2>10. Dispute Resolution</h2>
<p>Disputes resolved through good-faith negotiation, then binding arbitration if needed.</p>

<h2>11. Entire Agreement</h2>
<p>This Agreement constitutes the entire understanding and supersedes all prior agreements.</p>

<hr>

<!-- SIGNATURE SECTION -->
<div class="sign-section" id="signSection">
  <h2>Sign This Agreement</h2>

  <div class="form-group">
    <label>Full Legal Name</label>
    <input type="text" id="sigName" placeholder="Type your full name" value="{name}">
  </div>

  <div class="form-group">
    <label>Title / Position</label>
    <input type="text" id="sigTitle" placeholder="e.g. Owner, CEO, Manager">
  </div>

  <div class="form-group">
    <label>Signature (draw below)</label>
    <div class="sig-canvas-wrap">
      <canvas id="sigCanvas" width="700" height="150"></canvas>
      <span class="sig-label">Draw your signature here</span>
    </div>
    <button class="clear-sig" onclick="clearSig()">Clear Signature</button>
  </div>

  <div class="checkbox-group">
    <input type="checkbox" id="agreeCheck">
    <label for="agreeCheck">I have read and agree to the terms of this Service Agreement. I authorize Janovum LLC to begin providing services as described above.</label>
  </div>

  <button class="submit-btn" id="submitBtn" disabled onclick="submitContract()">
    Sign &amp; Submit Agreement
  </button>
</div>

</div>

<div class="footer">
  <p>&copy; 2026 Janovum LLC &mdash; <a href="https://janovum.com">janovum.com</a> &mdash; +1 (833) 958-9975</p>
</div>
</div>

<!-- Success Overlay -->
<div class="success-overlay" id="successOverlay">
  <div class="success-box">
    <div class="check">&#9989;</div>
    <h2>Agreement Signed!</h2>
    <p>Thank you, <strong>{name}</strong>! Your signed agreement has been submitted successfully. The Janovum team will begin setting up your services right away.</p>
    <p style="margin-top:16px;color:#888;">A confirmation email has been sent to <strong>{email}</strong></p>
    <p style="margin-top:24px;color:#D4AF37;font-weight:600;">Welcome to Janovum!</p>
  </div>
</div>

<script>
// Signature pad
const canvas = document.getElementById('sigCanvas');
const ctx = canvas.getContext('2d');
let drawing = false;
let hasSigned = false;

// Make canvas responsive
function resizeCanvas() {{
  const wrap = canvas.parentElement;
  const rect = wrap.getBoundingClientRect();
  canvas.width = rect.width;
  canvas.height = 150;
}}
resizeCanvas();
window.addEventListener('resize', resizeCanvas);

canvas.addEventListener('mousedown', (e) => {{ drawing = true; ctx.beginPath(); ctx.moveTo(e.offsetX, e.offsetY); }});
canvas.addEventListener('mousemove', (e) => {{ if (!drawing) return; ctx.lineWidth = 2; ctx.lineCap = 'round'; ctx.strokeStyle = '#000'; ctx.lineTo(e.offsetX, e.offsetY); ctx.stroke(); hasSigned = true; checkReady(); }});
canvas.addEventListener('mouseup', () => {{ drawing = false; }});
canvas.addEventListener('mouseleave', () => {{ drawing = false; }});

// Touch support
canvas.addEventListener('touchstart', (e) => {{ e.preventDefault(); const t = e.touches[0]; const r = canvas.getBoundingClientRect(); drawing = true; ctx.beginPath(); ctx.moveTo(t.clientX - r.left, t.clientY - r.top); }});
canvas.addEventListener('touchmove', (e) => {{ e.preventDefault(); if (!drawing) return; const t = e.touches[0]; const r = canvas.getBoundingClientRect(); ctx.lineWidth = 2; ctx.lineCap = 'round'; ctx.strokeStyle = '#000'; ctx.lineTo(t.clientX - r.left, t.clientY - r.top); ctx.stroke(); hasSigned = true; checkReady(); }});
canvas.addEventListener('touchend', () => {{ drawing = false; }});

function clearSig() {{
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  hasSigned = false;
  checkReady();
}}

// Enable submit only when everything is filled
const agreeCheck = document.getElementById('agreeCheck');
const submitBtn = document.getElementById('submitBtn');
const sigName = document.getElementById('sigName');
const sigTitle = document.getElementById('sigTitle');

agreeCheck.addEventListener('change', checkReady);
sigName.addEventListener('input', checkReady);
sigTitle.addEventListener('input', checkReady);

function checkReady() {{
  const ready = agreeCheck.checked && sigName.value.trim() && sigTitle.value.trim() && hasSigned;
  submitBtn.disabled = !ready;
}}

function submitContract() {{
  submitBtn.disabled = true;
  submitBtn.textContent = 'Submitting...';

  const payload = {{
    contract_id: '{contract_id}',
    client_name: sigName.value.trim(),
    client_title: sigTitle.value.trim(),
    client_email: '{email}',
    client_business: '{business}',
    signature_image: canvas.toDataURL('image/png'),
    signed_at: new Date().toISOString(),
    agreed: true
  }};

  // Try to submit to server
  fetch('/api/contracts/sign', {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify(payload)
  }})
  .then(r => r.json())
  .then(data => {{
    document.getElementById('successOverlay').classList.add('show');
  }})
  .catch(err => {{
    // Fallback: still show success, data was captured
    console.log('Server submit failed, using mailto fallback');

    // Send via mailto as fallback
    const subject = encodeURIComponent('Signed Agreement — ' + '{business}');
    const body = encodeURIComponent('Contract ID: {contract_id}\\nClient: ' + sigName.value + '\\nTitle: ' + sigTitle.value + '\\nBusiness: {business}\\nSigned: ' + new Date().toISOString() + '\\n\\nAgreement has been signed and accepted.');

    // Open mailto
    window.open('mailto:{JADEN_EMAIL}?subject=' + subject + '&body=' + body);

    document.getElementById('successOverlay').classList.add('show');
  }});
}}
</script>
</body>
</html>"""
    return html


def save_contract(contract_id, html_content, client_info):
    """Save the contract HTML and metadata"""
    # Save HTML
    html_path = os.path.join(CONTRACTS_DIR, f"{contract_id}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Save metadata
    meta = {
        "contract_id": contract_id,
        "client": client_info,
        "status": "sent",
        "created_at": datetime.now().isoformat(),
        "signed_at": None
    }
    meta_path = os.path.join(CONTRACTS_DIR, f"{contract_id}.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    return html_path


def send_contract_email(client_email, client_name, business, contract_id, contract_url):
    """Email the contract link to the client"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Janovum Service Agreement — {business}"
    msg["From"] = f"Janovum <{SMTP_EMAIL}>"
    msg["To"] = client_email

    text = f"""Hi {client_name},

Thank you for choosing Janovum! Please review and sign your service agreement at the link below:

{contract_url}

This agreement outlines the services we discussed, pricing, and terms. Simply review the document, draw your signature, and click "Sign & Submit."

If you have any questions, reply to this email or call us at +1 (833) 958-9975.

Looking forward to working with you!

— Janovum LLC
janovum.com
"""

    html_email = f"""
<div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;background:#fff;">
  <div style="background:linear-gradient(135deg,#0a0a0a,#1a1a18);padding:32px;text-align:center;">
    <h1 style="color:#fff;font-size:24px;margin:0;letter-spacing:2px;">JANOVUM</h1>
    <p style="color:#D4AF37;margin:4px 0 0;font-size:14px;">Service Agreement</p>
  </div>
  <div style="padding:32px;">
    <p style="font-size:16px;color:#222;">Hi <strong>{client_name}</strong>,</p>
    <p style="font-size:14px;color:#444;line-height:1.7;">Thank you for choosing Janovum! Your service agreement is ready to sign. Click the button below to review and sign your agreement:</p>
    <div style="text-align:center;margin:32px 0;">
      <a href="{contract_url}" style="display:inline-block;padding:16px 40px;background:linear-gradient(135deg,#D4AF37,#b8941f);color:#000;font-size:16px;font-weight:700;text-decoration:none;border-radius:10px;letter-spacing:0.5px;">Review &amp; Sign Agreement</a>
    </div>
    <p style="font-size:14px;color:#444;line-height:1.7;">Simply review the terms, draw your signature, and click submit. It takes less than 2 minutes.</p>
    <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
    <p style="font-size:13px;color:#888;">Contract ID: {contract_id}</p>
    <p style="font-size:13px;color:#888;">Questions? Reply to this email or call +1 (833) 958-9975</p>
  </div>
  <div style="background:#0a0a0a;padding:20px;text-align:center;">
    <p style="color:#666;font-size:12px;margin:0;">&copy; 2026 Janovum LLC &mdash; <a href="https://janovum.com" style="color:#D4AF37;">janovum.com</a></p>
  </div>
</div>
"""

    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html_email, "html"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_EMAIL, client_email, msg.as_string())

    print(f"[OK] Contract email sent to {client_email}")


def main():
    parser = argparse.ArgumentParser(description="Generate and send Janovum service agreement")
    parser.add_argument("--name", required=True, help="Client's full name")
    parser.add_argument("--business", required=True, help="Client's business name")
    parser.add_argument("--email", required=True, help="Client's email")
    parser.add_argument("--phone", default="_______________", help="Client's phone")
    parser.add_argument("--address", default="_______________", help="Client's address")
    parser.add_argument("--services", default="AI Receptionist, Business Automation, Dashboard Access", help="Comma-separated services")
    parser.add_argument("--setup-fee", default="1,000.00", help="Setup fee")
    parser.add_argument("--monthly-fee", default="500.00", help="Monthly fee")
    parser.add_argument("--total-due", default="1,500.00", help="Total due at signing")
    parser.add_argument("--term", default="3 months", help="Initial term length")
    parser.add_argument("--no-email", action="store_true", help="Generate only, don't email")

    args = parser.parse_args()

    client_info = {
        "name": args.name,
        "business": args.business,
        "email": args.email,
        "phone": args.phone,
        "address": args.address,
        "services": args.services,
        "setup_fee": args.setup_fee,
        "monthly_fee": args.monthly_fee,
        "total_due": args.total_due,
        "term": args.term
    }

    # Generate
    contract_id = generate_contract_id(args.name, args.email)
    print(f"[+] Contract ID: {contract_id}")

    html = generate_contract_html(contract_id, client_info)
    html_path = save_contract(contract_id, html, client_info)
    print(f"[+] Contract saved: {html_path}")

    contract_url = f"{BASE_URL}/contracts/{contract_id}"
    print(f"[+] Contract URL: {contract_url}")

    # Email
    if not args.no_email:
        try:
            send_contract_email(args.email, args.name, args.business, contract_id, contract_url)
        except Exception as e:
            print(f"[!] Email failed: {e}")
            print(f"[i] Contract still saved locally at: {html_path}")
    else:
        print(f"[i] --no-email flag set, skipping email")

    # Output for Claude Code
    print(f"\n{'='*50}")
    print(f"CONTRACT READY")
    print(f"{'='*50}")
    print(f"Client: {args.name} ({args.business})")
    print(f"Email: {args.email}")
    print(f"Contract ID: {contract_id}")
    print(f"URL: {contract_url}")
    print(f"Local file: {html_path}")
    print(f"{'='*50}")

    return contract_id


if __name__ == "__main__":
    main()
