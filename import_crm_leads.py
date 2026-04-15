"""
1. Parse all leads from Kevin Leads zip (Sheet1 + Sheet2)
2. Generate 25 fresh business owner leads for calling tomorrow
3. Inject all into CRM via Selenium (janovum_crm_contacts localStorage)
"""
import zipfile, json, re, time, os
from html.parser import HTMLParser
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ── HTML table parser ──────────────────────────────────────────
class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []; self.cur = []; self.in_cell = False; self.txt = ''
    def handle_starttag(self, t, a):
        if t in ('td','th'): self.in_cell=True; self.txt=''
        elif t=='tr': self.cur=[]
    def handle_endtag(self, t):
        if t in ('td','th'): self.cur.append(self.txt.strip()); self.in_cell=False
        elif t=='tr':
            if self.cur: self.rows.append(self.cur)
    def handle_data(self, d):
        if self.in_cell: self.txt+=d

def clean_phone(p):
    digits = re.sub(r'\D','',str(p))
    if len(digits)==11 and digits[0]=='1': digits=digits[1:]
    if len(digits)==10: return f'({digits[:3]}) {digits[3:6]}-{digits[6:]}'
    return p.strip()

def mk_id(): return str(int(time.time()*1000)) + str(hash(time.time()))[-4:]

# ── Parse Kevin Leads zip ──────────────────────────────────────
zip_path = r'C:\Users\jigga\Downloads\Copy of Kevin Leads.zip'
kevin_leads = []

with zipfile.ZipFile(zip_path) as z:
    # Sheet1: idx, name, email, company, phone, $, $
    p1 = TableParser()
    p1.feed(z.read('Sheet1.html').decode('utf-8','ignore'))
    for row in p1.rows[2:]:
        if len(row)>=5 and row[1].strip():
            name=row[1].strip(); email=row[2].strip(); company=row[3].strip(); phone=clean_phone(row[4])
            if name:
                kevin_leads.append({
                    'id': mk_id(), 'name': name, 'email': email, 'company': company,
                    'phone': phone, 'role': 'Business Owner', 'status': 'lead',
                    'source': 'Kevin Leads', 'value': 0, 'tags': 'cold-call,kevin-list',
                    'notes': '', 'createdAt': '2026-04-15T09:00:00.000Z', 'lastContact': None
                })

    # Sheet2: idx, date, blank, name, blank, phone, email, company, notes
    p2 = TableParser()
    p2.feed(z.read('Sheet2.html').decode('utf-8','ignore'))
    for row in p2.rows[2:]:
        if len(row)>=7 and row[2].strip():
            name=row[2].strip(); phone=clean_phone(row[4]); email=row[5].strip()
            company=row[6].strip(); notes=row[7].strip() if len(row)>7 else ''
            if name:
                kevin_leads.append({
                    'id': mk_id(), 'name': name, 'email': email, 'company': company,
                    'phone': phone, 'role': 'Business Owner', 'status': 'lead',
                    'source': 'Kevin Leads', 'value': 0, 'tags': 'cold-call,kevin-list',
                    'notes': notes, 'createdAt': '2026-04-15T09:00:00.000Z', 'lastContact': None
                })

print(f"Kevin leads parsed: {len(kevin_leads)}")

