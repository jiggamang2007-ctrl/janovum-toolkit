import json, smtplib, time, random, sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

leads = [
  {"name": "Dr. Deborah Longwill", "email": "info@miamidermlaser.com", "biz": "Miami Dermatology & Laser Institute", "type": "dermatology"},
  {"name": "West Kendall Animal Hospital", "email": "info@westkendallvet.com", "biz": "West Kendall Animal Hospital", "type": "veterinary clinic"},
  {"name": "Lux MedSpa Brickell", "email": "info@luxmedspabrickell.com", "biz": "Lux MedSpa Brickell", "type": "med spa"},
  {"name": "Hialeah Auto Care Center", "email": "service@hialeahautocare.com", "biz": "Hialeah Auto Care Center", "type": "auto repair"},
  {"name": "Ivy Accounting", "email": "info@ivy-cpa.com", "biz": "Ivy Accounting Tax & Advisors", "type": "accounting firm"},
  {"name": "Glenn", "email": "glenn@miamicpa.com", "biz": "MiamiCPA LLC", "type": "accounting firm"},
  {"name": "Dr. Alex", "email": "dralex@miami-chiropractors.com", "biz": "Aventura Wellness & Rehab Center", "type": "chiropractor"},
  {"name": "Kendale Air Conditioning", "email": "kendaleair@gmail.com", "biz": "Kendale Air Conditioning", "type": "HVAC"},
  {"name": "Esmelin", "email": "esmelin@goldstarroofing.us", "biz": "Gold Star Roofing & Construction", "type": "roofing"},
  {"name": "Picazzo Painting", "email": "picazzopainting@gmail.com", "biz": "Picazzo Painting Corp", "type": "painting"},
  {"name": "Elekron Electric", "email": "info@elekronelectric.com", "biz": "Elekron Electric Inc", "type": "electrician"},
  {"name": "Miami Power Company", "email": "hello@miamipowercompany.com", "biz": "Miami Power Company", "type": "electrician"},
  {"name": "Miami Physical Therapy", "email": "customerservice@miamipta.com", "biz": "Miami Physical Therapy Associates", "type": "physical therapy"},
  {"name": "Advance Therapy Center", "email": "info@advancetherapycenter.com", "biz": "Advance Therapy Center", "type": "physical therapy"},
  {"name": "IPT Miami", "email": "info@iptmiami.com", "biz": "Integrated Physical Therapy & Wellness", "type": "physical therapy"},
  {"name": "American Towing Service", "email": "dispatch@americantowingservice.net", "biz": "American Towing Service", "type": "towing company"},
  {"name": "Coral Gables Plumbing", "email": "info@coralgablesplumbing.com", "biz": "Coral Gables Plumbing Co", "type": "plumbing"},
  {"name": "Dr. G Dental Studio", "email": "hello@drgdentalstudio.com", "biz": "Dr. G Dental Studio", "type": "dentist"},
  {"name": "All Smiles Dentistry", "email": "allsmiles33161@gmail.com", "biz": "All Smiles General Dentistry", "type": "dentist"},
  {"name": "Miami Dental Group", "email": "kendall@miamidentalgroup.com", "biz": "Miami Dental Group", "type": "dentist"},
  {"name": "Florida Dental Group", "email": "info@floridadentalgroup.com", "biz": "Florida Dental Group of Kendall", "type": "dentist"},
  {"name": "Dental Group of South Florida", "email": "info@dentalsfl.com", "biz": "Dental Group of South Florida", "type": "dentist"},
  {"name": "Dental Total", "email": "info@dentaltotal.com", "biz": "Dental Total", "type": "dentist"},
  {"name": "SONRIE Dental Studio", "email": "info@sonriedentalstudio.com", "biz": "SONRIE Dental Studio", "type": "dentist"},
  {"name": "Dr. Francisco Azar", "email": "xavierazar@gmail.com", "biz": "Azar Dentistry", "type": "dentist"},
  {"name": "Miami Beach Dental Solutions", "email": "info@miamibeachds.com", "biz": "Miami Beach Dental Solutions", "type": "dentist"},
  {"name": "South Gables Dental", "email": "toothdoclar@gmail.com", "biz": "South Gables Dental", "type": "dentist"},
  {"name": "Orthodontic Options Aventura", "email": "aventura@orthodonticoptions.com", "biz": "Orthodontic Options Aventura", "type": "orthodontist"},
  {"name": "Orthodontic Options North Miami", "email": "northmiami@orthodonticoptions.com", "biz": "Orthodontic Options North Miami", "type": "orthodontist"},
  {"name": "Cosmetic Laser Professionals", "email": "NewMe@CLPMedSpa.com", "biz": "Cosmetic Laser Professionals", "type": "med spa"},
  {"name": "Aromas Med Spa", "email": "aromas@me.com", "biz": "Aromas Med Spa", "type": "med spa"},
  {"name": "Idealaser Cosmetic Center", "email": "Idealasermiami@gmail.com", "biz": "Idealaser Cosmetic Center", "type": "med spa"},
  {"name": "AestheteMed", "email": "info@aesthetemed.com", "biz": "AestheteMed", "type": "med spa"},
  {"name": "Prestige Plastic Surgery", "email": "info@prestigeplasticsurgery.com", "biz": "Prestige Plastic Surgery", "type": "plastic surgery"},
  {"name": "Family Medical Group Kendall", "email": "Kendall@TheFamilyMedGroup.com", "biz": "Family Medical Group Kendall", "type": "medical office"},
  {"name": "Family Medical Group Doral", "email": "Doral@thefamilymedgroup.com", "biz": "Family Medical Group Doral", "type": "medical office"},
  {"name": "Family Medical Group Hialeah", "email": "HML@TheFamilyMedGroup.com", "biz": "Family Medical Group Hialeah", "type": "medical office"},
  {"name": "Integrated Comprehensive Urgent Care", "email": "info@integratedcomprehensiveurgentcare.com", "biz": "Integrated Comprehensive Urgent Care", "type": "urgent care"},
  {"name": "Arch Creek Animal Clinic", "email": "esmith@archcreekanimalclinic.com", "biz": "Arch Creek Animal Clinic", "type": "veterinary clinic"},
  {"name": "Crossroads Animal Hospital", "email": "crossroadsah@bellsouth.net", "biz": "Crossroads Animal Hospital", "type": "veterinary clinic"},
  {"name": "Sabal Chase Animal Clinic", "email": "info@scacvet.com", "biz": "Sabal Chase Animal Clinic", "type": "veterinary clinic"},
  {"name": "Alejo Vet Clinic", "email": "contact@alejovetclinic.com", "biz": "Alejo Vet Clinic", "type": "veterinary clinic"},
  {"name": "Dolly's Animal Clinic", "email": "dollysanimalclinic@yahoo.com", "biz": "Dolly's Animal Clinic", "type": "veterinary clinic"},
  {"name": "Bernardo Garcia Funeral Homes", "email": "bernardogarciasmash@gmail.com", "biz": "Bernardo Garcia Funeral Homes", "type": "funeral home"},
  {"name": "Melinda Goncalves CPA", "email": "melinda@mgcpamiami.com", "biz": "Melinda Goncalves CPA PA", "type": "accounting firm"},
  {"name": "G. Moreno", "email": "gmoreno@kendalltaxes.com", "biz": "West Kendall Accounting & Tax Services", "type": "accounting firm"},
  {"name": "TaxLeaf Kendall", "email": "kendall@taxleaf.com", "biz": "TaxLeaf Accounting", "type": "accounting firm"},
  {"name": "Body Shop Pros", "email": "bodyshopprosjenice@gmail.com", "biz": "Body Shop Pros Collision Center", "type": "auto body"},
  {"name": "TemPros Air Conditioning", "email": "temprosair@gmail.com", "biz": "TemPros Air Conditioning & Heating", "type": "HVAC"},
  {"name": "Gamal Riquelme", "email": "gamalr@gmail.com", "biz": "Homestead Property Management", "type": "property management"}
]

