"""
Enrich CRM leads with tailored pitch notes based on what Janovum can ACTUALLY build for them.
Not just AI receptionist — custom AI tools, automations, dashboards, whatever they need.
Fetches all leads, overwrites notes, pushes back to server.
"""
import requests, json, time

API = "https://janovum.com/api/crm/contacts"

def get_first_name(full_name):
    if not full_name:
        return "there"
    parts = full_name.strip().split()
    return parts[0].capitalize() if parts else "there"

def categorize(company, name):
    c = company.upper()
    cats = {
        "trucking":      ["TRUCK","FREIGHT","LOGISTIC","TRANSPORT","HAULING","CARGO","MOVING","DISPATCH"],
        "construction":  ["CONSTRUCT","CONTRAC","RENOVATION","BUILDER","ROOFING","REMODEL","CONCRETE","FLOORING","DRYWALL","PLUMBING","EXCAVAT","MASON","PAVING","FRAMING","WATERPROOF"],
        "home_services": ["HOME","CLEANING","MAID","HVAC","ELECTRIC","PLUMB","PAINT","LANDSCAP","LAWN","GUTTER","PRESSURE","HANDYMAN","MAINTENANCE","REPAIR","PEST","POOL","IRRIGATION","FENCE"],
        "restaurant":    ["CAFE","RESTAURANT","DINER","BISTRO","KITCHEN","FOOD","PIZZA","BURGER","TACO","SUSHI","GRILL","EATERY","LOUNGE","BAR","PUB","FUSION","SICILIAN","PANE","CUPI","STEAKHOUSE","SEAFOOD","WINGS"],
        "auto":          ["AUTO","CAR WASH","COLLISION","TIRE","VEHICLE","MOTOR","BODY SHOP","MECHANIC","DETAILING","TOWING","AUTO GLASS","TRANSMISSION","BRAKES","OIL CHANGE"],
        "medical":       ["MEDICAL","HEALTH","DENTAL","CLINIC","DOCTOR","THERAPY","WELLNESS","CARE","CHIRO","ORTHO","PHARMA","DHUPER","PEDIATRIC","VISION","OPTOM","HEARING","DERMA","PHYSICAL"],
        "legal":         ["LAW","ATTORNEY","LEGAL","FIRM","COUNSEL","ZARBALAS","ESQUIRE","LITIGATION","INJURY","CRIMINAL","DIVORCE","IMMIGRATION"],
        "real_estate":   ["REAL ESTATE","REALTY","PROPERTY","LOTS","RENTALS","LEASING","HOUSING","APARTMENT","CONDO","LAND","HOMES","MORTGAGE","TITLE","BROKERAGE","INVEST"],
        "events":        ["EVENT","WEDDING","PARTY","CATERING","DESIGN","DECOR","PHOTO","VIDEO","SOUND","ILLUMIN","ENTERTAINMENT","SPARKLING","DJ","FLORIST","VENUE"],
        "accounting":    ["ACCOUNT","TAX","BOOKKEEP","CPA","FINANCE","FINANCIAL","ADVISORY","CONSULTING","PAYROLL","AUDIT"],
        "telecom":       ["TELECOM","COMMUNICATION","NETWORK","CABLE","FIBER","WIRELESS","INTERNET","TWISTED PAIR","A&J TELE"],
        "marine":        ["MARINE","BOAT","YACHT","CRUISE","VESSEL","HARBOR","DOCK","MARINA","WATERCRAFT"],
        "farm":          ["FARM","AGRI","RANCH","LIVESTOCK","CROP","HARVEST","NURSERY","GREENHOUSE"],
        "signage":       ["SIGN","PRINT","BANNER","GRAPHIC","DISPLAY","ELECTRIC SIGN","WRAP","VINYL"],
        "salon":         ["SALON","BARBER","HAIR","BEAUTY","SPA","NAIL","LASH","BROW","WAXING","TATTOO","PIERCING"],
        "vacation":      ["VACATION","AIRBNB","SHORT TERM","RESORT","LODGE","INN","HOTEL","MOTEL","BNB","POCONOS","HOSPITALITY"],
        "storage":       ["STORAGE","SHED","SELF STOR","MINI STOR","WAREHOUSE","SELF-STOR"],
        "staffing":      ["STAFF","RECRUIT","HIRING","PLACEMENT","WORKFORCE","EMPLOYMENT","HR","TEMP AGENC"],
        "tech":          ["TECH","SOFTWARE","IT SERVICE","DIGITAL","WEB DESIGN","APP DEV","SAAS","CLOUD","MANAGED IT","CYBERSEC"],
        "insurance":     ["INSURANCE","INSUR","COVERAGE","POLICY","CLAIMS","UNDERWRITE"],
        "retail":        ["RETAIL","STORE","SHOP","BOUTIQUE","OUTLET","MARKET","MERCHANDISE","SUPPLY","WHOLESALE"],
        "gym":           ["GYM","FITNESS","CROSSFIT","YOGA","PILATES","MARTIAL","BOXING","TRAINING","SPORT","ATHLETIC"],
        "childcare":     ["CHILD","DAYCARE","PRESCHOOL","ACADEMY","LEARNING","TUTORING","SCHOOL","EDUCATION","MONTESSORI"],
    }
    for cat, keywords in cats.items():
        for kw in keywords:
            if kw in c:
                return cat
    return "general"


