"""
Janovum Cold Email Outreach
Scrapes businesses that need AI receptionists, sends personalized emails
"""

import time
import json
import random
import re
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# --- Config ---
GMAIL_EMAIL = "janovumllc@gmail.com"
GMAIL_PASS = "3Champion3!"
AGENT_EMAIL = "myfriendlyagent12@gmail.com"
AGENT_APP_PASS = "pdcvjroclstugncx"
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "platform", "agent_screenshots")
LEADS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outreach_leads.json")
SENT_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outreach_sent_log.json")

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# Best industries for AI receptionists (high call volume, miss calls = lose money)
SEARCHES = [
    "dental office Miami FL",
    "HVAC company Miami FL",
    "plumbing company Miami FL",
    "law firm Miami FL",
    "med spa Miami FL",
    "auto repair shop Miami FL",
    "veterinary clinic Miami FL",
    "chiropractic office Miami FL",
    "roofing company Miami FL",
    "dental office Fort Lauderdale FL",
    "HVAC company Fort Lauderdale FL",
    "plumbing company Broward County FL",
    "law firm Fort Lauderdale FL",
    "med spa Boca Raton FL",
    "electrician Miami FL",
    "pest control company Miami FL",
    "physical therapy clinic Miami FL",
    "insurance agency Miami FL",
    "real estate agency Miami FL",
    "dental office Coral Gables FL",
    "orthodontist Miami FL",
    "dermatologist Miami FL",
    "pool service company Miami FL",
    "landscaping company Miami FL",
    "moving company Miami FL",
]

# Email blacklists
DOMAIN_BLACKLIST = ["yelp.com", "yellowpages.com", "bbb.org", "facebook.com",
                    "google.com", "mapquest.com", "angi.com", "thumbtack.com",
                    "homeadvisor.com", "nextdoor.com", "tripadvisor.com",
                    "healthgrades.com", "zocdoc.com", "avvo.com", "findlaw.com",
                    "instagram.com", "twitter.com", "linkedin.com", "pinterest.com",
                    "tiktok.com", "youtube.com", "wikipedia.org", "reddit.com"]

EMAIL_BLACKLIST = ["noreply", "no-reply", "support@", "info@google", "example.com",
                   "sentry.io", "wixpress", "squarespace", "wordpress", "godaddy",
                   "mailchimp", "sendgrid", "amazonaws", "cloudflare"]


def is_good_email(email):
    email = email.lower().strip()
    for bl in EMAIL_BLACKLIST:
        if bl in email:
            return False
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return False
    # Prefer business domain emails over generic
    return True


def extract_emails(html):
    raw = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html)
    return list(set(e for e in raw if is_good_email(e)))


def get_domain(url):
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.replace("www.", "")
    except:
        return url


# ══════════════════════════════════════════
# PHASE 1: SCRAPE LEADS
# ══════════════════════════════════════════

def scrape_leads():
    import requests
    from bs4 import BeautifulSoup
    from urllib.parse import unquote

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    leads = []
    seen_domains = set()
    seen_emails = set()

    print(f"\n{'='*60}")
    print(f"  PHASE 1: SCRAPING LEADS FOR AI RECEPTIONIST PITCH")
    print(f"{'='*60}\n")

    for i, query in enumerate(SEARCHES):
        print(f"[{i+1}/{len(SEARCHES)}] Searching: {query}")
        try:
            url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}+contact+email"
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")

            results = soup.select(".result__a")
            for r in results[:6]:
                link = r.get("href", "")
                title = r.get_text(strip=True)

                if "uddg=" in link:
                    link = link.split("uddg=")[1].split("&")[0]
                    link = unquote(link)

                if not link.startswith("http"):
                    continue

                domain = get_domain(link)
                if domain in seen_domains:
                    continue
                if any(sd in domain for sd in DOMAIN_BLACKLIST):
                    continue

                seen_domains.add(domain)

                # Visit site + contact pages
                emails = []
                try:
                    page = requests.get(link, headers=headers, timeout=8)
                    emails = extract_emails(page.text)

                    if len(emails) == 0:
                        base = link.rstrip("/")
                        for suffix in ["/contact", "/contact-us", "/about", "/about-us", "/contact.html"]:
                            try:
                                cp = requests.get(base + suffix, headers=headers, timeout=6)
                                if cp.status_code == 200:
                                    emails += extract_emails(cp.text)
                            except:
                                pass

                    emails = list(set(emails))
                    # Filter out already-seen emails
                    emails = [e for e in emails if e not in seen_emails][:2]
                    for e in emails:
                        seen_emails.add(e)

                except Exception as e:
                    pass

                if emails:
                    industry = query.replace(" Miami FL", "").replace(" Fort Lauderdale FL", "").replace(" Broward County FL", "").replace(" Boca Raton FL", "").replace(" Coral Gables FL", "").strip()
                    lead = {
                        "name": title[:100],
                        "url": link,
                        "domain": domain,
                        "emails": emails,
                        "industry": industry,
                        "location": "South Florida",
                        "found": datetime.now().isoformat()
                    }
                    leads.append(lead)
                    print(f"  + {title[:50]} — {', '.join(emails)}")

            time.sleep(random.uniform(2, 4))

        except Exception as e:
            print(f"  ! Error: {e}")
            continue

    # Save leads
    with open(LEADS_FILE, "w") as f:
        json.dump(leads, f, indent=2)

    print(f"\n  TOTAL: {len(leads)} leads with emails saved\n")
    return leads


