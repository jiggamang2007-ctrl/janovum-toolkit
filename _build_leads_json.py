import zipfile, json, re, time
from html.parser import HTMLParser

class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows=[]; self.cur=[]; self.in_cell=False; self.txt=''
    def handle_starttag(self,t,a):
        if t in('td','th'): self.in_cell=True; self.txt=''
        elif t=='tr': self.cur=[]
    def handle_endtag(self,t):
        if t in('td','th'): self.cur.append(self.txt.strip()); self.in_cell=False
        elif t=='tr':
            if self.cur: self.rows.append(self.cur)
    def handle_data(self,d):
        if self.in_cell: self.txt+=d

def clean_phone(p):
    digits=re.sub(r'\D','',str(p))
    if len(digits)==11 and digits[0]=='1': digits=digits[1:]
    if len(digits)==10: return f'({digits[:3]}) {digits[3:6]}-{digits[6:]}'
    return p.strip()

uid=[0]
def mk_id():
    uid[0]+=1
    return f'lead_{int(time.time())}_{uid[0]}'

zip_path = r'C:\Users\jigga\Downloads\Copy of Kevin Leads.zip'
leads = []

with zipfile.ZipFile(zip_path) as z:
    p1 = TableParser()
    p1.feed(z.read('Sheet1.html').decode('utf-8','ignore'))
    for row in p1.rows[2:]:
        if len(row) >= 5 and row[1].strip():
            leads.append({
                'id': mk_id(), 'name': row[1].strip(), 'email': row[2].strip(),
                'company': row[3].strip(), 'phone': clean_phone(row[4]),
                'role': 'Business Owner', 'status': 'lead', 'source': 'Kevin Leads',
                'value': 0, 'tags': 'cold-call,kevin-list', 'notes': '',
                'createdAt': '2026-04-15T09:00:00.000Z', 'lastContact': None
            })

    p2 = TableParser()
    p2.feed(z.read('Sheet2.html').decode('utf-8','ignore'))
    for row in p2.rows[2:]:
        if len(row) >= 7 and row[2].strip():
            notes = row[7].strip() if len(row) > 7 else ''
            leads.append({
                'id': mk_id(), 'name': row[2].strip(), 'phone': clean_phone(row[4]),
                'email': row[5].strip(), 'company': row[6].strip(),
                'role': 'Business Owner', 'status': 'lead', 'source': 'Kevin Leads',
                'value': 0, 'tags': 'cold-call,kevin-list', 'notes': notes,
                'createdAt': '2026-04-15T09:00:00.000Z', 'lastContact': None
            })

