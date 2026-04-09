import json, smtplib, time, random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# All scraped leads with REAL emails
leads = [
    {"name": "Midtown Dental Miami", "email": "info@midtowndentalmiami.com", "industry": "dental office"},
    {"name": "Doctor Air HVAC Services", "email": "Info@doctorairhvac.com", "industry": "HVAC company"},
    {"name": "Miami Shores Plumbing", "email": "info@miamishoresplumbing.com", "industry": "plumbing company"},
    {"name": "Marlin Plumbing of Miami", "email": "Theresa@marlinplumbinginc.com", "industry": "plumbing company"},
    {"name": "Rarick Law", "email": "info@raricklaw.com", "industry": "law firm"},
    {"name": "Monaco MedSpa", "email": "officemanager@monacomedspa.com", "industry": "med spa"},
    {"name": "Nava Wellness & Med Spa", "email": "navawellnessmedspa@gmail.com", "industry": "med spa"},
    {"name": "Lumea Med Spa", "email": "support@lumeamedspa.com", "industry": "med spa"},
    {"name": "Yancy Harmony Spa", "email": "yancyvs@gmail.com", "industry": "med spa"},
    {"name": "New Image Works", "email": "info-miami@newimageworks.com", "industry": "med spa"},
    {"name": "Med Aesthetics Miami", "email": "coralgables@medaestheticsmiami.com", "industry": "med spa"},
    {"name": "79th Auto Center", "email": "79autoc@bellsouth.net", "industry": "auto repair shop"},
    {"name": "Miami Pet Clinic", "email": "wecare@miamipetclinic.com", "industry": "veterinary clinic"},
    {"name": "Adams Veterinary Clinic", "email": "adamsvetclinic@aol.com", "industry": "veterinary clinic"},
    {"name": "Bayshore Veterinary Clinic", "email": "bayshorevetclinic@gmail.com", "industry": "veterinary clinic"},
    {"name": "The Miami Chiropractor", "email": "info@themiamichiropractor.com", "industry": "chiropractic office"},
    {"name": "Dr. Martin Grossman Chiropractic", "email": "drgrossmanchiro@aol.com", "industry": "chiropractic office"},
    {"name": "Roofing By Royale", "email": "roofingbyroyale1@gmail.com", "industry": "roofing company"},
    {"name": "Bessard Roofing", "email": "info@bessardroofing.com", "industry": "roofing company"},
    {"name": "Roofer Mike Inc", "email": "roofermike2006@gmail.com", "industry": "roofing company"},
    {"name": "My Angel Service", "email": "support@myangelservice.com", "industry": "electrician"},
    {"name": "Rizo Electric", "email": "RIZOELECTRICFL@GMAIL.COM", "industry": "electrician"},
    {"name": "Active Pest Control", "email": "activepestcontrol1957@gmail.com", "industry": "pest control"},
    {"name": "American Trust Insurance", "email": "info@americantrustins.com", "industry": "insurance agency"},
    {"name": "FLO Pool", "email": "cs@flopool.com", "industry": "pool service"},
    {"name": "Acquality Pool Service", "email": "contact@acqualitypool.com", "industry": "pool service"},
    {"name": "Deep Blue Pool & Spa", "email": "info@dbpoolandspa.com", "industry": "pool service"},
    {"name": "All Miami Pools", "email": "steven@allmiamipools.com", "industry": "pool service"},
    {"name": "PTC Miami Beach", "email": "info@ptcmiami.com", "industry": "physical therapy"},
    {"name": "Physical Therapy NOW Miami Lakes", "email": "MiamiLakes@physicaltherapynow.com", "industry": "physical therapy"},
]

hooks = {
    "dental office": ("patients calling to book cleanings or ask about insurance", "Your front desk is juggling walk-ins and a ringing phone at the same time", "books hygiene appointments, confirms insurance, and handles reschedules"),
    "HVAC company": ("emergency AC calls, especially after hours", "When someone's AC dies at 10pm in Miami heat, they call whoever answers first", "captures every emergency call 24/7, books service appointments, and gives estimates"),
    "plumbing company": ("emergency leak calls nights and weekends", "A burst pipe at 2am means they're calling every plumber until someone picks up", "answers emergency calls instantly, dispatches info to your team, and books jobs"),
    "law firm": ("potential clients calling for consultations", "85% of people who hit voicemail at a law firm never call back", "qualifies leads, books consultations, and collects case details automatically"),
    "med spa": ("clients calling to book Botox, facials, and ask pricing", "Every missed call is a $300+ appointment walking out the door", "books treatments, answers pricing questions, and upsells packages"),
    "auto repair shop": ("customers calling for estimates and drop-off times", "Your mechanics shouldn't be answering phones and customers hate hold music", "gives estimates, books drop-offs, and provides repair status updates"),
    "veterinary clinic": ("pet owners calling about sick pets and scheduling", "A worried pet owner goes to the first vet that picks up, not the best reviewed", "triages calls, books appointments, and handles medication refill requests"),
    "chiropractic office": ("patients calling to book adjustments and ask about insurance", "New patient calls that go to voicemail rarely convert", "books adjustments, handles intake questions, and confirms insurance"),
    "roofing company": ("homeowners calling for quotes after storms", "After every storm your phone blows up and you can't answer them all", "captures every lead, books estimates, and collects property details"),
    "electrician": ("emergency calls for outages and service requests", "Electrical emergencies don't wait for business hours", "handles emergency dispatch, books service calls, and gives troubleshooting"),
    "pest control": ("customers calling about infestations wanting same-day service", "When someone sees roaches they're calling everyone until someone picks up NOW", "books inspections, answers treatment questions, and handles recurring scheduling"),
    "insurance agency": ("clients calling for quotes, claims, and policy questions", "Every unanswered quote request is a customer signing with your competitor", "collects quote info, answers policy FAQs, and routes claims to the right agent"),
    "pool service": ("homeowners calling for cleanings, repairs, and chemical balancing", "Pool season means your phone rings nonstop while you're in someone's backyard", "books service visits, handles recurring scheduling, and answers maintenance questions"),
    "physical therapy": ("patients scheduling sessions and insurance questions", "No-shows and last-minute cancellations kill your revenue", "manages scheduling, confirms appointments, and handles insurance questions"),
}

