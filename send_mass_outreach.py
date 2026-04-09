import json, smtplib, time, random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

leads = [
    # MARKETING AGENCIES
    {"name": "Lazaro Jimenez", "email": "lazaro@marketingsvc.com", "biz": "Essential Marketing Miami", "type": "marketing agency"},
    # ACCOUNTING / CPA
    {"name": "Fabricant & Company", "email": "info@fabcocpa.com", "biz": "Fabricant & Company CPA", "type": "accounting firm"},
    {"name": "GLSC & Company", "email": "info@glsccpa.com", "biz": "GLSC & Company", "type": "accounting firm"},
    {"name": "Berkowitz Pollack Brant", "email": "info@bpbcpa.com", "biz": "Berkowitz Pollack Brant", "type": "accounting firm"},
    # CLEANING / JANITORIAL
    {"name": "A&M Janitorial", "email": "info@am-nw.com", "biz": "A&M Janitorial Services", "type": "cleaning company"},
    {"name": "Integrity Services", "email": "info@integrityservicecompanies.com", "biz": "Integrity Services", "type": "cleaning company"},
    # PHOTOGRAPHY
    {"name": "Photography by Iris", "email": "info@photographybyiris.com", "biz": "Photography by Iris", "type": "photography studio"},
    {"name": "White House Wedding Photography", "email": "cristina@whitehousewp.com", "biz": "White House Wedding Photography", "type": "photography studio"},
    {"name": "Photo Video Create", "email": "photovideocreate@gmail.com", "biz": "Miami Photographer", "type": "photography studio"},
    # SALON / BARBERSHOP
    {"name": "Assembly Hair Miami", "email": "hello@assemblymiami.com", "biz": "Assembly Hair Miami", "type": "salon"},
    # TOWING
    {"name": "Roadway Towing", "email": "info@towmiami.com", "biz": "Roadway Towing", "type": "towing company"},
    # CONSTRUCTION (from websites)
    {"name": "Pirtle Construction", "email": "info@pirtleconstruction.com", "biz": "Pirtle Construction", "type": "construction company"},
    {"name": "LEGO Construction", "email": "info@legocc.com", "biz": "LEGO Construction Co", "type": "construction company"},
    # MORE REAL ESTATE (owner emails)
    {"name": "Beatriz Goudie", "email": "beatriz@makecoralgableshome.com", "biz": "Coral Gables Luxury Real Estate", "type": "real estate"},
    # MORE FROM PREVIOUS SEARCHES - different industries
    {"name": "Restaurant Owner Marketing", "email": "info@restaurantownermarketing.com", "biz": "Restaurant Owner Marketing", "type": "restaurant marketing"},
    # AUTO
    {"name": "AutoDeal Miami", "email": "info@autodealmiami.net", "biz": "AutoDeal Miami", "type": "car dealership"},
    {"name": "Super Autos Miami", "email": "info@superautosmiami.com", "biz": "Super Autos Miami", "type": "car dealership"},
    # FITNESS
    {"name": "Core Fitness Miami", "email": "info@corefitnessmiami.com", "biz": "Core Fitness Miami", "type": "gym"},
    {"name": "ERA Fit", "email": "info@erafit.com", "biz": "ERA Fit", "type": "gym"},
]