PITCH = {

    "trucking": lambda n, co: f"""Hi {n}, I'm reaching out from Janovum — we build custom AI systems for trucking and logistics companies like {co}.

WHAT WE CAN BUILD FOR YOU:
- AI load board monitor — scans DAT/Truckstop 24/7, alerts you the second a high-paying load matches your lanes and truck type. No more refreshing manually.
- Automated dispatcher assistant — when a shipper calls, AI captures load details, checks schedule, and texts you a summary so you can confirm in one tap.
- Driver communication system — auto-send pickup/delivery confirmations, ETA updates to shippers, and check-in reminders to drivers.
- Invoice & paperwork automation — auto-generate rate confirmations and invoices from load details. Reduces back-office time by hours per week.
- Compliance tracker — keeps DOT expiration dates (licenses, medicals, registrations) and pings you before anything lapses.

PAIN POINTS TO HIT:
• "Dispatchers miss high-value loads while managing current ones."
• "Shippers call and nobody answers — they move to the next carrier."
• "Paperwork piles up and invoices go out late."

OPENER: "What's your biggest headache right now — finding loads, managing drivers, or the paperwork?"

$1,000–$3,000 setup depending on scope | $500/mo maintenance
INDUSTRY: Trucking/Logistics | OWNER: {n}""",


    "construction": lambda n, co: f"""Hi {n}, I'm reaching out from Janovum — we build custom AI automation for contractors and construction companies like {co}.

WHAT WE CAN BUILD FOR YOU:
- Automated bid request system — when a homeowner or GC submits a job request, AI collects project details, sends a scoping questionnaire, and schedules your estimate — all without you touching a phone.
- Job site progress tracker — daily photo reports from crews, auto-compiled into a client-facing update sent every Friday. Clients stay informed, you stay on site.
- Subcontractor coordination — AI manages sub availability, sends job details, collects confirmations, and follows up on no-shows.
- Material cost tracker — logs your supplier quotes, flags price increases, and keeps a running job cost against your bid margin.
- Lead follow-up machine — most contractors quote and forget. We build a sequence that follows up on every estimate automatically until they book or say no.

PAIN POINTS TO HIT:
• "I'm on a job site all day and miss calls from new customers — they hire someone else."
• "I spend hours chasing subs and sending update texts to clients."
• "I quote jobs and never hear back — no follow-up system."

OPENER: "Are you losing jobs to faster-responding competitors, or is the back-office stuff eating your time?"

$1,500–$3,000 setup | $500/mo
INDUSTRY: Construction/Contracting | OWNER: {n}""",


    "home_services": lambda n, co: f"""Hi {n}, I'm reaching out from Janovum — we build AI automation systems for home service businesses like {co}.

WHAT WE CAN BUILD FOR YOU:
- Smart scheduling system — AI books appointments via text or web form, fills open slots automatically, sends reminders, and re-books cancellations from a waitlist.
- Route optimization — takes your jobs for the day and builds the most efficient drive order. Saves 30–60 min of driving per tech per day.
- Automated quote follow-up — send an estimate, AI follows up 24h later, then 3 days, then 7 days with a different angle each time until they respond.
- Review generation system — after every completed job, AI sends a personalized text asking for a Google review. Most clients 2-3x their review count in 60 days.
- Seasonal campaign automation — before summer/winter, auto-text your past customers about HVAC tune-ups, gutter cleaning, lawn prep, etc. Fills your calendar months out.

PAIN POINTS TO HIT:
• "Evenings and weekends I miss calls — those are when homeowners are actually free to schedule."
• "I send quotes and never follow up — too busy."
• "I have 50 past customers I never re-marketed to."

OPENER: "What fills your schedule right now — word of mouth, Google, or something else?"

$1,000–$2,000 setup | $500/mo
INDUSTRY: Home Services | OWNER: {n}""",


    "restaurant": lambda n, co: f"""Hi {n}, I'm reaching out from Janovum — we build AI-powered systems for restaurants like {co}.

WHAT WE CAN BUILD FOR YOU:
- Reservation & waitlist system — AI takes reservations via phone, text, or web widget, manages the waitlist, and sends automated confirmation/reminder texts. Kills no-shows.
- Demand forecasting dashboard — analyzes your past sales data + local events/weather to predict how many covers you'll do each shift. Order the right amount, staff correctly.
- Automated review management — after each visit, AI texts guests asking for a Google review. Negative feedback gets routed to you privately before it hits Google.
- Menu performance tracker — shows which dishes are highest margin, which are slowest, which get reordered most. Data to cut the menu smartly.
- Catering & event lead capture — AI handles every catering inquiry: collects details, sends your package info, follows up, and books the consultation.

PAIN POINTS TO HIT:
• "No-shows are killing us — we hold tables and then nobody comes."
• "We have 200 reviews but they're from 3 years ago — we stopped asking."
• "I'm guessing on inventory and over-ordering every week."

OPENER: "Biggest issue right now — no-shows, staffing, or getting new customers in the door?"

$1,500–$2,500 setup | $500/mo
INDUSTRY: Restaurant/Food & Bev | OWNER: {n}""",


    "auto": lambda n, co: f"""Hi {n}, I'm reaching out from Janovum — we build AI automation for auto shops like {co}.

WHAT WE CAN BUILD FOR YOU:
- Online service scheduler — customers book their own appointments 24/7 via text or web. AI confirms, sends reminders, and follows up when they're overdue for service.
- Automated service reminders — tracks every customer's last visit and service type. Sends a text 3 months later: "Your oil change is coming up — want to lock in Tuesday?" Brings customers back without you lifting a finger.
- Vehicle history dashboard — logs every repair per vehicle. When a customer calls in, you instantly see their full history, build trust, and spot upsell opportunities.
- Parts inventory alerts — AI monitors your most-used parts and alerts you when stock drops below your set threshold. No more emergency orders.
- Review request automation — after pickup, AI texts customers a review request. Shops using this consistently reach 4.8+ stars.

PAIN POINTS TO HIT:
• "Mechanics can't answer phones while under a car — customers call and go to the next shop."
• "Past customers disappear and we never follow up to bring them back."
• "We have 40 reviews from 2 years ago and stopped growing."

OPENER: "How do most of your new customers find you right now?"

$1,000–$2,000 setup | $500/mo
INDUSTRY: Auto Shop | OWNER: {n}""",


    "medical": lambda n, co: f"""Hi {n}, I'm reaching out from Janovum — we build AI automation for medical and health practices like {co}.

WHAT WE CAN BUILD FOR YOU:
- No-show reduction system — automated appointment reminders via text/call 48h and 2h before. Confirms attendance, allows easy reschedule. Cuts no-shows 30–50%.
- Patient intake automation — new patients fill out forms digitally before arrival. AI pre-screens reason for visit and flags urgent cases. Front desk spends zero time on paper.
- Insurance pre-verification bot — AI checks insurance eligibility before the appointment and alerts staff of any coverage issues. Eliminates billing surprises.
- Recall campaign system — auto-texts patients who haven't visited in 6/12 months with a personalized message. Reactivates lapsed patients on autopilot.
- After-visit follow-up — 24h after each visit, AI sends a check-in text. Builds patient loyalty and catches problems before they become bad reviews.

PAIN POINTS TO HIT:
• "No-shows cost us $200–$400 per slot — it's our biggest revenue leak."
• "Front desk spends all day on calls that should be automated."
• "We have 800 inactive patients we've never tried to reactivate."

OPENER: "How many no-shows are you seeing per week on average?"

$1,500–$3,000 setup | $500/mo (HIPAA-friendly workflows)
INDUSTRY: Medical/Health | OWNER: {n}""",


    "legal": lambda n, co: f"""Hi {n}, I'm reaching out from Janovum — we build AI tools for law firms like {co}.

WHAT WE CAN BUILD FOR YOU:
- 24/7 AI intake system — potential clients call or fill out a web form at any hour. AI qualifies them (practice area, urgency, case value), schedules a consultation, and sends you a detailed summary. Every missed call at 9pm is a case — we catch them all.
- Case deadline tracker — AI monitors all your matter deadlines, statute of limitations dates, and court dates. Sends alerts to you and your team before anything slips.
- Document automation — intake forms, engagement letters, demand letters, NDAs. AI drafts them from a template using client data. Attorneys review, not draft from scratch.
- Client communication portal — clients check case status, upload documents, and get updates via a secure link. Reduces "where are we on my case?" calls by 80%.
- Review & referral system — after closing a case, AI requests a Google review and asks if they know anyone who needs legal help. Referral pipeline on autopilot.

PAIN POINTS TO HIT:
• "We miss calls when we're in court or depositions — those are high-value cases walking to a competitor."
• "Associates spend hours drafting standard documents that should be templated."
• "Clients constantly call to check in — it's eating up billable time."

OPENER: "What practice areas are you focused on right now? I want to make sure what we build fits your case types."

$2,000–$4,000 setup | $500–$750/mo
INDUSTRY: Legal | OWNER: {n}""",


    "real_estate": lambda n, co: f"""Hi {n}, I'm reaching out from Janovum — we build AI tools specifically for real estate professionals like {co}.

WHAT WE CAN BUILD FOR YOU:
- AI property search assistant — clients tell the AI what they want (beds, budget, neighborhood, school district, commute time). It searches MLS, filters matches, and texts them a curated list. You only get involved when they're ready to tour.
- Instant lead follow-up — someone fills out a web form or calls at midnight about a listing. AI responds in under 60 seconds, qualifies them, and books a showing. First agent to respond wins 78% of the time.
- Automated showing coordinator — AI handles showing requests, checks your calendar, confirms times with buyers, and sends property info packs before each visit.
- Market analysis report bot — AI pulls comps, calculates price-per-sqft trends, and generates a PDF market report for any zip code in minutes. Use it for listing appointments to impress sellers.
- Deal pipeline tracker — tracks every active buyer and seller, where they are in the process, and what the next step is. AI nudges you when a lead goes cold.
- Off-market deal finder — scrapes public records for FSBOs, probate listings, tax delinquencies, and expired listings. Feeds you a daily list of motivated sellers before they hit the MLS.

PAIN POINTS TO HIT:
• "I lose online leads to faster agents — they submitted on Zillow, I called next morning, they already signed with someone."
• "I spend hours answering the same property questions from buyers who aren't serious yet."
• "I have no system to find off-market deals — I'm competing for the same MLS listings as everyone else."

OPENER: "Are you mostly working buyers, sellers, or both right now? I want to show you the tools that matter most for your workflow."

$2,000–$4,000 setup | $500–$750/mo
INDUSTRY: Real Estate | OWNER: {n}""",


    "events": lambda n, co: f"""Hi {n}, I'm reaching out from Janovum — we build AI automation for event and wedding businesses like {co}.

WHAT WE CAN BUILD FOR YOU:
- Instant inquiry responder — when someone fills out your contact form or DMs you, AI responds within 60 seconds with your packages, pricing, and availability. You only jump in when they're warm.
- Automated quote builder — client fills out an event details form, AI generates a custom quote PDF and emails it automatically. No more spending an hour writing proposals for tire-kickers.
- Client portal & timeline tracker — each client gets a link to their event timeline, checklist, and payment schedule. They can upload inspiration photos, mark tasks done, and see exactly what's next. Cuts 80% of "where are we?" texts.
- Vendor coordination system — AI sends job briefs to your vendors (florists, DJs, photographers), collects confirmations, and sends reminders 1 week and 24h before each event.
- Post-event review funnel — night of or morning after, AI texts clients asking for a Google review and a referral. Best time to catch them when they're emotional and happy.

PAIN POINTS TO HIT:
• "Inquiries come in at 11pm and I can't respond fast — they book someone who did."
• "I spend 2 hours writing proposals for people who ghost me."
• "Client management is all in my head and my DMs — one missed text and I look unprofessional."

OPENER: "How do most of your bookings come in — Instagram, referrals, Google, or your website?"

$1,500–$2,500 setup | $500/mo
INDUSTRY: Events/Wedding | OWNER: {n}""",


    "accounting": lambda n, co: f"""Hi {n}, I'm reaching out from Janovum — we build AI automation for accounting and tax firms like {co}.

WHAT WE CAN BUILD FOR YOU:
- Document collection bot — AI texts and emails clients a secure upload link and a checklist of what you need. Sends reminders every 3 days until everything is in. No more chasing people for W-2s in April.
- Client onboarding automation — new clients fill out a digital intake form. AI organizes their info, creates their folder, and sends a welcome sequence with deadlines and what to expect.
- Tax deadline reminder system — AI sends personalized reminders to every client before quarterly estimates, extension deadlines, and filing deadlines. You look proactive, they stay compliant.
- FAQ chatbot for your website — handles "Do you do S-corps?", "What's your pricing?", "Are you taking new clients?" 24/7. Filters leads before they reach your calendar.
- Referral request automation — after you file a return, AI sends a thank-you email and asks if they know anyone who needs a good accountant. Referrals on autopilot during tax season.

PAIN POINTS TO HIT:
• "I'm drowning in client follow-ups during tax season — everyone's late with documents."
• "I spend the first 2 weeks of April just chasing paperwork."
• "My referral pipeline is word of mouth only — no system."

OPENER: "How do you currently handle document collection from clients — email chains, a portal, or something else?"

$1,500–$2,000 setup | $500/mo
INDUSTRY: Accounting/Tax | OWNER: {n}""",


    "telecom": lambda n, co: f"""Hi {n}, I'm reaching out from Janovum — we build AI systems for telecom and IT service companies like {co}.

WHAT WE CAN BUILD FOR YOU:
- Service ticket triage bot — when a customer reports an issue, AI collects details, assigns priority, dispatches the right tech, and sends the customer an ETA. No more ticket chaos.
- Automated outage communications — when there's a service disruption, AI immediately texts all affected customers with status updates. Kills the flood of "is anyone else down?" calls.
- Equipment renewal tracker — AI monitors contract end dates for every customer's equipment/service plan and triggers a renewal outreach 90 days out. Never let a contract lapse silently.
- Tech dispatch optimizer — takes your open tickets and available techs, builds the most efficient dispatch schedule by location and skill set.
- Customer health scoring — AI tracks ticket frequency, payment history, and contract value per customer. Flags at-risk accounts before they churn.

PAIN POINTS TO HIT:
• "When there's an outage, our phone lines blow up — we can't handle the volume."
• "We have customers whose contracts auto-renewed at old rates because nobody caught it."
• "Dispatch is a mess — techs cross paths or drive past each other all day."

OPENER: "How many service tickets are you handling on a busy day right now?"

$2,000–$3,500 setup | $500–$750/mo
INDUSTRY: Telecom/IT Services | OWNER: {n}""",


    "marine": lambda n, co: f"""Hi {n}, I'm reaching out from Janovum — we build AI tools for marine and boat businesses like {co}.

WHAT WE CAN BUILD FOR YOU:
- Seasonal booking automation — AI handles slip rental requests, storage reservations, and service appointments 24/7. Maximizes your peak season without extra staff.
- Maintenance reminder system — tracks every vessel in your database and sends personalized service reminders: "Your winterization is coming up — want to lock in a date before we fill up?"
- Weather-triggered communication — when bad weather is forecasted, AI automatically texts boat owners with advisories and optional haul-out scheduling. Positions you as the expert they trust.
- Parts & inventory tracking — logs your most-used marine parts and alerts you when stock is low before busy season hits.
- Customer follow-up after service — 1 week after any repair, AI checks in to make sure everything is running well. Builds loyalty and catches warranty issues early.

PAIN POINTS TO HIT:
• "Peak season is insane — I can't answer every call and book every slip at the same time."
• "I have 100 past customers I've never reached back out to."
• "Winterization season catches me unprepared every year."

OPENER: "Is your business more storage and slips, or repairs and service? I want to build something that fits your model."

$1,500–$2,500 setup | $500/mo
INDUSTRY: Marine | OWNER: {n}""",


    "farm": lambda n, co: f"""Hi {n}, I'm reaching out from Janovum — we build AI systems for agricultural operations like {co}.

WHAT WE CAN BUILD FOR YOU:
- Wholesale buyer portal — restaurants, grocers, and distributors submit orders through a simple web form. AI confirms, schedules pickup, and sends invoices automatically.
- Market price alert system — AI monitors commodity prices for your crops and alerts you when a favorable selling window opens. Stop leaving money on the table.
- Harvest & delivery scheduler — coordinates harvest timing, truck availability, and buyer schedules so deliveries don't pile up or get missed.
- CSA / subscription management — if you do CSA boxes, AI handles signups, payments, delivery confirmations, and weekly "what's in your box" emails automatically.
- Equipment maintenance tracker — logs service schedules for tractors, irrigation, and equipment. Alerts before seasonal breakdowns happen.

PAIN POINTS TO HIT:
• "I'm out in the field all day and miss calls from buyers."
• "Coordinating delivery logistics is a mess across multiple buyers."
• "I don't have a system — it's all in my head and my phone."

OPENER: "Are you selling mostly direct to consumers, wholesale to restaurants, or both?"

$1,500–$2,500 setup | $500/mo
INDUSTRY: Agriculture/Farm | OWNER: {n}""",


    "signage": lambda n, co: f"""Hi {n}, I'm reaching out from Janovum — we build AI automation for sign and print businesses like {co}.

WHAT WE CAN BUILD FOR YOU:
- Instant quote system — customers submit their sign request online (size, material, quantity, deadline). AI generates a quote and sends it in minutes, 24/7. First to quote wins the job.
- Design approval workflow — AI sends customers a link to review proofs, leave comments, and click approve. No more email chains. Tracks revision history and timestamps approvals.
- Production tracker — each order has a status customers can check: "In design", "Approved", "In production", "Ready for pickup." Kills "is my order done?" calls.
- Order follow-up & reorder automation — 6 months after delivery, AI sends a check-in: "Need a refresh on your outdoor banners before season?" Brings repeat business without you thinking about it.
- Review request after pickup — AI texts a review request the day of pickup. Sign companies live and die by Google reviews for local search.

PAIN POINTS TO HIT:
• "Customers want quotes fast — if we take a day to respond, they've already gone somewhere else."
• "Design approvals go back and forth over email forever and delay production."
• "We never follow up with past customers for reorders."

OPENER: "What's your biggest order type right now — vehicle wraps, storefront signs, or event banners?"

$1,000–$2,000 setup | $500/mo
INDUSTRY: Signage/Print | OWNER: {n}""",


    "salon": lambda n, co: f"""Hi {n}, I'm reaching out from Janovum — we build AI booking and retention systems for salons and barbershops like {co}.

WHAT WE CAN BUILD FOR YOU:
- 24/7 AI booking system — clients text or DM to book. AI checks stylist availability, books the appointment, and sends a confirmation instantly. No more phone tag.
- No-show protection — 24h and 2h reminders via text. If they don't confirm, AI offers their slot to the waitlist automatically. Empty chairs cost you money.
- Waitlist filler — when a cancellation happens, AI immediately texts the next person on the waitlist. Chair gets filled in minutes.
- Client preference tracker — logs every client's preferred stylist, usual service, product allergies, and last visit. Staff knows everything before they sit down. Builds loyalty fast.
- Rebooking automation — 4–6 weeks after each visit, AI texts: "Hey, it's been a month since your last cut — want to grab a slot before the weekend fills up?" Keeps your regulars coming back on schedule.
- Review request system — after checkout, AI sends a review request. Salons with more Google reviews dominate local search and walk-in traffic.

PAIN POINTS TO HIT:
• "Stylists are doing hair and can't answer phones — we miss bookings."
• "No-shows are killing us — especially Saturdays."
• "We have regulars who just stop coming and we never know why or reach back out."

OPENER: "How do clients book right now — walk-in, phone, or do you have an app?"

$1,000–$1,500 setup | $500/mo
INDUSTRY: Salon/Barbershop | OWNER: {n}""",


    "vacation": lambda n, co: f"""Hi {n}, I'm reaching out from Janovum — we build AI automation for short-term rental and hospitality businesses like {co}.

WHAT WE CAN BUILD FOR YOU:
- Dynamic pricing engine — AI monitors competitor rates, local events, and occupancy trends, then adjusts your nightly rate automatically to maximize revenue. Most hosts leave 15–30% on the table with flat pricing.
- Guest communication automation — check-in instructions, door codes, house rules, mid-stay check-ins, checkout reminders, and local recommendations — all automated and personalized. Guests feel taken care of, you don't lift a finger.
- Cleaning crew coordinator — when a checkout is confirmed, AI automatically texts your cleaner with the checkout time, number of guests, and any special notes. No more manual coordination.
- Review generation system — 2 hours after checkout, AI sends a personalized message asking for a review. Properties with more reviews rank higher and book faster.
- Problem escalation filter — if a guest messages about an issue, AI handles the standard stuff (WiFi password, checkout time) and only escalates real problems to you. Cuts your message load by 60%.

PAIN POINTS TO HIT:
• "I'm manually answering the same guest questions over and over — WiFi, parking, checkout."
• "I have 3 properties and coordinating cleaners is a logistical nightmare."
• "My prices are the same every night — I know I'm losing money on weekends and events."

OPENER: "How many properties are you managing right now — and are you doing it solo or with a team?"

$1,500–$2,500 setup | $500/mo
INDUSTRY: Short-Term Rental/Hospitality | OWNER: {n}""",


    "storage": lambda n, co: f"""Hi {n}, I'm reaching out from Janovum — we build AI systems for self-storage businesses like {co}.

WHAT WE CAN BUILD FOR YOU:
- 24/7 unit availability bot — when someone calls or texts asking about units, AI answers instantly with available sizes, pricing, and move-in specials. Books their reservation on the spot. Storage shoppers call 3 places and rent from whoever answers.
- Automated rental agreement system — new tenant fills out a form, AI generates the lease, sends it for e-signature, and processes move-in confirmation. Zero paperwork for staff.
- Late payment reminder system — AI sends a text reminder 5 days before rent is due, a follow-up on the due date, and escalating reminders after. Reduces delinquencies without awkward calls.
- Move-out prediction & upsell — AI tracks tenant behavior (declining payment activity, shorter renewal patterns) and flags at-risk accounts so you can reach out and retain them.
- Referral program automation — after move-in, AI texts tenants: "Know anyone who needs storage? Send them our way and get $25 off your next month." Word-of-mouth, systematized.

PAIN POINTS TO HIT:
• "People shop for storage at 10pm when our office is closed — we lose them to facilities with online booking."
• "Chasing late payments is uncomfortable and time-consuming."
• "We have no follow-up system for people who called but didn't rent."

OPENER: "How many units are you running, and do you have a physical office on-site or is it fully unmanned?"

$1,000–$2,000 setup | $500/mo
INDUSTRY: Self-Storage | OWNER: {n}""",


    "staffing": lambda n, co: f"""Hi {n}, I'm reaching out from Janovum — we build AI tools for staffing and recruiting firms like {co}.

WHAT WE CAN BUILD FOR YOU:
- AI candidate screener — sends a text-based screening interview to every applicant. Asks your qualifying questions, scores their answers, and gives you a ranked shortlist. Screens 50 candidates in the time it takes you to call 5.
- Job alert system — when a new role opens, AI instantly texts your entire talent pool and matches it to candidates by skill and location. Best candidates get to clients faster.
- Client job order intake — clients submit new openings through a form. AI pulls the details, confirms requirements, and starts matching immediately. No missed orders.
- Candidate pipeline tracker — shows where every candidate is in the process (applied, screened, submitted, interviewing, placed). Sends nudges when stages stall.
- Placement follow-up — 30/60/90 days after a placement, AI checks in with both the client and the candidate. Catches problems early, builds retention, and creates upsell opportunities.

PAIN POINTS TO HIT:
• "We have 200 resumes in our inbox and no time to screen them all."
• "Good candidates ghost us because our follow-up is slow."
• "Clients call with urgent openings and we scramble to find matches manually."

OPENER: "What industries do you place in mostly, and are your clients looking for temp, perm, or both?"

$2,000–$3,500 setup | $500–$750/mo
INDUSTRY: Staffing/Recruiting | OWNER: {n}""",


    "tech": lambda n, co: f"""Hi {n}, I'm reaching out from Janovum — we build custom AI tools for tech and IT service businesses like {co}.

WHAT WE CAN BUILD FOR YOU:
- Client onboarding automation — new clients get a structured onboarding sequence: welcome email, setup checklist, kickoff call scheduler, and progress tracker. Zero manual coordination.
- Support ticket AI — first-line triage bot handles password resets, common issues, and FAQs automatically. Only escalates real problems to your team. Cuts ticket volume 40–60%.
- Contract renewal radar — AI tracks every client's contract end date and kicks off a renewal conversation 90 days out. No more last-minute scrambles or silent churns.
- Usage-based upsell triggers — if a client is consistently hitting their plan limits, AI flags them and generates a personalized upsell email. Revenue from existing clients, no new sales effort.
- Churn prediction dashboard — tracks engagement signals (login frequency, support tickets, response time) and scores each client on churn risk. Reach out before they cancel.

PAIN POINTS TO HIT:
• "Our support team spends half their day on tickets that could be self-served."
• "We lose clients at renewal because nobody reached out 90 days before."
• "We have no system to track who's happy vs. who's about to leave."

OPENER: "How many active clients are you managing right now, and what's your biggest customer success challenge?"

$2,000–$4,000 setup | $750/mo
INDUSTRY: Tech/IT Services | OWNER: {n}""",


    "insurance": lambda n, co: f"""Hi {n}, I'm reaching out from Janovum — we build AI automation for insurance agencies like {co}.

WHAT WE CAN BUILD FOR YOU:
- Instant quote intake bot — website visitors or callers answer a few questions via AI. It collects all the info you need to run a quote and sends it to your team organized and ready. No more incomplete intake forms.
- Policy renewal campaign — AI tracks every policy expiration date and reaches out 90/60/30 days before renewal with a personalized message. Clients stay, you look proactive.
- Cross-sell identifier — AI analyzes each client's current coverage and flags obvious gaps (no umbrella, no life, underinsured home). Sends personalized outreach at the right time.
- Claims follow-up assistant — after a client files a claim, AI checks in at key milestones and keeps them updated. Reduces calls to your office and builds trust during a stressful time.
- Referral system — after policy issuance or renewal, AI sends a referral request. Insurance is one of the highest-referral industries when you actually ask.

PAIN POINTS TO HIT:
• "Clients leave at renewal because a competitor quoted them and we weren't top of mind."
• "I have 500 clients and no system to cross-sell — I'm leaving money on every account."
• "Referral business is inconsistent because I only remember to ask sometimes."

OPENER: "What lines do you focus on — personal, commercial, or both? I want to show you what we'd build for your book of business."

$1,500–$2,500 setup | $500/mo
INDUSTRY: Insurance | OWNER: {n}""",


    "retail": lambda n, co: f"""Hi {n}, I'm reaching out from Janovum — we build AI systems for retail and product businesses like {co}.

WHAT WE CAN BUILD FOR YOU:
- Inventory demand forecasting — AI analyzes your sales history, seasonal trends, and current stock to predict what you'll need and when. Stop over-ordering slow movers and stocking out on top sellers.
- Abandoned cart recovery — for online stores, AI sends personalized follow-ups to customers who added to cart but didn't buy. Recovers 15–25% of abandoned revenue.
- Loyalty & reorder automation — AI tracks purchase frequency and sends personalized reorder reminders: "You usually grab more of X every 6 weeks — running low?" Increases repeat purchase rate.
- Supplier reorder automation — when a product hits your reorder threshold, AI drafts a purchase order and sends it to your supplier. No more emergency restocking.
- Review & UGC collection — after purchase, AI requests a review and optionally asks for a photo. More reviews = more trust = more sales.

PAIN POINTS TO HIT:
• "I order inventory based on gut feel and I'm always either overstocked or sold out."
• "Online, people add to cart and disappear — I have no follow-up."
• "Repeat customers come back randomly — I have no way to encourage it."

OPENER: "Is your business mostly in-store, online, or both?"

$1,500–$2,500 setup | $500/mo
INDUSTRY: Retail | OWNER: {n}""",


    "gym": lambda n, co: f"""Hi {n}, I'm reaching out from Janovum — we build AI automation for gyms and fitness studios like {co}.

WHAT WE CAN BUILD FOR YOU:
- Lead nurture system — when someone inquires about membership, AI sends a follow-up sequence: "Come in for a free day pass", then testimonials, then a limited-time offer. Converts more inquiries to members.
- Member retention tracker — AI monitors attendance frequency and flags members who are showing up less. Triggers a check-in text: "Haven't seen you in a while — everything okay?" Catches churners before they cancel.
- Class booking automation — members text or use a link to book classes, get reminders before each one, and get on a waitlist when full. Instructor gets a headcount automatically.
- Re-engagement campaign — for former members, AI sends a "we miss you" campaign with a win-back offer. Most gyms never reach back out and leave this revenue on the table.
- Personal training upsell — after a member's first 30 days, AI sends a personalized message about personal training. Converts members to higher-LTV clients.

PAIN POINTS TO HIT:
• "Members stop coming and then cancel — by the time we notice, it's too late."
• "We get a lot of free trial signups but only convert about 30% — we don't follow up well."
• "We have 200 cancelled members we've never tried to win back."

OPENER: "What's your current monthly churn rate? That's usually the first thing we fix."

$1,500–$2,000 setup | $500/mo
INDUSTRY: Gym/Fitness | OWNER: {n}""",


    "childcare": lambda n, co: f"""Hi {n}, I'm reaching out from Janovum — we build AI tools for childcare and education businesses like {co}.

WHAT WE CAN BUILD FOR YOU:
- Enrollment inquiry automation — when a parent inquires about enrollment, AI responds instantly with program info, availability, and schedules a tour. No lead falls through the cracks.
- Daily parent communication — AI sends parents a daily text update: attendance confirmation, any notes from teachers, and a photo (if you share them). Keeps parents engaged and reduces "how was my kid's day?" calls.
- Tuition reminder & payment tracking — AI sends payment reminders before due dates, tracks who's paid, and sends escalating reminders for late accounts. Takes the awkward conversation off your staff.
- Staff scheduling assistant — AI manages shift coverage requests, finds available staff for open slots, and sends schedule reminders. Reduces no-call no-shows.
- Waitlist management — AI maintains your waitlist, notifies families when a spot opens, and gives them a deadline to respond. No more manually tracking who's next.

PAIN POINTS TO HIT:
• "We have a waitlist but no system to manage it — families get frustrated when we can't tell them where they stand."
• "Chasing tuition payments is uncomfortable and time-consuming for our director."
• "Parents feel out of the loop and that increases anxiety and drop-outs."

OPENER: "How many kids are you currently enrolled, and what ages do you serve?"

$1,500–$2,000 setup | $500/mo
INDUSTRY: Childcare/Education | OWNER: {n}""",


    "general": lambda n, co: f"""Hi {n}, I'm reaching out from Janovum — we build custom AI tools and automation systems for businesses like {co}.

WHAT WE DO:
We don't sell a generic software subscription. We sit down with you, figure out where your business is losing time or money, and build something custom that fixes it.

Common things we build:
- AI that answers calls/texts 24/7 and captures every lead (no missed calls = no missed revenue)
- Automated follow-up sequences that chase leads so you don't have to
- Scheduling and booking systems that run themselves
- Customer reactivation campaigns that bring back past clients
- Dashboards that show you what's working in your business in real time
- Custom tools specific to your industry — we build what you actually need

THE CORE PITCH:
Most small businesses lose 30–40% of their revenue to three things: missed calls, slow follow-ups, and no repeat-customer strategy. We fix all three with AI, typically in under 2 weeks, with no tech knowledge required on your end.

$1,000–$3,000 setup depending on what we build | $500/mo
INDUSTRY: General Business | OWNER: {n}

OPENER: "What's the biggest time-waster or revenue leak in your business right now? That's usually where we start." """,
}


