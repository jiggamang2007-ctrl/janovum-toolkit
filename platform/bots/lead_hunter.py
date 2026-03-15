"""
Lead Hunter Bot
Generic business lead finder. Searches DuckDuckGo for leads based on keywords,
scrapes contact info (emails) from pages, and saves to a leads database.
"""

import sys
import os
import json
import time
import re
import logging
import hashlib
from pathlib import Path
from datetime import datetime

PLATFORM_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLATFORM_DIR))

try:
    from core.api_router import search_web
except ImportError:
    search_web = None

import requests
from bs4 import BeautifulSoup

BOT_INFO = {
    "name": "Lead Hunter",
    "category": "sales",
    "description": "Finds business leads and contact info from web searches",
    "icon": "\U0001f3af",
    "version": "1.0",
    "author": "Janovum",
    "config_schema": {
        "search_queries": {"type": "list", "default": [
            "small business owner email contact",
            "startup founder contact",
            "local business directory",
        ]},
        "industries": {"type": "list", "default": ["technology", "real estate", "marketing"]},
        "locations": {"type": "list", "default": [""]},
        "max_results_per_query": {"type": "int", "default": 10},
        "max_leads_per_run": {"type": "int", "default": 50},
        "interval_seconds": {"type": "int", "default": 3600},
        "scrape_emails": {"type": "bool", "default": True},
        "email_blacklist_domains": {"type": "list", "default": [
            "example.com", "domain.com", "email.com", "test.com",
            "google.com", "facebook.com", "twitter.com", "instagram.com",
            "youtube.com", "wikipedia.org", "github.com",
        ]},
    }
}

_running = False
_status = {"state": "stopped", "leads_found": 0, "pages_scraped": 0, "last_run": None, "errors": []}
_logger = logging.getLogger("LeadHunter")
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    _logger.addHandler(logging.StreamHandler())

DATA_DIR = PLATFORM_DIR / "data" / "bots" / "lead_hunter"
LEADS_FILE = DATA_DIR / "leads.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}


