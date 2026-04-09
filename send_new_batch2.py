import json, smtplib, time, random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

leads = [
  {"name": "ManCave For Men", "email": "info@ManCaveForMen.com", "biz": "ManCave For Men", "type": "barbershop"},
  {"name": "The Parlor Barbershoppe", "email": "hello@theparlorshoppe.com", "biz": "The Parlor Barbershoppe", "type": "barbershop"},
  {"name": "Iconic Beauty Miami", "email": "iconicbeautymiami@yahoo.com", "biz": "Iconic Beauty Miami", "type": "hair salon"},
  {"name": "Anais Nails & Spa", "email": "anaisnailspa@gmail.com", "biz": "Anais Nails & Spa", "type": "nail salon"},
  {"name": "Hair Studio & Nail Spa", "email": "info@hairnailspa.com", "biz": "Hair Studio & Nail Spa", "type": "nail salon"},
  {"name": "Doral Elite Collision", "email": "Info@doralelite.com", "biz": "Doral Elite Collision Center", "type": "auto body shop"},
  {"name": "Auto Body Lab", "email": "contactus@autobodylab.com", "biz": "Auto Body Lab", "type": "auto body shop"},
  {"name": "Gables Dental Care", "email": "info@gablesdentalcare.com", "biz": "Gables Dental Care", "type": "dentist"},
  {"name": "Garcia Mayoral Dentistry", "email": "garciamayoraldentistry@gmail.com", "biz": "Garcia Mayoral Dentistry", "type": "dentist"},
  {"name": "Doral Sedation Dentistry", "email": "reservationspecialist@gablessedationdentistry.com", "biz": "Doral Sedation & Family Dentistry", "type": "dentist"},
  {"name": "The Smile Mission", "email": "thesmilemissionflorida@gmail.com", "biz": "The Smile Mission", "type": "dentist"},
  {"name": "Pet Avenue Grooming", "email": "petavenuegrooming@gmail.com", "biz": "Pet Avenue Grooming", "type": "pet groomer"},
  {"name": "The Dog From Ipanema", "email": "info@thedogfromipanema.com", "biz": "The Dog From Ipanema", "type": "pet groomer"},
  {"name": "Miami's Pet Grooming", "email": "info@miamispetgrooming.com", "biz": "Miami's Pet Grooming", "type": "pet groomer"},
  {"name": "Love Hate Tattoo Studio", "email": "lovehatetattooinfo@yahoo.com", "biz": "Love Hate Tattoo Studio", "type": "tattoo shop"},
  {"name": "Tatt Em Up Tattoos", "email": "nglmaxx@yahoo.com", "biz": "Tatt Em Up Tattoos & Piercings", "type": "tattoo shop"},
  {"name": "SKYE INK", "email": "thestudio@skyeink.com", "biz": "SKYE INK Tattoo Studio", "type": "tattoo shop"},
  {"name": "Iris Tattoo Wynwood", "email": "wynwood@iristattoomia.com", "biz": "Iris Tattoo Studio Wynwood", "type": "tattoo shop"},
  {"name": "Fame Tattoos", "email": "FameTattoos@HotMail.com", "biz": "Fame Tattoos", "type": "tattoo shop"},
  {"name": "The Shop Tattoo Studio", "email": "theshoptattoostudio305@gmail.com", "biz": "The Shop Tattoo Studio", "type": "tattoo shop"},
  {"name": "Salvation Tattoo Lounge", "email": "info@salvationtattoolounge.com", "biz": "Salvation Tattoo Lounge", "type": "tattoo shop"},
  {"name": "Fuentes Moving", "email": "pfmoving@gmail.com", "biz": "Fuentes Moving", "type": "moving company"},
  {"name": "The Miami Movers", "email": "info@themiamimovers.com", "biz": "The Miami Movers", "type": "moving company"},
  {"name": "Miami Movers for Less", "email": "sales@miamimoversforless.com", "biz": "Miami Movers for Less", "type": "moving company"},
  {"name": "TMC Movers Miami", "email": "customersupport@tmc.miami", "biz": "TMC Movers Miami", "type": "moving company"},
  {"name": "Royal Movers", "email": "info@royalmoversinc.com", "biz": "Royal Movers Inc", "type": "moving company"},
  {"name": "Econoway Exterminating", "email": "econowayextco@aol.com", "biz": "Econoway Exterminating Co.", "type": "pest control"},
  {"name": "Al-Flex Exterminators", "email": "info@al-flex.com", "biz": "Al-Flex Exterminators", "type": "pest control"},
  {"name": "Sugar Green Gardens", "email": "info@sugargreengardens.com", "biz": "Sugar Green Gardens", "type": "landscaping"},
  {"name": "Grove Tree Service", "email": "Info@GroveTreeServiceFL.com", "biz": "Grove Tree Service & Landscaping", "type": "landscaping"},
  {"name": "Butler Buckley & Deets", "email": "info@bbdins.com", "biz": "Butler Buckley & Deets Insurance", "type": "insurance agency"},
  {"name": "Rovner & Company", "email": "mrovner@rovnerco.com", "biz": "Rovner & Company Insurance", "type": "insurance agency"},
  {"name": "JMK Property Management", "email": "info@jmkpropertymanagement.com", "biz": "JMK Property Management", "type": "property management"},
  {"name": "Rovira Property Management", "email": "info@rovirapm.com", "biz": "Rovira Property Management", "type": "property management"},
  {"name": "Florida Management Group", "email": "info@floridamanagement.net", "biz": "Florida Management & Consulting Group", "type": "property management"},
  {"name": "La Mesa Miami", "email": "info@lamesamiami.com", "biz": "La Mesa Miami", "type": "restaurant"},
  {"name": "Crema Gourmet Doral", "email": "cremagourmetdoral@gmail.com", "biz": "Crema Gourmet", "type": "restaurant"},
  {"name": "MIKA Coral Gables", "email": "hello@mikacoralgables.com", "biz": "MIKA Restaurant", "type": "restaurant"},
  {"name": "Mamey Miami", "email": "hello@mameymiami.com", "biz": "Mamey Miami", "type": "restaurant"},
  {"name": "The Collab Miami", "email": "info@TheCollaborativeAtThesis.com", "biz": "The Collab Restaurant", "type": "restaurant"},
  {"name": "MIAM Cafe", "email": "miamwynwood@gmail.com", "biz": "MIAM Cafe Wynwood", "type": "restaurant"},
  {"name": "Emergency AC Corp", "email": "emergencyaccorp@gmail.com", "biz": "Emergency AC Corp", "type": "HVAC"},
  {"name": "Ponce De Leon Animal Clinic", "email": "poncedeleonreception@gmail.com", "biz": "Ponce De Leon Animal Clinic", "type": "veterinary clinic"},
  {"name": "LaSalle Dry Cleaners", "email": "lasalledrycleanerscg@gmail.com", "biz": "LaSalle Dry Cleaners", "type": "dry cleaner"},
  {"name": "Grove Cleaners", "email": "info@grovecleaners.com", "biz": "Grove Cleaners", "type": "dry cleaner"},
  {"name": "Libre Aerial Fitness", "email": "hello@libreAF.com", "biz": "Libre Aerial Fitness", "type": "fitness studio"}
]

