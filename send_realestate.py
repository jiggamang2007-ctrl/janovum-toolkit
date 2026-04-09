import json, smtplib, time, random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

leads = [
    {"name": "Diana Caro Perez", "email": "caroperez2501@gmail.com", "note": "United Real Estate Miami agent"},
    {"name": "Marvin Arrieta", "email": "msarrieta@msn.com", "note": "Coldwell Banker, Coral Gables/Doral luxury"},
    {"name": "InvesTeam Realty", "email": "info@investeamrealty.com", "note": "Doral investment-focused brokerage"},
    {"name": "ComReal Miami", "email": "ssmith@comreal.com", "note": "Commercial real estate Coral Gables"},
    {"name": "ComReal Doral", "email": "industrialteam@comreal.com", "note": "Commercial/industrial Doral"},
    {"name": "Lamacchia Realty Fort Lauderdale", "email": "FtLauderdale@LamacchiaRealty.com", "note": "Fort Lauderdale office"},
    {"name": "Jason Taub", "email": "Jason@TaubRealEstate.com", "note": "Broker/owner Fort Lauderdale"},
    {"name": "D'Angelo Realty Group", "email": "info@dangelorealty.com", "note": "Fort Lauderdale agents"},
    {"name": "Beckett Realty", "email": "info@beckettrealty.com", "note": "Fort Lauderdale brokers"},
]

def build_email(lead):
    name = lead["name"]

    t1 = f"""Hi,

I came across {name} and wanted to share something that could give you a serious edge finding deals.

We built an AI automation that works like having a wholesaler on your team 24/7 — except it costs a fraction of what you'd pay a real one, and it never sleeps.

Here's what it does:
- Scans for high-ROI properties in your target area automatically
- Filters by YOUR criteria — price range, cap rate, neighborhood, property type
- Plugs into whatever listing tools you already use to search properties
- Sends you deals the moment they hit, before your competition sees them
- Runs the numbers for you — estimated ROI, cash flow, rehab costs

Instead of paying a wholesaler thousands per deal, you get an AI doing the same work around the clock for way less.

We're setting this up for a few agents in South Florida right now. Would love to show you how it works — takes 10 minutes.

Check us out: https://janovum.com

Worth a quick call?

Best,
Jaden Gonzalez
Founder, Janovum LLC
janovumllc@gmail.com
https://janovum.com"""

    t2 = f"""Hi,

Quick question — how much time does {name} spend hunting for good investment properties every week?

What if an AI did that for you automatically?

We built an automation that scans listings around the clock, filters by whatever criteria you set — price, ROI, area, property type — and sends you only the deals worth looking at. It connects to whatever tools you already use to pull listings.

Think of it like having a wholesaler working for you 24/7, except:
- No finder's fee per deal
- It never misses a listing
- It runs the numbers automatically (ROI, cash flow, cap rate)
- You set the filters, it does the work

A few agents here in South Florida are already using it and finding deals they would've missed.

I'd love to give you a quick demo — 10 minutes and you'll see exactly how it works.

https://janovum.com

Interested?

Best,
Jaden Gonzalez
Founder, Janovum LLC
janovumllc@gmail.com"""

    t3 = f"""Hi,

I work with real estate agents in South Florida who want to find better deals faster without paying wholesaler fees.

We created an AI-powered deal finder that does what a wholesaler does — but better, cheaper, and 24/7.

It automatically:
- Scans every listing in your target market in real time
- Filters properties by YOUR investment criteria
- Calculates ROI, cap rate, cash flow, and estimated rehab costs
- Connects to whatever platforms you already use for property searches
- Alerts you instantly when a deal matches your filters

No more manually scrolling through hundreds of listings. No more paying thousands in wholesaler fees. Just the right deals delivered to you.

We're offering demos to agents in the area right now. Check us out at https://janovum.com and let me know if you want to see it in action.

Jaden Gonzalez
Founder, Janovum LLC
janovumllc@gmail.com
https://janovum.com"""

    body = random.choice([t1, t2, t3])
    subjects = [
        f"AI Deal Finder for {name} — Better Than a Wholesaler",
        f"Stop paying wholesaler fees — {name}",
        f"Find high-ROI properties on autopilot",
        f"Quick question for {name}",
        f"AI that finds deals before your competition",
    ]
    return random.choice(subjects), body


print(f"Sending {len(leads)} real estate outreach emails...")
print(f"From: myfriendlyagent12@gmail.com (Reply-To: janovumllc@gmail.com)\n")

server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('myfriendlyagent12@gmail.com', 'pdcvjroclstugncx')
print("Connected!\n")

sent = []
failed = []

for i, lead in enumerate(leads):
    subject, body = build_email(lead)
    msg = MIMEMultipart()
    msg['From'] = 'Jaden Gonzalez - Janovum <myfriendlyagent12@gmail.com>'
    msg['Reply-To'] = 'janovumllc@gmail.com'
    msg['To'] = lead['email']
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server.sendmail('myfriendlyagent12@gmail.com', lead['email'], msg.as_string())
        print(f"[{i+1}/{len(leads)}] SENT -> {lead['email']} ({lead['name']})")
        sent.append({"to": lead['email'], "name": lead['name'], "subject": subject, "time": datetime.now().isoformat()})
        if i < len(leads) - 1:
            delay = random.uniform(25, 45)
            print(f"         waiting {delay:.0f}s...")
            time.sleep(delay)
    except Exception as e:
        print(f"[{i+1}/{len(leads)}] FAILED -> {lead['email']}: {e}")
        failed.append({"to": lead['email'], "error": str(e)})

server.quit()

# Append to existing log
log_file = "outreach_sent_log.json"
try:
    with open(log_file) as f:
        existing = json.load(f)
except:
    existing = {"sent": [], "failed": []}

existing["sent"].extend(sent)
existing["failed"].extend(failed)
existing["total_sent"] = len(existing["sent"])
existing["total_failed"] = len(existing["failed"])
existing["last_batch"] = "real_estate"
existing["last_date"] = datetime.now().isoformat()

with open(log_file, "w") as f:
    json.dump(existing, f, indent=2)

print(f"\n{'='*60}")
print(f"  DONE: {len(sent)} sent, {len(failed)} failed")
print(f"  Total outreach so far: {existing['total_sent']} emails")
print(f"{'='*60}")