ideas = {
    "dermatology": "answer patient calls 24/7, book consultations, send appointment reminders, handle insurance questions, and follow up on treatment plans",
    "veterinary clinic": "answer calls day and night, book appointments, send vaccination reminders, handle after-hours emergencies, and reduce no-shows",
    "med spa": "handle consultation requests 24/7, book treatments, send appointment reminders, answer pricing questions, and follow up for rebookings",
    "auto repair": "answer every service call, schedule drop-offs, send repair status updates, handle estimate requests, and follow up when jobs are done",
    "accounting firm": "handle client calls, schedule consultations, send tax deadline reminders, follow up on document collection, and manage your busy season overflow",
    "chiropractor": "answer patient calls 24/7, book adjustments, send appointment reminders, handle new patient intake, and reduce no-shows",
    "HVAC": "capture every emergency call 24/7, schedule service appointments, send technician ETAs, and follow up for maintenance plans",
    "roofing": "answer estimate calls instantly, schedule inspections, follow up on pending quotes, and never miss a storm-damage lead",
    "painting": "handle quote requests 24/7, schedule estimates, follow up on pending proposals, and book jobs automatically",
    "electrician": "capture every service call, schedule appointments, send technician ETAs, and follow up for repeat business",
    "physical therapy": "answer patient calls, book appointments, send session reminders, handle insurance verification questions, and reduce no-shows",
    "towing company": "answer every dispatch call 24/7, give ETAs, handle roadside assistance requests, and follow up with customers",
    "plumbing": "capture every emergency call day or night, schedule service appointments, send technician ETAs, and follow up for maintenance",
    "dentist": "answer patient calls 24/7, book and confirm appointments, send reminders, handle insurance questions, and reduce no-shows by 30-40%",
    "orthodontist": "handle new patient inquiries, book consultations, send appointment reminders, answer treatment questions, and manage your waitlist",
    "plastic surgery": "handle consultation requests 24/7, book procedures, answer financing questions, send pre/post-op reminders, and follow up on leads",
    "medical office": "answer patient calls 24/7, schedule appointments, handle prescription refill requests, send reminders, and manage after-hours calls",
    "urgent care": "handle patient calls around the clock, provide wait time info, schedule follow-ups, and answer insurance and billing questions",
    "funeral home": "answer calls with compassion 24/7, schedule arrangements, provide service information, and handle after-hours inquiries sensitively",
    "auto body": "answer estimate calls, schedule drop-offs, send repair status updates, handle insurance claim questions, and follow up when vehicles are ready",
    "property management": "handle tenant calls and maintenance requests 24/7, schedule showings, screen inquiries, and automate lease renewal reminders",
}