ideas = {
    "barbershop": "answer every call, book appointments automatically, send reminders so clients don't no-show, and follow up for rebookings",
    "hair salon": "handle booking calls 24/7, send appointment reminders, reduce no-shows, and automatically follow up with clients",
    "nail salon": "book appointments by phone or text automatically, send reminders, handle walk-in waitlists, and follow up for repeat visits",
    "auto body shop": "answer estimate calls instantly, schedule drop-offs, send repair status updates, and follow up when jobs are done",
    "dentist": "answer patient calls 24/7, book and confirm appointments, send reminders, handle insurance questions, and reduce no-shows",
    "pet groomer": "book grooming appointments by phone or text, send reminders, handle pricing questions, and follow up for regular schedules",
    "tattoo shop": "handle consultation requests, book appointments, answer pricing and aftercare questions, and manage your waitlist automatically",
    "moving company": "answer quote requests instantly day or night, schedule estimates, follow up on pending quotes, and book moves automatically",
    "pest control": "capture every service call, schedule inspections, send treatment reminders, and follow up for recurring service plans",
    "landscaping": "answer service calls, schedule estimates, send crew schedules, and follow up for recurring maintenance contracts",
    "insurance agency": "handle quote requests 24/7, schedule consultations, follow up on pending policies, and answer common coverage questions",
    "property management": "handle tenant calls and maintenance requests 24/7, schedule showings, screen inquiries, and automate lease renewals",
    "restaurant": "handle reservation calls, answer menu questions, manage waitlists, and send confirmation texts automatically",
    "HVAC": "capture every emergency call 24/7, schedule service appointments, send technician ETAs, and follow up for maintenance plans",
    "veterinary clinic": "answer patient calls, book appointments, send vaccination reminders, handle after-hours emergencies, and reduce no-shows",
    "dry cleaner": "handle pickup/delivery scheduling, send ready-for-pickup notifications, answer pricing questions, and manage regular orders",
    "fitness studio": "handle class bookings, answer membership questions, send class reminders, and follow up with trial members automatically",
}