def build_email(lead):
    name = lead["name"]
    ind = lead["industry"]
    pain, hook, benefit = hooks.get(ind, ("customers calling and not getting through", "Every missed call is money on the table", "answers calls 24/7, books appointments, and handles questions"))

    t1 = f"Hi,\n\nI came across {name} and wanted to reach out with something I think could seriously help your business.\n\n{hook}. That's {pain} going unanswered.\n\nWe built an AI-powered receptionist that {benefit}. It picks up every call on the first ring, 24/7, and sounds completely natural. Your customers won't even know it's AI.\n\nNo hold music. No voicemail. No missed revenue.\n\nWe're working with a few {ind} businesses in South Florida right now. Would love to show you a quick 10-minute demo.\n\nCheck us out: https://janovum.com\n\nWorth a quick call this week?\n\nBest,\nJaden Gonzalez\nFounder, Janovum LLC\njanovumllc@gmail.com\nhttps://janovum.com"

    t2 = f"Hi there,\n\nQuick question - how many calls does {name} miss per week?\n\nFor most {ind} businesses, the answer is more than they think. {hook}.\n\nWe built Janovum - an AI phone receptionist that {benefit}. It answers instantly, sounds human, and works 24/7 including nights, weekends, and holidays.\n\nIt costs less than a part-time employee and never calls in sick.\n\nI'd love to give you a free demo so you can hear it yourself: https://janovum.com\n\nGot 10 minutes this week?\n\nBest,\nJaden Gonzalez\nFounder, Janovum LLC\njanovumllc@gmail.com"

    t3 = f"Hi,\n\nI work with {ind} businesses in South Florida to solve one problem: missed calls costing you real money.\n\n{hook}. {pain.capitalize()} - and every one that goes unanswered is lost revenue.\n\nWe created Janovum - an AI receptionist that {benefit}. It answers every single call on the first ring, 24/7, and sounds just like a real person.\n\nWhat business owners tell us after switching:\n- We stopped losing leads to voicemail overnight\n- It paid for itself in the first week\n\nI'd love to set up {name} with a free demo. Check us out at https://janovum.com\n\nJaden Gonzalez\nFounder, Janovum LLC\njanovumllc@gmail.com\nhttps://janovum.com"

    body = random.choice([t1, t2, t3])
    subjects = [
        f"AI Receptionist for {name} - Never Miss a Call",
        f"Quick question for {name}",
        f"Stop losing calls to voicemail - {name}",
        f"10-min demo for {name}?",
    ]
    return random.choice(subjects), body


print(f"Total leads: {len(leads)}")
print(f"Sending from: myfriendlyagent12@gmail.com (Reply-To: janovumllc@gmail.com)\n")

server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('myfriendlyagent12@gmail.com', 'pdcvjroclstugncx')
print("Connected to Gmail!\n")

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
        sent.append({"to": lead['email'], "name": lead['name'], "subject": subject, "industry": lead['industry'], "time": datetime.now().isoformat()})

        if i < len(leads) - 1:
            delay = random.uniform(20, 40)
            print(f"         waiting {delay:.0f}s...")
            time.sleep(delay)
    except Exception as e:
        print(f"[{i+1}/{len(leads)}] FAILED -> {lead['email']}: {e}")
        failed.append({"to": lead['email'], "name": lead['name'], "error": str(e)})

server.quit()

with open("outreach_sent_log.json", "w") as f:
    json.dump({"sent": sent, "failed": failed, "total_sent": len(sent), "total_failed": len(failed), "date": datetime.now().isoformat()}, f, indent=2)

print(f"\n{'='*60}")
print(f"  DONE: {len(sent)} sent, {len(failed)} failed")
print(f"  Log saved to outreach_sent_log.json")
print(f"{'='*60}")