def build_email(lead):
    name = lead["name"]
    biz = lead["biz"]
    btype = lead["type"]

    # General AI automation pitch - tailored per business type
    automation_ideas = {
        "marketing agency": "automate client reporting, social media scheduling, lead qualification, and campaign analytics",
        "accounting firm": "automate client intake, document collection, appointment scheduling, tax deadline reminders, and invoice follow-ups",
        "cleaning company": "automate booking requests, client scheduling, follow-up reminders, quote generation, and review collection",
        "photography studio": "automate booking inquiries, client scheduling, contract sending, payment reminders, and gallery delivery",
        "salon": "automate appointment booking, reminders, no-show follow-ups, review requests, and client retention campaigns",
        "towing company": "automate dispatch calls, ETA updates, customer follow-ups, and 24/7 call answering",
        "construction company": "automate lead intake, estimate requests, project status updates, subcontractor coordination, and client communication",
        "real estate": "automate property deal finding, lead qualification, showing scheduling, follow-ups, and market analysis reports",
        "restaurant marketing": "automate reservation handling, review responses, customer loyalty campaigns, and social media content",
        "car dealership": "automate lead follow-ups, test drive scheduling, inventory alerts, financing pre-qualification, and customer retention",
        "gym": "automate membership inquiries, class scheduling, trial bookings, payment reminders, and client retention outreach",
    }

    ideas = automation_ideas.get(btype, "automate repetitive tasks, handle customer inquiries 24/7, and streamline your operations")

    t1 = f"""Hi {name},

I came across {biz} and wanted to reach out — we help businesses like yours save time and money with AI automation.

We build custom AI systems that {ideas} — all running automatically so you and your team can focus on what actually makes money.

Here's what makes us different:
- Everything is custom-built for YOUR business, not a generic template
- We can automate almost anything that's repetitive and time-consuming
- Our AI answers calls, responds to inquiries, and handles tasks 24/7
- It costs a fraction of hiring someone to do it manually

We're working with several businesses in South Florida right now and the results have been crazy — owners are saving 20+ hours a week on stuff that used to eat up their whole day.

Would love to show you what we could automate for {biz}. Takes 10 minutes.

https://janovum.com

Best,
Jaden Gonzalez
Founder, Janovum LLC
janovumllc@gmail.com
https://janovum.com"""

    t2 = f"""Hi {name},

Quick question — how many hours per week does your team spend on tasks that could be automated?

For most {btype} businesses, it's way more than they realize. That's where we come in.

We build AI automations that {ideas}. Think of it as hiring a tireless assistant that works 24/7 and never drops the ball.

A few things we can do for {biz}:
- Answer every call and inquiry instantly, day or night
- Automate scheduling, follow-ups, and reminders
- Handle repetitive admin work so your team focuses on revenue
- Custom AI workflows built specifically for your business

We're not a one-size-fits-all tool — everything is built around how YOUR business actually operates.

Interested in a quick 10-minute demo? Check us out: https://janovum.com

Best,
Jaden Gonzalez
Founder, Janovum LLC
janovumllc@gmail.com"""

    t3 = f"""Hi {name},

I work with {btype} businesses in South Florida to automate the stuff that eats up your time and costs you money.

We build AI-powered systems that {ideas} — all running on autopilot.

What business owners tell us:
- "I'm saving 20+ hours a week on admin work"
- "We haven't missed a single lead since switching"
- "It paid for itself in the first month"

Every automation we build is custom for your business. No cookie-cutter solutions.

I'd love to show you what's possible for {biz}. Takes 10 minutes and I think you'll be surprised.

https://janovum.com

Jaden Gonzalez
Founder, Janovum LLC
janovumllc@gmail.com
https://janovum.com"""

    body = random.choice([t1, t2, t3])
    subjects = [
        f"AI automation for {biz} — save 20+ hours/week",
        f"Quick question for {name}",
        f"What if {biz} ran on autopilot?",
        f"Custom AI for {biz} — 10 min demo",
        f"Stop doing manually what AI can handle — {biz}",
    ]
    return random.choice(subjects), body


print(f"Sending {len(leads)} AI automation outreach emails...")
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
        print(f"[{i+1}/{len(leads)}] SENT -> {lead['email']} ({lead['biz']})")
        sent.append({"to": lead['email'], "name": lead['name'], "biz": lead['biz'], "type": lead['type'], "subject": subject, "time": datetime.now().isoformat()})
        if i < len(leads) - 1:
            delay = random.uniform(25, 45)
            print(f"         waiting {delay:.0f}s...")
            time.sleep(delay)
    except Exception as e:
        print(f"[{i+1}/{len(leads)}] FAILED -> {lead['email']}: {e}")
        failed.append({"to": lead['email'], "error": str(e)})

server.quit()

# Append to log
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
existing["last_batch"] = "mass_ai_automation"
existing["last_date"] = datetime.now().isoformat()

with open(log_file, "w") as f:
    json.dump(existing, f, indent=2)

print(f"\n{'='*60}")
print(f"  DONE: {len(sent)} sent, {len(failed)} failed")
print(f"  GRAND TOTAL: {existing['total_sent']} emails sent today")
print(f"{'='*60}")
