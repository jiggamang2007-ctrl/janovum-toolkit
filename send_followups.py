import json, smtplib, time, random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

bounced = [
    '79autoc@bellsouth.net', 'drgrossmanchiro@aol.com', 'info@bessardroofing.com',
    'support@myangelservice.com', 'serviceatic@gmail.com', 'info@dangelorealty.com',
    'cristina@whitehousewp.com', 'info@pirtleconstruction.com', 'info@legocc.com',
    'info@restaurantownermarketing.com', 'info@autodealmiami.net', 'info@venturebuilders.co'
]

with open('outreach_sent_log.json', 'r') as f:
    data = json.load(f)

delivered = [e for e in data['sent'] if e['to'].lower() not in [b.lower() for b in bounced]]

def build_followup(name, biz):
    followups = [
        f"Hey {name},\n\nJust bumping this up -- I sent a note yesterday about helping {biz} with AI automation.\n\nReal quick: we build AI that answers your phone calls 24/7, books appointments, and handles customer questions automatically. Businesses we work with are saving 20+ hours a week.\n\nI recorded a 2-minute demo showing exactly what it would look like for {biz}. Want me to send it over?\n\n- Jaden\nJanovum LLC | janovum.com",
        f"Hey {name},\n\nFollowing up -- did you get a chance to see my email yesterday?\n\nI know you're busy running {biz}, that's exactly why I reached out. We build AI systems that handle the stuff eating up your time -- answering calls, booking clients, following up on leads -- all on autopilot.\n\nIt takes 10 minutes to see. If it's not a fit, no worries at all.\n\nWorth a quick look?\n\n- Jaden\nJanovum LLC | janovum.com",
        f"Hi {name},\n\nCircling back on my email from yesterday.\n\nI wanted to share something real quick -- one of our clients (similar business to {biz}) went from missing 40% of their calls to capturing every single one with our AI receptionist. Their revenue went up 15% in the first month just from not losing leads.\n\nHappy to show you a quick demo if you're curious. No pressure, no commitment -- just 10 minutes.\n\n- Jaden\nJanovum LLC | janovum.com"
    ]
    subjects = [
        f"Re: Quick question for {name}",
        f"Following up - {biz}",
        f"Did you see this, {name}?",
        f"Re: 10-min demo for {biz}?",
    ]
    return random.choice(subjects), random.choice(followups)

print("=" * 60)
print("  PHASE 1: FOLLOW-UP EMAILS")
print("=" * 60)

server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('myfriendlyagent12@gmail.com', 'pdcvjroclstugncx')
print("Connected!\n")

sent_followups = []
failed_followups = []

for i, lead in enumerate(delivered):
    biz_name = lead.get('biz', lead.get('name', 'Business'))
    name = lead.get('name', biz_name)
    subject, body = build_followup(name, biz_name)

    msg = MIMEMultipart()
    msg['From'] = 'Jaden Gonzalez - Janovum <myfriendlyagent12@gmail.com>'
    msg['Reply-To'] = 'janovumllc@gmail.com'
    msg['To'] = lead['to']
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server.sendmail('myfriendlyagent12@gmail.com', lead['to'], msg.as_string())
        print(f"[{i+1}/{len(delivered)}] FOLLOW-UP SENT -> {lead['to']} ({biz_name})")
        sent_followups.append({
            "to": lead['to'], "name": name, "biz": biz_name,
            "subject": subject, "type": "followup",
            "time": datetime.now().isoformat()
        })
        if i < len(delivered) - 1:
            delay = random.uniform(20, 40)
            print(f"         waiting {delay:.0f}s...")
            time.sleep(delay)
    except Exception as e:
        print(f"[{i+1}/{len(delivered)}] FAILED -> {lead['to']}: {e}")
        failed_followups.append({"to": lead['to'], "error": str(e)})

server.quit()

log_file = "outreach_sent_log.json"
with open(log_file) as f:
    existing = json.load(f)
if "followups" not in existing:
    existing["followups"] = []
existing["followups"].extend(sent_followups)
existing["last_followup_date"] = datetime.now().isoformat()
existing["total_followups"] = len(existing["followups"])
with open(log_file, "w") as f:
    json.dump(existing, f, indent=2)

print(f"\nFOLLOW-UPS DONE: {len(sent_followups)} sent, {len(failed_followups)} failed")