# ══════════════════════════════════════════
# PHASE 2: BUILD PERSONALIZED EMAILS
# ══════════════════════════════════════════

def build_email(lead):
    """Build a unique, personalized pitch based on their industry"""
    biz_name = lead["name"].split(" - ")[0].split(" | ")[0].split(" — ")[0].strip()
    industry = lead.get("industry", "")

    # Industry-specific pain points and hooks
    hooks = {
        "dental office": {
            "pain": "patients calling to book cleanings, reschedule, or ask about insurance",
            "hook": "Your front desk staff is probably juggling patients in-office AND the phone at the same time",
            "benefit": "books hygiene appointments, confirms insurance questions, and handles reschedules"
        },
        "orthodontist": {
            "pain": "patients calling about appointments, retainer issues, and payment plans",
            "hook": "Your front desk is swamped between walk-ins and ringing phones",
            "benefit": "books consultations, answers common questions about braces/Invisalign, and handles scheduling"
        },
        "dermatologist": {
            "pain": "patients calling for appointment scheduling and treatment questions",
            "hook": "Missed calls mean missed patients going to a competitor",
            "benefit": "books skin consultations, answers questions about procedures, and handles rescheduling"
        },
        "HVAC company": {
            "pain": "emergency AC calls, especially after hours when no one's picking up",
            "hook": "When someone's AC goes out at 10pm in Miami, they're calling the first company that answers",
            "benefit": "captures every emergency call 24/7, books service appointments, and gives quotes"
        },
        "plumbing company": {
            "pain": "emergency leak calls and service requests, especially nights and weekends",
            "hook": "A burst pipe at 2am means the homeowner is calling every plumber until someone picks up",
            "benefit": "answers emergency calls instantly, dispatches info to your team, and books non-urgent appointments"
        },
        "law firm": {
            "pain": "potential clients calling for consultations but getting voicemail instead",
            "hook": "Studies show 85% of people who reach voicemail at a law firm never call back",
            "benefit": "qualifies leads, books consultations, and collects case details before you even speak to them"
        },
        "med spa": {
            "pain": "clients calling to book Botox, facials, and ask about pricing",
            "hook": "Every missed call is a $300+ appointment walking out the door",
            "benefit": "books treatments, answers pricing questions, and upsells packages"
        },
        "auto repair shop": {
            "pain": "customers calling for estimates, appointment booking, and repair status",
            "hook": "Your mechanics shouldn't be answering phones, and customers hate waiting on hold",
            "benefit": "gives estimates, books drop-offs, and provides repair status updates"
        },
        "veterinary clinic": {
            "pain": "pet owners calling about sick pets, appointment scheduling, and emergencies",
            "hook": "A worried pet owner will go to the first vet that picks up — not the one with the best Yelp reviews",
            "benefit": "triages calls, books appointments, and handles medication refill requests"
        },
        "chiropractic office": {
            "pain": "patients calling to book adjustments and ask about insurance coverage",
            "hook": "New patient calls that go to voicemail rarely convert",
            "benefit": "books adjustments, handles new patient intake questions, and confirms insurance"
        },
        "roofing company": {
            "pain": "homeowners calling for quotes after storms or for general repairs",
            "hook": "After every storm, your phone blows up and you can't answer them all",
            "benefit": "captures every lead, books estimates, and collects property details"
        },
        "electrician": {
            "pain": "emergency calls for power outages and service requests",
            "hook": "Electrical emergencies don't happen during business hours",
            "benefit": "handles emergency dispatch, books service calls, and gives basic troubleshooting"
        },
        "pest control company": {
            "pain": "customers calling about infestations and wanting same-day service",
            "hook": "When someone sees roaches, they're calling everyone until someone picks up NOW",
            "benefit": "books inspections, answers treatment questions, and handles recurring service scheduling"
        },
        "physical therapy clinic": {
            "pain": "patients scheduling sessions, insurance verification, and cancellations",
            "hook": "No-shows and last-minute cancellations kill your revenue — an AI catches those calls instantly",
            "benefit": "manages scheduling, confirms appointments, and handles insurance pre-auth questions"
        },
        "insurance agency": {
            "pain": "clients calling for quotes, claims, and policy questions",
            "hook": "Every unanswered quote request is a customer signing with your competitor",
            "benefit": "collects quote info, answers policy FAQs, and routes claims to the right agent"
        },
        "real estate agency": {
            "pain": "buyers and sellers calling about listings, showings, and offers",
            "hook": "A buyer who can't reach you will call the next agent on Zillow",
            "benefit": "qualifies leads, books showings, and answers listing questions 24/7"
        },
        "pool service company": {
            "pain": "homeowners calling for cleanings, repairs, and chemical balancing",
            "hook": "Pool season means your phone rings nonstop and you're stuck in someone's backyard",
            "benefit": "books service visits, handles recurring scheduling, and answers maintenance questions"
        },
        "landscaping company": {
            "pain": "customers calling for quotes, scheduling, and seasonal services",
            "hook": "You're out mowing lawns all day and can't answer the phone — that's lost revenue",
            "benefit": "captures new leads, books estimates, and manages recurring service schedules"
        },
        "moving company": {
            "pain": "customers calling for moving quotes and availability",
            "hook": "People planning a move call 3-4 companies — whoever answers first usually wins",
            "benefit": "collects move details, gives instant estimates, and books moving dates"
        },
    }

    h = hooks.get(industry, {
        "pain": "customers calling and not getting through",
        "hook": "Every missed call is money left on the table",
        "benefit": "answers calls 24/7, books appointments, and handles customer questions"
    })

    # Randomize email style slightly for each one
    templates = [
        # Template 1 — Direct problem/solution
        f"""Hi,

I found {biz_name} online and wanted to reach out with something that could help your business.

{h['hook']}. That's {h['pain']} — all going unanswered.

We built an AI receptionist that {h['benefit']} — 24/7, sounding completely natural. Your customers won't know it's AI.

No hold music. No voicemail. Every call answered on the first ring.

We're working with a few {industry} businesses in South Florida right now and getting great results. Would love to show you a quick demo — takes 10 minutes.

Check us out: https://janovum.com

Worth a quick look?

Best,
Jaden Gonzalez
Founder, Janovum LLC
janovumllc@gmail.com
https://janovum.com""",

        # Template 2 — Question-led
        f"""Hi,

Quick question — how many calls does {biz_name} miss per week?

For most {industry} businesses, the answer is more than they think. {h['hook']}.

We built an AI phone receptionist that {h['benefit']}. It picks up instantly, sounds human, and works 24/7 — nights, weekends, holidays.

It costs less than a part-time employee and never calls in sick.

I'd love to give you a free demo so you can hear it in action. Here's our site: https://janovum.com

Do you have 10 minutes this week?

Best,
Jaden Gonzalez
Founder, Janovum LLC
janovumllc@gmail.com""",

        # Template 3 — Social proof angle
        f"""Hi,

I work with {industry} businesses in South Florida to solve one problem: missed calls costing you money.

{h['hook']}.

We created Janovum — an AI receptionist that {h['benefit']}. It answers every call on the first ring, 24/7, and sounds just like a real person.

Here's what business owners tell us after switching:
— "We stopped losing leads to voicemail overnight"
— "It paid for itself in the first week"
— "Our customers actually prefer it — no more hold times"

I'd love to set up {biz_name} with a free trial. Check us out at https://janovum.com and let me know if you're interested.

Jaden Gonzalez
Founder, Janovum LLC
janovumllc@gmail.com
https://janovum.com""",
    ]

    body = random.choice(templates)

    # Randomize subject lines too
    subjects = [
        f"AI Receptionist for {biz_name} — Never Miss a Call Again",
        f"Quick question for {biz_name}",
        f"{biz_name} — Stop Losing Calls to Voicemail",
        f"How {industry} businesses are answering 100% of calls",
        f"10-minute demo for {biz_name}?",
    ]
    subject = random.choice(subjects)

    return subject, body