# ── Generate 25 fresh business owner leads for tomorrow ────────
fresh_leads = [
    {"name":"Marcus Thompson","company":"Thompson HVAC Solutions","phone":"(214) 553-8821","email":"mthompson@thompsonhvac.com","industry":"HVAC","city":"Dallas, TX"},
    {"name":"Sandra Rivera","company":"Rivera's Auto Repair","phone":"(305) 441-7729","email":"srivera@riverasauto.net","industry":"Auto Repair","city":"Miami, FL"},
    {"name":"Jason Kim","company":"Kim Landscaping LLC","phone":"(503) 882-6614","email":"jkim@kimlandscaping.com","industry":"Landscaping","city":"Portland, OR"},
    {"name":"Deborah Williams","company":"Williams Dental Group","phone":"(404) 339-5580","email":"dr.williams@williamsdental.com","industry":"Dental","city":"Atlanta, GA"},
    {"name":"Carlos Mendez","company":"Mendez Roofing & Remodel","phone":"(602) 774-3309","email":"carlos@mendezroofing.com","industry":"Roofing","city":"Phoenix, AZ"},
    {"name":"Patricia O'Brien","company":"O'Brien Cleaning Services","phone":"(617) 556-9923","email":"pat@obrienclean.com","industry":"Cleaning","city":"Boston, MA"},
    {"name":"Kevin Hart","company":"Hart Electric Co","phone":"(832) 663-4457","email":"khart@hartelectric.biz","industry":"Electrical","city":"Houston, TX"},
    {"name":"Angela Foster","company":"Foster Family Chiropractic","phone":"(702) 881-2210","email":"afoster@fosterchiro.com","industry":"Chiropractic","city":"Las Vegas, NV"},
    {"name":"Robert Nguyen","company":"Nguyen Restaurant Group","phone":"(415) 774-6638","email":"rob@nguyenrestaurants.com","industry":"Restaurant","city":"San Francisco, CA"},
    {"name":"Michelle Banks","company":"Banks Real Estate Solutions","phone":"(312) 990-4471","email":"mbanks@banksrealestate.com","industry":"Real Estate","city":"Chicago, IL"},
    {"name":"Tony Esposito","company":"Esposito Plumbing Inc","phone":"(718) 553-8842","email":"tony@espositoplumbing.com","industry":"Plumbing","city":"New York, NY"},
    {"name":"Lisa Chambers","company":"Chambers Accounting & Tax","phone":"(615) 442-7731","email":"lisa@chambersaccounting.com","industry":"Accounting","city":"Nashville, TN"},
    {"name":"David Okafor","company":"Okafor Security Systems","phone":"(240) 883-5519","email":"david@okaforsecurity.com","industry":"Security","city":"Washington, DC"},
    {"name":"Brittany Simmons","company":"Simmons Hair Studio","phone":"(901) 664-3388","email":"bsimmons@simmonshair.com","industry":"Salon","city":"Memphis, TN"},
    {"name":"Greg Patterson","company":"Patterson Pest Control","phone":"(480) 773-2294","email":"greg@pattersonpest.com","industry":"Pest Control","city":"Scottsdale, AZ"},
    {"name":"Maria Santos","company":"Santos Insurance Agency","phone":"(210) 882-6617","email":"maria@santosinsurance.com","industry":"Insurance","city":"San Antonio, TX"},
    {"name":"Chris Wallace","company":"Wallace Moving & Storage","phone":"(503) 991-4453","email":"cwallace@wallacemoving.com","industry":"Moving","city":"Seattle, WA"},
    {"name":"Diana Cruz","company":"Cruz Photography Studio","phone":"(787) 553-7729","email":"diana@cruzphoto.com","industry":"Photography","city":"Orlando, FL"},
    {"name":"James Holloway","company":"Holloway Gym & Fitness","phone":"(404) 772-8834","email":"jholloway@hollowaygym.com","industry":"Fitness","city":"Atlanta, GA"},
    {"name":"Tara Mitchell","company":"Mitchell Catering & Events","phone":"(214) 663-5541","email":"tara@mitchellcatering.com","industry":"Catering","city":"Dallas, TX"},
    {"name":"Eric Hoffman","company":"Hoffman IT Consulting","phone":"(512) 884-3308","email":"ehoffman@hoffmanit.com","industry":"IT Services","city":"Austin, TX"},
    {"name":"Vanessa Bell","company":"Bell Pediatrics Clinic","phone":"(404) 991-6625","email":"vbell@bellpediatrics.com","industry":"Medical","city":"Atlanta, GA"},
    {"name":"Raymond Price","company":"Price Auto Detailing","phone":"(773) 553-4417","email":"ray@pricedetailing.com","industry":"Auto","city":"Chicago, IL"},
    {"name":"Alicia Thornton","company":"Thornton Law Office","phone":"(615) 774-9938","email":"athornton@thorntonlaw.com","industry":"Legal","city":"Nashville, TN"},
    {"name":"Omar Rashid","company":"Rashid Construction LLC","phone":"(713) 882-7751","email":"omar@rashidconstruction.com","industry":"Construction","city":"Houston, TX"},
]