def build_email(lead):
    name = lead["name"]
    biz = lead["biz"]
    btype = lead["type"]
    idea = ideas.get(btype, "answer calls 24/7, book appointments, send reminders, and handle customer questions automatically")

    templates = [
        f"Hi {name},\n\nI found {biz} online and had a quick question -- how many calls do you think you miss in a week?\n\nFor most {btype}s, the answer is way more than they realize. Every missed call is a lost customer going to a competitor.\n\nWe built an AI receptionist that picks up every single call for you. It can {idea} -- all without you lifting a finger.\n\nIt sounds like your business, answers like a real person, and works 24/7/365. No hold music, no voicemail, no missed revenue.\n\nOne of our clients stopped losing 40% of their calls overnight. Their revenue jumped 15% in month one.\n\nCan I show you a 10-minute demo of what it would sound like for {biz}?\n\n- Jaden Gonzalez\nFounder, Janovum LLC\njanovum.com | janovumllc@gmail.com",

        f"Hey {name},\n\nRunning a {btype} is nonstop -- you're busy with clients and can't always grab the phone. But every missed call is money walking out the door.\n\nWhat if you had an AI assistant that answered every call for {biz}? It can {idea}.\n\nIt's not a robot voice either -- it sounds natural, knows your business, and handles calls exactly how you would.\n\nWe're offering free demos this week to local Miami businesses. Takes 10 minutes and I think you'll be impressed.\n\nWorth a quick look?\n\n- Jaden Gonzalez\nFounder, Janovum LLC\njanovum.com | janovumllc@gmail.com",

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
print("  SENDING TO 46 NEW LEADS")
print("=" * 60)

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
        sent.append({
            "to": lead['email'], "name": lead['name'], "biz": lead['biz'],
            "type": lead['type'], "subject": subject, "time": datetime.now().isoformat()
        })
        if i < len(leads) - 1:
            delay = random.uniform(20, 40)
            print(f"         waiting {delay:.0f}s...")
            time.sleep(delay)
    except Exception as e:
        print(f"[{i+1}/{len(leads)}] FAILED -> {lead['email']}: {e}")
        failed.append({"to": lead['email'], "error": str(e)})

server.quit()

log_file = "outreach_sent_log.json"
with open(log_file) as f:
    existing = json.load(f)
existing["sent"].extend(sent)
existing["total_sent"] = len(existing["sent"])
existing["last_batch"] = "new_leads_batch2"
existing["last_date"] = datetime.now().isoformat()
with open(log_file, "w") as f:
    json.dump(existing, f, indent=2)

print(f"\n{'='*60}")
print(f"  NEW LEADS DONE: {len(sent)} sent, {len(failed)} failed")
print(f"  GRAND TOTAL: {existing['total_sent']}")
print(f"{'='*60}")