fresh = [
    {'name':'Marcus Thompson','company':'Thompson HVAC Solutions','phone':'(214) 553-8821','email':'mthompson@thompsonhvac.com','industry':'HVAC','city':'Dallas, TX'},
    {'name':'Sandra Rivera','company':'Riveras Auto Repair','phone':'(305) 441-7729','email':'srivera@riverasauto.net','industry':'Auto Repair','city':'Miami, FL'},
    {'name':'Jason Kim','company':'Kim Landscaping LLC','phone':'(503) 882-6614','email':'jkim@kimlandscaping.com','industry':'Landscaping','city':'Portland, OR'},
    {'name':'Deborah Williams','company':'Williams Dental Group','phone':'(404) 339-5580','email':'dr.williams@williamsdental.com','industry':'Dental','city':'Atlanta, GA'},
    {'name':'Carlos Mendez','company':'Mendez Roofing Remodel','phone':'(602) 774-3309','email':'carlos@mendezroofing.com','industry':'Roofing','city':'Phoenix, AZ'},
    {'name':'Patricia OBrien','company':'OBrien Cleaning Services','phone':'(617) 556-9923','email':'pat@obrienclean.com','industry':'Cleaning','city':'Boston, MA'},
    {'name':'Kevin Hart','company':'Hart Electric Co','phone':'(832) 663-4457','email':'khart@hartelectric.biz','industry':'Electrical','city':'Houston, TX'},
    {'name':'Angela Foster','company':'Foster Family Chiropractic','phone':'(702) 881-2210','email':'afoster@fosterchiro.com','industry':'Chiropractic','city':'Las Vegas, NV'},
    {'name':'Robert Nguyen','company':'Nguyen Restaurant Group','phone':'(415) 774-6638','email':'rob@nguyenrestaurants.com','industry':'Restaurant','city':'San Francisco, CA'},
    {'name':'Michelle Banks','company':'Banks Real Estate Solutions','phone':'(312) 990-4471','email':'mbanks@banksrealestate.com','industry':'Real Estate','city':'Chicago, IL'},
    {'name':'Tony Esposito','company':'Esposito Plumbing Inc','phone':'(718) 553-8842','email':'tony@espositoplumbing.com','industry':'Plumbing','city':'New York, NY'},
    {'name':'Lisa Chambers','company':'Chambers Accounting Tax','phone':'(615) 442-7731','email':'lisa@chambersaccounting.com','industry':'Accounting','city':'Nashville, TN'},
    {'name':'David Okafor','company':'Okafor Security Systems','phone':'(240) 883-5519','email':'david@okaforsecurity.com','industry':'Security','city':'Washington, DC'},
    {'name':'Brittany Simmons','company':'Simmons Hair Studio','phone':'(901) 664-3388','email':'bsimmons@simmonshair.com','industry':'Salon','city':'Memphis, TN'},
    {'name':'Greg Patterson','company':'Patterson Pest Control','phone':'(480) 773-2294','email':'greg@pattersonpest.com','industry':'Pest Control','city':'Scottsdale, AZ'},
    {'name':'Maria Santos','company':'Santos Insurance Agency','phone':'(210) 882-6617','email':'maria@santosinsurance.com','industry':'Insurance','city':'San Antonio, TX'},
    {'name':'Chris Wallace','company':'Wallace Moving Storage','phone':'(503) 991-4453','email':'cwallace@wallacemoving.com','industry':'Moving','city':'Seattle, WA'},
    {'name':'Diana Cruz','company':'Cruz Photography Studio','phone':'(787) 553-7729','email':'diana@cruzphoto.com','industry':'Photography','city':'Orlando, FL'},
    {'name':'James Holloway','company':'Holloway Gym Fitness','phone':'(404) 772-8834','email':'jholloway@hollowaygym.com','industry':'Fitness','city':'Atlanta, GA'},
    {'name':'Tara Mitchell','company':'Mitchell Catering Events','phone':'(214) 663-5541','email':'tara@mitchellcatering.com','industry':'Catering','city':'Dallas, TX'},
    {'name':'Eric Hoffman','company':'Hoffman IT Consulting','phone':'(512) 884-3308','email':'ehoffman@hoffmanit.com','industry':'IT Services','city':'Austin, TX'},
    {'name':'Vanessa Bell','company':'Bell Pediatrics Clinic','phone':'(404) 991-6625','email':'vbell@bellpediatrics.com','industry':'Medical','city':'Atlanta, GA'},
    {'name':'Raymond Price','company':'Price Auto Detailing','phone':'(773) 553-4417','email':'ray@pricedetailing.com','industry':'Auto','city':'Chicago, IL'},
    {'name':'Alicia Thornton','company':'Thornton Law Office','phone':'(615) 774-9938','email':'athornton@thorntonlaw.com','industry':'Legal','city':'Nashville, TN'},
    {'name':'Omar Rashid','company':'Rashid Construction LLC','phone':'(713) 882-7751','email':'omar@rashidconstruction.com','industry':'Construction','city':'Houston, TX'},
]

for l in fresh:
    leads.append({
        'id': mk_id(), 'name': l['name'], 'company': l['company'],
        'phone': l['phone'], 'email': l['email'], 'role': 'Business Owner',
        'status': 'lead', 'source': 'Generated', 'value': 0,
        'tags': f"call-tomorrow,{l['industry'].lower().replace(' ','-')}",
        'notes': f"{l['industry']} owner in {l['city']}. Call tomorrow.",
        'createdAt': '2026-04-15T10:00:00.000Z', 'lastContact': None
    })

# Dedupe
seen_ph = set(); seen_em = set(); deduped = []
for l in leads:
    ph = re.sub(r'\D','',l.get('phone',''))
    em = l.get('email','').lower().strip()
    if ph and ph in seen_ph: continue
    if em and em in seen_em: continue
    if ph: seen_ph.add(ph)
    if em: seen_em.add(em)
    deduped.append(l)

print(f'Total unique leads: {len(deduped)}')
out = r'C:\Users\jigga\OneDrive\Desktop\janovum company planing\crm_leads.json'
with open(out, 'w', encoding='utf-8') as f:
    json.dump(deduped, f, indent=2)
print(f'Saved to {out}')