def make_note(company, owner_name):
    cat = categorize(company, owner_name)
    first = get_first_name(owner_name)
    template = PITCH.get(cat, PITCH["general"])
    co_display = company.title() if company else "your business"
    return template(first, co_display)


def run():
    print("Fetching leads from server...")
    r = requests.get(API, timeout=15)
    leads = r.json()
    print(f"Got {len(leads)} leads")

    updated = 0
    failed = 0

    for i, lead in enumerate(leads):
        lead_id = lead.get("id")
        company = lead.get("company", "")
        name = lead.get("name", "")

        note = make_note(company, name)

        try:
            resp = requests.post(
                f"{API}/{lead_id}",
                json={"notes": note},
                timeout=10
            )
            if resp.status_code in (200, 201):
                updated += 1
                cat = categorize(company, name)
                print(f"  [{i+1}] OK ({cat}): {company}")
            else:
                failed += 1
                print(f"  [{i+1}] FAIL {resp.status_code}: {company} — {resp.text[:80]}")
        except Exception as e:
            failed += 1
            print(f"  [{i+1}] ERROR: {company} — {e}")

        if (i+1) % 20 == 0:
            time.sleep(0.3)

    print(f"\nDone! Updated: {updated} | Failed: {failed}")

if __name__ == "__main__":
    run()