def _ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_leads():
    if LEADS_FILE.exists():
        try:
            return json.loads(LEADS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_leads(leads):
    _ensure_dirs()
    LEADS_FILE.write_text(json.dumps(leads, indent=2, default=str), encoding="utf-8")


def _lead_id(name, url):
    return hashlib.md5(f"{name}|{url}".encode()).hexdigest()


def _extract_emails(text, blacklist_domains=None):
    """Extract email addresses from text, filtering out blacklisted domains."""
    blacklist = set(d.lower() for d in (blacklist_domains or []))
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    filtered = []
    for email in emails:
        email = email.lower().strip()
        domain = email.split("@")[1] if "@" in email else ""
        # Skip blacklisted, image files, CSS files
        if domain in blacklist:
            continue
        if any(email.endswith(ext) for ext in [".png", ".jpg", ".gif", ".css", ".js", ".svg"]):
            continue
        if len(email) > 60:
            continue
        filtered.append(email)
    return list(set(filtered))


def _extract_phone_numbers(text):
    """Extract phone numbers from text."""
    patterns = [
        r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        r'\+1[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',
    ]
    phones = []
    for p in patterns:
        phones.extend(re.findall(p, text))
    return list(set(phones))[:3]


def _scrape_page_contacts(url, blacklist_domains):
    """Scrape a webpage for contact information."""
    contacts = {"emails": [], "phones": [], "social": []}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        if resp.status_code != 200:
            return contacts

        text = resp.text
        contacts["emails"] = _extract_emails(text, blacklist_domains)
        contacts["phones"] = _extract_phone_numbers(text)

        # Try to find social links
        soup = BeautifulSoup(text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            if "linkedin.com/" in href and href not in contacts["social"]:
                contacts["social"].append(a["href"])
            elif "twitter.com/" in href and href not in contacts["social"]:
                contacts["social"].append(a["href"])

        # Also check /contact or /about pages
        for path in ["/contact", "/about", "/contact-us", "/about-us"]:
            try:
                base = url.rstrip("/")
                contact_url = base + path
                cresp = requests.get(contact_url, headers=HEADERS, timeout=8, allow_redirects=True)
                if cresp.status_code == 200:
                    extra_emails = _extract_emails(cresp.text, blacklist_domains)
                    contacts["emails"].extend(extra_emails)
                    extra_phones = _extract_phone_numbers(cresp.text)
                    contacts["phones"].extend(extra_phones)
            except Exception:
                pass

        contacts["emails"] = list(set(contacts["emails"]))[:5]
        contacts["phones"] = list(set(contacts["phones"]))[:3]
        contacts["social"] = contacts["social"][:5]

    except Exception as e:
        _logger.debug(f"Scrape error for {url}: {e}")

    return contacts


def _search_leads(config):
    """Search DuckDuckGo and scrape results for leads."""
    global _status

    queries = config.get("search_queries", [])
    industries = config.get("industries", [])
    locations = config.get("locations", [""])
    max_per_query = config.get("max_results_per_query", 10)
    scrape_emails = config.get("scrape_emails", True)
    blacklist = config.get("email_blacklist_domains", [])

    all_new_leads = []
    existing = _load_leads()
    existing_ids = {l["id"] for l in existing}

    for query_template in queries:
        for industry in industries:
            for location in locations:
                if not _running:
                    return all_new_leads

                search_query = f"{query_template} {industry} {location}".strip()
                _logger.info(f"Searching: {search_query}")

                try:
                    if search_web:
                        result = search_web(search_query, max_results=max_per_query)
                        results_list = result.get("results", [])
                    else:
                        resp = requests.get(
                            "https://html.duckduckgo.com/html/",
                            params={"q": search_query},
                            headers=HEADERS,
                            timeout=15
                        )
                        if resp.status_code != 200:
                            continue
                        soup = BeautifulSoup(resp.text, "html.parser")
                        results_list = []
                        for rd in soup.select(".result__body")[:max_per_query]:
                            title_el = rd.select_one(".result__title a")
                            snippet_el = rd.select_one(".result__snippet")
                            if title_el:
                                results_list.append({
                                    "title": title_el.get_text(strip=True),
                                    "href": title_el.get("href", ""),
                                    "body": snippet_el.get_text(strip=True) if snippet_el else "",
                                })

                    for r in results_list:
                        title = r.get("title", "")
                        url = r.get("href", r.get("link", ""))
                        body = r.get("body", r.get("snippet", ""))

                        lid = _lead_id(title, url)
                        if lid in existing_ids:
                            continue

                        lead = {
                            "id": lid,
                            "source": "duckduckgo",
                            "query": search_query,
                            "industry": industry,
                            "location": location,
                            "name": title.strip(),
                            "url": url.strip(),
                            "description": body.strip()[:500],
                            "emails": [],
                            "phones": [],
                            "social_links": [],
                            "scraped_at": datetime.now().isoformat(),
                            "contacted": False,
                        }

                        # Scrape contact info from the page
                        if scrape_emails and url:
                            _logger.info(f"  Scraping contacts from: {url[:60]}...")
                            contacts = _scrape_page_contacts(url, blacklist)
                            lead["emails"] = contacts["emails"]
                            lead["phones"] = contacts["phones"]
                            lead["social_links"] = contacts["social"]
                            _status["pages_scraped"] += 1
                            time.sleep(1.5)  # Polite delay

                        all_new_leads.append(lead)
                        existing_ids.add(lid)

                    time.sleep(2)  # Delay between searches

                except Exception as e:
                    _logger.error(f"Search error for '{search_query}': {e}")
                    _status["errors"].append(str(e))

    # Merge and save
    existing.extend(all_new_leads)
    max_total = config.get("max_leads_per_run", 50)
    all_new_leads = all_new_leads[:max_total]
    _save_leads(existing)

    return all_new_leads


def run(config=None):
    """Start the lead hunter bot loop."""
    global _running, _status
    _running = True
    _ensure_dirs()

    if config is None:
        config = {v: s["default"] for v, s in BOT_INFO["config_schema"].items()}

    _status = {"state": "running", "leads_found": 0, "pages_scraped": 0, "last_run": None, "errors": []}
    _logger.info("Lead Hunter started.")

    interval = config.get("interval_seconds", 3600)

    while _running:
        try:
            _status["state"] = "hunting"
            new_leads = _search_leads(config)
            _status["leads_found"] += len(new_leads)
            _status["last_run"] = datetime.now().isoformat()
            _status["state"] = "waiting"

            leads_with_email = [l for l in new_leads if l.get("emails")]
            _logger.info(f"Found {len(new_leads)} new leads ({len(leads_with_email)} with emails). Next run in {interval}s...")
        except Exception as e:
            _logger.error(f"Hunt cycle error: {e}")
            _status["errors"].append(str(e))
            _status["state"] = "error"

        for _ in range(interval):
            if not _running:
                break
            time.sleep(1)

    _status["state"] = "stopped"
    _logger.info("Lead Hunter stopped.")


def stop():
    global _running
    _running = False
    _status["state"] = "stopping"


def get_status():
    total = len(_load_leads()) if LEADS_FILE.exists() else 0
    return {**_status, "total_leads_in_file": total}


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        stop()
