"""
Real Estate Lead Scraper Bot
Scrapes property listings from RSS feeds, Craigslist housing, and DuckDuckGo search.
Saves leads to a JSON file for downstream bots.
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

# Setup path for platform imports
PLATFORM_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLATFORM_DIR))

try:
    from core.api_router import search_web, get_router
except ImportError:
    search_web = None

import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

BOT_INFO = {
    "name": "Real Estate Lead Scraper",
    "category": "real_estate",
    "description": "Scrapes property listings and leads from free sources",
    "icon": "\U0001f3e0",
    "version": "1.0",
    "author": "Janovum",
    "config_schema": {
        "search_queries": {"type": "list", "default": ["houses for sale", "apartments for rent"]},
        "locations": {"type": "list", "default": ["New York", "Los Angeles", "Chicago"]},
        "craigslist_cities": {"type": "list", "default": ["newyork", "losangeles", "chicago"]},
        "max_leads_per_run": {"type": "int", "default": 50},
        "interval_seconds": {"type": "int", "default": 3600},
        "scrape_craigslist": {"type": "bool", "default": True},
        "scrape_rss": {"type": "bool", "default": True},
        "scrape_duckduckgo": {"type": "bool", "default": True},
    }
}

_running = False
_status = {"state": "stopped", "leads_found": 0, "last_run": None, "errors": []}
_logger = logging.getLogger("RealEstateLeadScraper")
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    _logger.addHandler(logging.StreamHandler())

DATA_DIR = PLATFORM_DIR / "data" / "bots" / "real_estate_lead_scraper"
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


def _lead_id(title, url):
    raw = f"{title}|{url}"
    return hashlib.md5(raw.encode()).hexdigest()


def _scrape_craigslist(cities, max_per_city=10):
    """Scrape Craigslist housing RSS feeds."""
    leads = []
    for city in cities:
        try:
            rss_url = f"https://{city}.craigslist.org/search/apa?format=rss"
            resp = requests.get(rss_url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                _logger.warning(f"Craigslist {city} returned {resp.status_code}")
                continue

            root = ET.fromstring(resp.content)
            ns = {"rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                  "dc": "http://purl.org/dc/elements/1.1/",
                  "enc": "http://purl.oclc.org/net/rss_2.0/enc#"}

            items = root.findall(".//item")
            if not items:
                items = root.findall(".//{http://purl.org/rss/1.0/}item")

            count = 0
            for item in items:
                if count >= max_per_city:
                    break
                title = item.findtext("title") or item.findtext("{http://purl.org/rss/1.0/}title") or ""
                link = item.findtext("link") or item.findtext("{http://purl.org/rss/1.0/}link") or ""
                desc = item.findtext("description") or item.findtext("{http://purl.org/rss/1.0/}description") or ""
                date = item.findtext("{http://purl.org/dc/elements/1.1/}date") or ""

                # Extract price from title (Craigslist format: "$1,200 / 2br - Title")
                price_match = re.search(r'\$[\d,]+', title)
                price = price_match.group(0) if price_match else ""
                bedrooms_match = re.search(r'(\d+)br', title)
                bedrooms = bedrooms_match.group(1) if bedrooms_match else ""

                lead = {
                    "id": _lead_id(title, link),
                    "source": "craigslist",
                    "city": city,
                    "title": title.strip(),
                    "url": link.strip(),
                    "description": desc.strip()[:500],
                    "price": price,
                    "bedrooms": bedrooms,
                    "date_posted": date,
                    "scraped_at": datetime.now().isoformat(),
                    "contacted": False,
                    "contact_email": "",
                }
                leads.append(lead)
                count += 1

            _logger.info(f"Craigslist {city}: found {count} listings")
        except Exception as e:
            _logger.error(f"Craigslist {city} error: {e}")
            _status["errors"].append(f"Craigslist {city}: {str(e)}")

    return leads


def _scrape_rss_feeds():
    """Scrape general real estate RSS feeds (Realtor, Redfin blog, etc.)."""
    leads = []
    rss_sources = [
        ("https://www.realtor.com/news/feed/", "realtor_news"),
        ("https://www.housingwire.com/feed/", "housingwire"),
    ]

    for rss_url, source_name in rss_sources:
        try:
            resp = requests.get(rss_url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue

            root = ET.fromstring(resp.content)
            for item in root.findall(".//item")[:10]:
                title = item.findtext("title") or ""
                link = item.findtext("link") or ""
                desc = item.findtext("description") or ""
                pub_date = item.findtext("pubDate") or ""

                # Clean HTML from description
                if desc:
                    soup = BeautifulSoup(desc, "html.parser")
                    desc = soup.get_text()[:500]

                lead = {
                    "id": _lead_id(title, link),
                    "source": source_name,
                    "city": "",
                    "title": title.strip(),
                    "url": link.strip(),
                    "description": desc.strip(),
                    "price": "",
                    "bedrooms": "",
                    "date_posted": pub_date,
                    "scraped_at": datetime.now().isoformat(),
                    "contacted": False,
                    "contact_email": "",
                }
                leads.append(lead)

            _logger.info(f"RSS {source_name}: found {len(leads)} items")
        except Exception as e:
            _logger.error(f"RSS {source_name} error: {e}")
            _status["errors"].append(f"RSS {source_name}: {str(e)}")

    return leads


def _scrape_duckduckgo(queries, locations, max_results=10):
    """Search DuckDuckGo for real estate listings."""
    leads = []

    for query in queries:
        for location in locations:
            try:
                search_query = f"{query} {location}"

                if search_web:
                    result = search_web(search_query, max_results=max_results)
                    results_list = result.get("results", [])
                else:
                    # Fallback: direct DuckDuckGo HTML scraping
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
                    for result_div in soup.select(".result__body")[:max_results]:
                        title_el = result_div.select_one(".result__title a")
                        snippet_el = result_div.select_one(".result__snippet")
                        if title_el:
                            results_list.append({
                                "title": title_el.get_text(strip=True),
                                "href": title_el.get("href", ""),
                                "body": snippet_el.get_text(strip=True) if snippet_el else "",
                            })

                for r in results_list:
                    title = r.get("title", "")
                    link = r.get("href", r.get("link", ""))
                    body = r.get("body", r.get("snippet", ""))
                    price_match = re.search(r'\$[\d,]+(?:\.?\d*)?(?:[kKmM])?', f"{title} {body}")
                    price = price_match.group(0) if price_match else ""

                    lead = {
                        "id": _lead_id(title, link),
                        "source": "duckduckgo",
                        "city": location,
                        "title": title.strip(),
                        "url": link.strip(),
                        "description": body.strip()[:500],
                        "price": price,
                        "bedrooms": "",
                        "date_posted": "",
                        "scraped_at": datetime.now().isoformat(),
                        "contacted": False,
                        "contact_email": "",
                    }
                    leads.append(lead)

                _logger.info(f"DDG '{search_query}': found {len(results_list)} results")
                time.sleep(2)  # Be polite

            except Exception as e:
                _logger.error(f"DDG search error: {e}")
                _status["errors"].append(f"DDG: {str(e)}")

    return leads


def _extract_emails_from_page(url):
    """Try to extract email addresses from a listing page."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', resp.text)
            # Filter out common false positives
            filtered = [e for e in emails if not any(x in e.lower() for x in ["example.com", "domain.com", "email.com", ".png", ".jpg", ".gif"])]
            return list(set(filtered))[:3]
    except Exception:
        pass
    return []