# ══════════════════════════════════════════
# PHASE 3: SEND VIA SELENIUM (Gmail Web)
# ══════════════════════════════════════════

def send_via_selenium(leads):
    """Log into Gmail via Selenium and send emails through compose"""
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    print(f"\n{'='*60}")
    print(f"  SENDING {len(leads)} EMAILS VIA GMAIL")
    print(f"{'='*60}\n")

    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")

    driver = uc.Chrome(options=options)
    wait = WebDriverWait(driver, 25)
    sent_count = 0
    sent_log = []

    try:
        # LOGIN
        print("[*] Logging into Gmail...")
        driver.get("https://accounts.google.com/signin/v2/identifier?service=mail&flowName=GlifWebSignIn")
        time.sleep(3)
        save_screenshot(driver, "Login page")

        # Email
        email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="email"]')))
        email_input.send_keys(GMAIL_EMAIL)
        email_input.send_keys(Keys.RETURN)
        time.sleep(4)
        save_screenshot(driver, "Entered email")

        # Password
        pass_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[type="password"]')))
        pass_input.send_keys(GMAIL_PASS)
        pass_input.send_keys(Keys.RETURN)
        time.sleep(6)
        save_screenshot(driver, "Entered password")

        # Wait for inbox
        time.sleep(5)
        save_screenshot(driver, "Inbox loaded")
        current_url = driver.current_url
        if "mail.google.com" not in current_url and "inbox" not in current_url:
            print("  ! Might need verification — check the browser window")
            save_screenshot(driver, "Possible verification needed")
            input("  Press ENTER after handling verification in the browser...")

        print("  ✓ Logged in!\n")

        # SEND EACH EMAIL
        for i, lead in enumerate(leads):
            to_email = lead["emails"][0]
            subject, body = build_email(lead)
            biz_name = lead["name"].split(" - ")[0].split(" | ")[0].strip()[:50]

            print(f"[{i+1}/{len(leads)}] → {to_email} ({biz_name})")

            try:
                # Navigate to compose URL directly (most reliable)
                compose_url = f"https://mail.google.com/mail/?view=cm&to={to_email}&su={subject.replace(' ', '+')}"
                driver.get(compose_url)
                time.sleep(4)

                # Find the body field and fill it
                body_div = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[aria-label="Message Body"], div[role="textbox"][aria-label*="Message"], div.Am.Al.editable')))
                # Set body via JS
                html_body = body.replace("\n", "<br>")
                driver.execute_script("arguments[0].innerHTML = arguments[1];", body_div, html_body)
                time.sleep(1)

                save_screenshot(driver, f"Composed #{i+1} to {to_email}")

                # Click Send (Ctrl+Enter is most reliable)
                body_div.send_keys(Keys.CONTROL + Keys.RETURN)
                time.sleep(3)

                save_screenshot(driver, f"Sent #{i+1}")
                print(f"  ✓ SENT!")

                sent_log.append({
                    "to": to_email, "name": biz_name, "subject": subject,
                    "industry": lead.get("industry", ""), "status": "sent",
                    "sent_at": datetime.now().isoformat()
                })
                sent_count += 1

                # Delay between emails
                delay = random.uniform(30, 55)
                print(f"  ... waiting {delay:.0f}s")
                time.sleep(delay)

            except Exception as e:
                print(f"  ✗ Failed: {e}")
                save_screenshot(driver, f"Error #{i+1}")
                sent_log.append({
                    "to": to_email, "name": biz_name, "status": "failed",
                    "error": str(e), "sent_at": datetime.now().isoformat()
                })
                time.sleep(3)
                continue

    except Exception as e:
        print(f"\n  CRITICAL ERROR: {e}")
        save_screenshot(driver, "Critical error")
    finally:
        with open(SENT_LOG, "w") as f:
            json.dump(sent_log, f, indent=2)
        stop_agent()
        try:
            driver.quit()
        except:
            pass

    print(f"\n{'='*60}")
    print(f"  COMPLETE: {sent_count}/{len(leads)} emails sent")
    print(f"  Log: {SENT_LOG}")
    print(f"{'='*60}\n")
    return sent_count


# ══════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════

if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════════════╗
║   JANOVUM COLD OUTREACH — AI RECEPTIONIST       ║
║   From: {GMAIL_EMAIL}                   ║
║   Target: South Florida businesses               ║
╚══════════════════════════════════════════════════╝
    """)

    # Phase 1: Scrape leads
    if os.path.exists(LEADS_FILE):
        with open(LEADS_FILE) as f:
            leads = json.load(f)
        print(f"Found {len(leads)} existing leads.")
        ans = input("Use existing leads? (y/n): ").strip().lower()
        if ans != "y":
            leads = scrape_leads()
    else:
        leads = scrape_leads()

    if not leads:
        print("No leads found!")
        exit(1)

    # Show preview
    print(f"\n--- PREVIEW: First email ---")
    subj, body = build_email(leads[0])
    print(f"To: {leads[0]['emails'][0]}")
    print(f"Subject: {subj}")
    print(f"\n{body[:300]}...\n")

    print(f"Ready to send {len(leads)} personalized emails.")
    go = input("Send them? (y/n): ").strip().lower()
    if go != "y":
        print("Aborted.")
        exit(0)

    # Phase 2: Send
    send_via_selenium(leads)