def build_email(lead):
    name = lead["name"]
    biz = lead["biz"]
    btype = lead["type"]
    idea = ideas.get(btype, "answer calls 24/7, book appointments, send reminders, and handle customer questions automatically")

    templates = [
        f"Hi {name},\n\nI found {biz} online and had a quick question -- how many calls do you think you miss in a week?\n\nFor most businesses like yours, the answer is way more than they realize. Every missed call is a lost customer going to a competitor.\n\nWe built an AI receptionist that picks up every single call for you. It can {idea} -- all without you lifting a finger.\n\nIt sounds like your business, answers like a real person, and works 24/7/365. No hold music, no voicemail, no missed revenue.\n\nOne of our clients stopped losing 40% of their calls overnight. Their revenue jumped 15% in month one.\n\nCan I show you a 10-minute demo of what it would sound like for {biz}?\n\n- Jaden Gonzalez\nFounder, Janovum LLC\njanovum.com | janovumllc@gmail.com",

        f"Hey {name},\n\nRunning a business like {biz} is nonstop -- you're busy with clients and can't always grab the phone. But every missed call is money walking out the door.\n\nWhat if you had an AI assistant that answered every call for {biz}? It can {idea}.\n\nIt's not a robot voice either -- it sounds natural, knows your business, and handles calls exactly how you would.\n\nWe're offering free demos this week to local Miami businesses. Takes 10 minutes and I think you'll be impressed.\n\nWorth a quick look?\n\n- Jaden Gonzalez\nFounder, Janovum LLC\njanovum.com | janovumllc@gmail.com",

        f"Hi {name},\n\nQuick pitch for {biz}:\n\nWe build AI phone systems that {idea}. It answers calls in your business's voice, 24/7, and never misses a beat.\n\nWhy business owners love it:\n- Never miss a call again (even at 2am)\n- Clients book themselves without waiting on hold\n- You save 20+ hours/week on phone tag and admin\n- Costs less than a part-time receptionist\n\nWe're based in Miami and already working with local businesses like yours.\n\nFree 10-min demo -- no commitment. Just reply \"interested\" and I'll set it up.\n\n- Jaden Gonzalez\nFounder, Janovum LLC\njanovum.com | janovumllc@gmail.com"
    ]

    subjects = [
        f"Never miss another call at {biz}",
        f"Quick question for {biz}",
        f"AI receptionist for {biz} -- free demo",
        f"How many calls is {biz} missing?",
        f"{name} -- 10 min could change your business",
    ]

    return random.choice(subjects), random.choice(templates)

print("=" * 60)
print("  BATCH 3: SENDING TO 50 NEW LEADS")
print("=" * 60)
sys.stdout.flush()

server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('myfriendlyagent12@gmail.com', 'pdcvjroclstugncx')
print("Connected!\n")
sys.stdout.flush()

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
        sys.stdout.flush()
        sent.append({
            "to": lead['email'], "name": lead['name'], "biz": lead['biz'],
            "type": lead['type'], "subject": subject, "time": datetime.now().isoformat()
        })
        if i < len(leads) - 1:
            delay = random.uniform(20, 40)
            print(f"         waiting {delay:.0f}s...")
            sys.stdout.flush()
            time.sleep(delay)
    except Exception as e:
        print(f"[{i+1}/{len(leads)}] FAILED -> {lead['email']}: {e}")
        sys.stdout.flush()
        failed.append({"to": lead['email'], "error": str(e)})

server.quit()

log_file = "outreach_sent_log.json"
with open(log_file) as f:
    existing = json.load(f)
existing["sent"].extend(sent)
existing["total_sent"] = len(existing["sent"])
existing["last_batch"] = "batch3_medical_dental_services"
existing["last_date"] = datetime.now().isoformat()
with open(log_file, "w") as f:
    json.dump(existing, f, indent=2)

print(f"\n{'='*60}")
print(f"  BATCH 3 DONE: {len(sent)} sent, {len(failed)} failed")
print(f"  GRAND TOTAL: {existing['total_sent']} emails sent")
print(f"{'='*60}")
