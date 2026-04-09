"""
Contact Form Blitz - Submit contact forms on local Miami business websites
Uses Selenium to find and fill out contact/inquiry forms automatically
"""
import time, json, random, sys, os
from datetime import datetime

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("Installing selenium...")
    os.system("pip install selenium webdriver-manager")
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager

# Businesses with known contact pages to hit
targets = [
    # Dental offices - high value targets
    {"biz": "Dr. G Dental Studio", "url": "https://drgdentalstudio.com", "type": "dentist"},
    {"biz": "SONRIE Dental Studio", "url": "https://sonriedentalstudio.com", "type": "dentist"},
    {"biz": "Miami Beach Dental Solutions", "url": "https://miamibeachds.com", "type": "dentist"},
    {"biz": "Gables Dental Care", "url": "https://gablesdentalcare.com", "type": "dentist"},
    {"biz": "Florida Dental Group", "url": "https://floridadentalgroup.com", "type": "dentist"},
    {"biz": "Dental Total", "url": "https://dentaltotal.com", "type": "dentist"},
    {"biz": "Garcia Mayoral Dentistry", "url": "https://garciamayoraldentistry.com", "type": "dentist"},
    # Med spas
    {"biz": "Lux MedSpa Brickell", "url": "https://luxmedspabrickell.com", "type": "med spa"},
    {"biz": "AestheteMed", "url": "https://aesthetemed.com", "type": "med spa"},
    {"biz": "Prestige Plastic Surgery", "url": "https://prestigeplasticsurgery.com", "type": "plastic surgery"},
    {"biz": "Cosmetic Laser Professionals", "url": "https://clpmedspa.com", "type": "med spa"},
    # Vets
    {"biz": "West Kendall Animal Hospital", "url": "https://westkendallvet.com", "type": "vet"},
    {"biz": "Sabal Chase Animal Clinic", "url": "https://scacvet.com", "type": "vet"},
    {"biz": "The Dog From Ipanema", "url": "https://thedogfromipanema.com", "type": "pet groomer"},
    # Home services
    {"biz": "Coral Gables Plumbing", "url": "https://coralgablesplumbing.com", "type": "plumbing"},
    {"biz": "Gold Star Roofing", "url": "https://goldstarroofing.us", "type": "roofing"},
    {"biz": "Elekron Electric", "url": "https://elekronelectric.com", "type": "electrician"},
    {"biz": "Miami Power Company", "url": "https://miamipowercompany.com", "type": "electrician"},
    {"biz": "Emergency AC Corp", "url": "https://emergencyaccorp.com", "type": "HVAC"},
    # Moving
    {"biz": "The Miami Movers", "url": "https://themiamimovers.com", "type": "moving"},
    {"biz": "Miami Movers for Less", "url": "https://miamimoversforless.com", "type": "moving"},
    {"biz": "Royal Movers Inc", "url": "https://royalmoversinc.com", "type": "moving"},
    # Property management
    {"biz": "JMK Property Management", "url": "https://jmkpropertymanagement.com", "type": "property mgmt"},
    {"biz": "Rovira Property Management", "url": "https://rovirapm.com", "type": "property mgmt"},
    {"biz": "Florida Management Group", "url": "https://floridamanagement.net", "type": "property mgmt"},
    # Auto
    {"biz": "Doral Elite Collision", "url": "https://doralelite.com", "type": "auto body"},
    {"biz": "Auto Body Lab", "url": "https://autobodylab.com", "type": "auto body"},
    {"biz": "Hialeah Auto Care", "url": "https://hialeahautocare.com", "type": "auto repair"},
    # Insurance / accounting
    {"biz": "Butler Buckley & Deets Insurance", "url": "https://bbdins.com", "type": "insurance"},
    {"biz": "Ivy Accounting", "url": "https://ivy-cpa.com", "type": "accounting"},
    # Restaurants
    {"biz": "La Mesa Miami", "url": "https://lamesamiami.com", "type": "restaurant"},
    {"biz": "MIKA Restaurant", "url": "https://mikacoralgables.com", "type": "restaurant"},
    {"biz": "Mamey Miami", "url": "https://mameymiami.com", "type": "restaurant"},
    # Fitness
    {"biz": "Libre Aerial Fitness", "url": "https://libreaf.com", "type": "fitness"},
    {"biz": "Core Fitness Miami", "url": "https://corefitnessmiami.com", "type": "fitness"},
    # Medical
    {"biz": "Miami Dermatology & Laser", "url": "https://miamidermlaser.com", "type": "dermatology"},
    {"biz": "Advance Therapy Center", "url": "https://advancetherapycenter.com", "type": "physical therapy"},
    {"biz": "IPT Miami", "url": "https://iptmiami.com", "type": "physical therapy"},
    {"biz": "Family Medical Group", "url": "https://thefamilymedgroup.com", "type": "medical"},
]