def _run_scrape(config):
    """Execute one full scrape cycle."""
    global _status
    _status["errors"] = []
    all_leads = []

    if config.get("scrape_craigslist", True):
        cl_leads = _scrape_craigslist(
            config.get("craigslist_cities", ["newyork", "losangeles", "chicago"]),
            max_per_city=config.get("max_leads_per_run", 50) // 3
        )
        all_leads.extend(cl_leads)

    if config.get("scrape_rss", True):
        rss_leads = _scrape_rss_feeds()
        all_leads.extend(rss_leads)

    if config.get("scrape_duckduckgo", True):
        ddg_leads = _scrape_duckduckgo(
            config.get("search_queries", ["houses for sale", "apartments for rent"]),
            config.get("locations", ["New York", "Los Angeles", "Chicago"]),
            max_results=5
        )
        all_leads.extend(ddg_leads)

    # Deduplicate with existing leads
    existing = _load_leads()
    existing_ids = {l["id"] for l in existing}
    new_leads = [l for l in all_leads if l["id"] not in existing_ids]

    # Try to extract emails from new lead pages (limit to avoid being too aggressive)
    for lead in new_leads[:10]:
        if lead["url"] and not lead["contact_email"]:
            emails = _extract_emails_from_page(lead["url"])
            if emails:
                lead["contact_email"] = emails[0]
            time.sleep(1)

    # Trim to max
    max_leads = config.get("max_leads_per_run", 50)
    new_leads = new_leads[:max_leads]

    # Merge and save
    existing.extend(new_leads)
    _save_leads(existing)

    _logger.info(f"Scrape complete: {len(new_leads)} new leads, {len(existing)} total")
    return len(new_leads)


def run(config=None):
    """Start the lead scraper bot loop."""
    global _running, _status
    _running = True
    _ensure_dirs()

    if config is None:
        config = {v: s["default"] for v, s in BOT_INFO["config_schema"].items()}

    _status["state"] = "running"
    _logger.info(f"Real Estate Lead Scraper started with config: {json.dumps(config, indent=2)}")

    interval = config.get("interval_seconds", 3600)

    while _running:
        try:
            _status["state"] = "scraping"
            new_count = _run_scrape(config)
            _status["leads_found"] += new_count
            _status["last_run"] = datetime.now().isoformat()
            _status["state"] = "waiting"
            _logger.info(f"Next scrape in {interval}s...")
        except Exception as e:
            _logger.error(f"Scrape cycle error: {e}")
            _status["errors"].append(str(e))
            _status["state"] = "error"

        # Sleep in small increments so stop() is responsive
        for _ in range(interval):
            if not _running:
                break
            time.sleep(1)

    _status["state"] = "stopped"
    _logger.info("Real Estate Lead Scraper stopped.")


def stop():
    """Stop the bot."""
    global _running
    _running = False
    _status["state"] = "stopping"


def get_status():
    """Get current bot status."""
    total_leads = len(_load_leads()) if LEADS_FILE.exists() else 0
    return {**_status, "total_leads_in_file": total_leads}


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        stop()