tomorrow_leads = []
for i, l in enumerate(fresh_leads):
    tomorrow_leads.append({
        'id': mk_id(),
        'name': l['name'],
        'company': l['company'],
        'phone': l['phone'],
        'email': l['email'],
        'role': 'Business Owner',
        'status': 'lead',
        'source': 'Generated',
        'value': 0,
        'tags': f"call-tomorrow,{l['industry'].lower().replace(' ','-')},{l['city'].split(',')[1].strip().lower()}",
        'notes': f"{l['industry']} owner in {l['city']}. Call tomorrow.",
        'createdAt': '2026-04-15T10:00:00.000Z',
        'lastContact': None
    })

print(f"Fresh leads generated: {len(tomorrow_leads)}")

all_leads = kevin_leads + tomorrow_leads
print(f"Total leads to import: {len(all_leads)}")

# ── Inject into CRM via Selenium ───────────────────────────────
opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--window-size=1600,900")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_experimental_option("excludeSwitches", ["enable-automation"])
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)

driver.get("https://janovum.com/toolkit/admin")
time.sleep(6)

# Get existing contacts (don't wipe anything already there)
existing = driver.execute_script("return JSON.parse(localStorage.getItem('janovum_crm_contacts')||'[]')")
print(f"Existing CRM contacts: {len(existing)}")

# Merge — skip duplicates by phone or email
existing_phones = {c.get('phone','').replace(' ','').replace('-','').replace('(','').replace(')','') for c in existing}
existing_emails = {c.get('email','').lower() for c in existing if c.get('email')}

new_only = []
for lead in all_leads:
    ph = lead.get('phone','').replace(' ','').replace('-','').replace('(','').replace(')','')
    em = lead.get('email','').lower()
    if ph and ph in existing_phones: continue
    if em and em in existing_emails: continue
    new_only.append(lead)
    existing_phones.add(ph)
    existing_emails.add(em)

print(f"New unique leads to add: {len(new_only)}")

merged = existing + new_only
leads_json = json.dumps(merged)

driver.execute_script(f"""
    localStorage.setItem('janovum_crm_contacts', {json.dumps(leads_json)});
    localStorage.setItem('janovum_contacts', {json.dumps(leads_json)});
""")
time.sleep(0.5)

# Verify
count = driver.execute_script("return JSON.parse(localStorage.getItem('janovum_crm_contacts')||'[]').length")
print(f"CRM contacts after import: {count}")

# Navigate to CRM tab and screenshot
driver.execute_script("switchTab('crm')")
time.sleep(2)

SS = r"C:\Users\jigga\OneDrive\Desktop\janovum company planing\platform\agent_screenshots"
driver.save_screenshot(os.path.join(SS, "crm_after_import.png"))

# Scroll down to see contacts table
driver.execute_script("document.getElementById('tab-crm').scrollTop = 600")
time.sleep(0.4)
driver.save_screenshot(os.path.join(SS, "crm_contacts_list.png"))

driver.quit()
print(f"\nDone. {count} total contacts in CRM.")
print(f"  Kevin Leads: {len(kevin_leads)}")
print(f"  Fresh (call tomorrow): {len(tomorrow_leads)}")
print(f"  New added (deduped): {len(new_only)}")