def get_message(biz, btype):
    ideas = {
        "dentist": "answer patient calls 24/7, book appointments, send reminders, and reduce no-shows",
        "med spa": "handle consultation requests, book treatments, and follow up with clients automatically",
        "plastic surgery": "handle consultation requests 24/7, book procedures, and follow up on leads",
        "vet": "answer calls, book appointments, send vaccination reminders, and handle after-hours calls",
        "pet groomer": "book grooming appointments, send reminders, and follow up for regular schedules",
        "plumbing": "capture every emergency call 24/7, schedule appointments, and send ETAs",
        "roofing": "answer estimate calls, schedule inspections, and follow up on pending quotes",
        "electrician": "capture every service call, schedule appointments, and follow up automatically",
        "HVAC": "capture every emergency call 24/7, schedule service, and follow up for maintenance plans",
        "moving": "answer quote requests day or night, schedule estimates, and book moves automatically",
        "property mgmt": "handle tenant calls 24/7, manage maintenance requests, and schedule showings",
        "auto body": "answer estimate calls, schedule drop-offs, and send repair status updates",
        "auto repair": "answer every service call, schedule appointments, and follow up when jobs are done",
        "insurance": "handle quote requests 24/7, schedule consultations, and follow up on pending policies",
        "accounting": "handle client calls, schedule consultations, and send tax deadline reminders",
        "restaurant": "handle reservation calls, answer menu questions, and manage waitlists",
        "fitness": "handle class bookings, answer membership questions, and follow up with trial members",
        "dermatology": "answer patient calls 24/7, book consultations, and send appointment reminders",
        "physical therapy": "answer patient calls, book sessions, send reminders, and reduce no-shows",
        "medical": "answer patient calls 24/7, schedule appointments, and handle after-hours calls",
    }
    idea = ideas.get(btype, "answer calls 24/7, book appointments, and handle customer questions")

    return f"Hi, my name is Jaden Gonzalez and I'm the founder of Janovum, a Miami-based AI automation company. I came across {biz} and wanted to reach out because we build AI receptionists that can {idea} -- all automatically, 24/7. Our clients are saving 20+ hours a week and never miss a call. I'd love to show you a quick 10-minute demo. You can reach me at janovumllc@gmail.com or check us out at janovum.com. Thanks!"

# Setup Chrome
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
driver.set_page_load_timeout(15)

results = {"submitted": [], "no_form": [], "failed": [], "phone_numbers": []}

print("=" * 60)
print("  CONTACT FORM BLITZ + PHONE NUMBER SCRAPE")
print("=" * 60)
sys.stdout.flush()

for i, target in enumerate(targets):
    biz = target["biz"]
    base_url = target["url"]
    btype = target["type"]
    message = get_message(biz, btype)

    print(f"\n[{i+1}/{len(targets)}] {biz} ({base_url})")
    sys.stdout.flush()

    # Try contact page URLs
    contact_urls = [
        base_url + "/contact",
        base_url + "/contact-us",
        base_url + "/contact.html",
        base_url + "/get-in-touch",
        base_url,
    ]

    form_found = False
    phone_found = None

    for url in contact_urls:
        try:
            driver.get(url)
            time.sleep(3)

            # Scrape phone numbers from the page
            page_text = driver.page_source
            import re
            phones = re.findall(r'(?:tel:|href="tel:)([^"<>\s]+)', page_text)
            if not phones:
                phones = re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', page_text)
            if phones:
                phone = phones[0].replace('tel:', '').strip()
                if len(phone) >= 10 and phone != phone_found:
                    phone_found = phone
                    print(f"  PHONE: {phone}")
                    sys.stdout.flush()
                    results["phone_numbers"].append({"biz": biz, "phone": phone, "type": btype, "url": base_url})

            # Look for contact forms
            forms = driver.find_elements(By.TAG_NAME, "form")
            if not forms:
                # Try iframes (some use embedded forms)
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes[:3]:
                    try:
                        driver.switch_to.frame(iframe)
                        forms = driver.find_elements(By.TAG_NAME, "form")
                        if forms:
                            break
                        driver.switch_to.default_content()
                    except:
                        driver.switch_to.default_content()

            if not forms:
                continue

            for form in forms:
                try:
                    inputs = form.find_elements(By.CSS_SELECTOR, "input, textarea, select")
                    if len(inputs) < 2:
                        continue

                    # Map fields
                    filled = 0
                    for inp in inputs:
                        inp_type = (inp.get_attribute("type") or "text").lower()
                        inp_name = (inp.get_attribute("name") or "").lower()
                        inp_id = (inp.get_attribute("id") or "").lower()
                        inp_placeholder = (inp.get_attribute("placeholder") or "").lower()
                        tag = inp.tag_name.lower()

                        all_attrs = f"{inp_name} {inp_id} {inp_placeholder}"

                        if inp_type in ("hidden", "submit", "button", "checkbox", "radio", "file"):
                            continue

                        if tag == "textarea" or "message" in all_attrs or "comment" in all_attrs or "inquiry" in all_attrs:
                            inp.clear()
                            inp.send_keys(message)
                            filled += 1
                        elif "name" in all_attrs and "last" not in all_attrs and "user" not in all_attrs:
                            inp.clear()
                            inp.send_keys("Jaden Gonzalez")
                            filled += 1
                        elif "last" in all_attrs and "name" in all_attrs:
                            inp.clear()
                            inp.send_keys("Gonzalez")
                            filled += 1
                        elif "first" in all_attrs and "name" in all_attrs:
                            inp.clear()
                            inp.send_keys("Jaden")
                            filled += 1
                        elif "email" in all_attrs or inp_type == "email":
                            inp.clear()
                            inp.send_keys("janovumllc@gmail.com")
                            filled += 1
                        elif "phone" in all_attrs or "tel" in all_attrs or inp_type == "tel":
                            inp.clear()
                            inp.send_keys("7862555014")
                            filled += 1
                        elif "company" in all_attrs or "business" in all_attrs or "organization" in all_attrs:
                            inp.clear()
                            inp.send_keys("Janovum LLC")
                            filled += 1
                        elif "subject" in all_attrs or "topic" in all_attrs:
                            inp.clear()
                            inp.send_keys(f"AI Receptionist for {biz} - Quick Question")
                            filled += 1
                        elif "website" in all_attrs or "url" in all_attrs:
                            inp.clear()
                            inp.send_keys("https://janovum.com")
                            filled += 1

                    if filled >= 2:
                        # Find and click submit button
                        submit_btns = form.find_elements(By.CSS_SELECTOR, "button[type='submit'], input[type='submit'], button.submit, .submit-btn, button")
                        if submit_btns:
                            try:
                                driver.execute_script("arguments[0].click();", submit_btns[0])
                                time.sleep(3)
                                print(f"  FORM SUBMITTED! ({filled} fields filled)")
                                sys.stdout.flush()
                                results["submitted"].append({"biz": biz, "url": url, "type": btype, "fields": filled, "time": datetime.now().isoformat()})
                                form_found = True
                                break
                            except Exception as e:
                                print(f"  Submit click failed: {e}")
                                sys.stdout.flush()
                except Exception as e:
                    continue

                driver.switch_to.default_content()

            if form_found:
                break

        except Exception as e:
            continue

    if not form_found and not phone_found:
        print(f"  No form or phone found")
        sys.stdout.flush()
        results["no_form"].append({"biz": biz, "url": base_url})
    elif not form_found:
        print(f"  No form found (got phone)")
        sys.stdout.flush()

    # Small delay between sites
    time.sleep(random.uniform(2, 5))

driver.quit()

# Save results
with open("contact_form_results.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"\n{'='*60}")
print(f"  CONTACT FORM BLITZ COMPLETE")
print(f"  Forms submitted: {len(results['submitted'])}")
print(f"  Phone numbers found: {len(results['phone_numbers'])}")
print(f"  No form found: {len(results['no_form'])}")
print(f"{'='*60}")

# Print all phone numbers for easy reference
if results["phone_numbers"]:
    print(f"\n  PHONE NUMBERS COLLECTED:")
    for p in results["phone_numbers"]:
        print(f"  {p['biz']}: {p['phone']} ({p['type']})")

sys.stdout.flush()
