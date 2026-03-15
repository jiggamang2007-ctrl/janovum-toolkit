"""
Real Estate Market Analyzer Bot
Analyzes property data from scraped leads, calculates stats,
and generates AI market reports using Pollinations.
"""

import sys
import os
import json
import time
import re
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict

PLATFORM_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLATFORM_DIR))

try:
    from core.api_router import generate_text_free
except ImportError:
    generate_text_free = None

import requests

BOT_INFO = {
    "name": "Market Analyzer",
    "category": "real_estate",
    "description": "Analyzes property market data and generates AI reports",
    "icon": "\U0001f4ca",
    "version": "1.0",
    "author": "Janovum",
    "config_schema": {
        "leads_file": {"type": "str", "default": ""},
        "interval_seconds": {"type": "int", "default": 7200},
        "generate_ai_report": {"type": "bool", "default": True},
        "report_format": {"type": "str", "default": "markdown"},
    }
}

_running = False
_status = {"state": "stopped", "reports_generated": 0, "last_analysis": None, "errors": []}
_logger = logging.getLogger("MarketAnalyzer")
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    _logger.addHandler(logging.StreamHandler())

DATA_DIR = PLATFORM_DIR / "data" / "bots" / "real_estate_market_analyzer"
DEFAULT_LEADS_FILE = PLATFORM_DIR / "data" / "bots" / "real_estate_lead_scraper" / "leads.json"


def _ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_leads(leads_file):
    lf = Path(leads_file) if leads_file else DEFAULT_LEADS_FILE
    if lf.exists():
        try:
            return json.loads(lf.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _parse_price(price_str):
    """Parse price string to float. Handles $1,200, $1.5M, $500K, etc."""
    if not price_str:
        return None
    price_str = price_str.strip().replace(",", "").replace("$", "")
    try:
        if price_str.upper().endswith("M"):
            return float(price_str[:-1]) * 1_000_000
        elif price_str.upper().endswith("K"):
            return float(price_str[:-1]) * 1_000
        return float(price_str)
    except (ValueError, IndexError):
        return None


def _analyze_leads(leads):
    """Perform statistical analysis on leads data."""
    stats = {
        "total_leads": len(leads),
        "by_source": defaultdict(int),
        "by_city": defaultdict(lambda: {"count": 0, "prices": [], "avg_price": 0}),
        "price_stats": {"min": None, "max": None, "avg": None, "median": None, "count_with_price": 0},
        "bedroom_distribution": defaultdict(int),
        "contacted_count": 0,
        "with_email_count": 0,
        "sources": [],
        "date_range": {"earliest": None, "latest": None},
    }

    prices = []

    for lead in leads:
        # By source
        stats["by_source"][lead.get("source", "unknown")] += 1

        # By city
        city = lead.get("city", "unknown") or "unknown"
        price = _parse_price(lead.get("price", ""))
        stats["by_city"][city]["count"] += 1
        if price is not None:
            stats["by_city"][city]["prices"].append(price)
            prices.append(price)

        # Bedrooms
        br = lead.get("bedrooms", "")
        if br:
            stats["bedroom_distribution"][f"{br}br"] += 1

        # Contact info
        if lead.get("contacted"):
            stats["contacted_count"] += 1
        if lead.get("contact_email"):
            stats["with_email_count"] += 1

        # Date tracking
        scraped = lead.get("scraped_at", "")
        if scraped:
            if stats["date_range"]["earliest"] is None or scraped < stats["date_range"]["earliest"]:
                stats["date_range"]["earliest"] = scraped
            if stats["date_range"]["latest"] is None or scraped > stats["date_range"]["latest"]:
                stats["date_range"]["latest"] = scraped

    # Price stats
    if prices:
        prices.sort()
        stats["price_stats"]["min"] = min(prices)
        stats["price_stats"]["max"] = max(prices)
        stats["price_stats"]["avg"] = sum(prices) / len(prices)
        stats["price_stats"]["median"] = prices[len(prices) // 2]
        stats["price_stats"]["count_with_price"] = len(prices)

    # City averages
    for city, data in stats["by_city"].items():
        if data["prices"]:
            data["avg_price"] = sum(data["prices"]) / len(data["prices"])
        data["prices"] = len(data["prices"])  # Replace list with count for serialization

    # Convert defaultdicts to regular dicts
    stats["by_source"] = dict(stats["by_source"])
    stats["by_city"] = dict(stats["by_city"])
    stats["bedroom_distribution"] = dict(stats["bedroom_distribution"])
    stats["sources"] = list(stats["by_source"].keys())

    return stats


def _generate_ai_report(stats):
    """Generate an AI market analysis report using Pollinations."""
    prompt = (
        f"Write a concise real estate market analysis report based on this data. "
        f"Use professional tone, include insights and recommendations. Under 500 words. "
        f"Do not use any markdown headers or formatting symbols. Use plain text with line breaks.\n\n"
        f"Data Summary:\n"
        f"- Total listings analyzed: {stats['total_leads']}\n"
        f"- Sources: {', '.join(stats['sources'])}\n"
        f"- Price range: ${stats['price_stats']['min']:,.0f} - ${stats['price_stats']['max']:,.0f}\n"
        f"- Average price: ${stats['price_stats']['avg']:,.0f}\n"
        f"- Median price: ${stats['price_stats']['median']:,.0f}\n"
        f"- Cities covered: {', '.join(stats['by_city'].keys())}\n"
        f"- Bedroom distribution: {stats['bedroom_distribution']}\n"
        f"- Leads with contact info: {stats['with_email_count']}/{stats['total_leads']}\n"
    ) if stats['price_stats']['avg'] else (
        f"Write a concise real estate market overview report. "
        f"Total listings: {stats['total_leads']}. Sources: {', '.join(stats['sources'])}. "
        f"Cities: {', '.join(stats['by_city'].keys())}. Under 300 words. Plain text."
    )

    try:
        if generate_text_free:
            result = generate_text_free(prompt)
            return result.get("text", "").strip()
        else:
            import urllib.parse
            encoded = urllib.parse.quote(prompt)
            url = f"https://text.pollinations.ai/{encoded}"
            resp = requests.get(url, headers={"User-Agent": "Janovum/1.0"}, timeout=60)
            if resp.status_code == 200:
                return resp.text.strip()
    except Exception as e:
        _logger.error(f"AI report generation failed: {e}")

    return "AI report generation unavailable. See raw statistics below."


def _format_report(stats, ai_text, fmt="markdown"):
    """Format the full report."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if fmt == "markdown":
        report = f"# Real Estate Market Report\n\n"
        report += f"**Generated:** {now}\n\n"
        report += f"## AI Analysis\n\n{ai_text}\n\n"
        report += f"## Key Statistics\n\n"
        report += f"| Metric | Value |\n|--------|-------|\n"
        report += f"| Total Listings | {stats['total_leads']} |\n"
        if stats['price_stats']['avg']:
            report += f"| Average Price | ${stats['price_stats']['avg']:,.0f} |\n"
            report += f"| Median Price | ${stats['price_stats']['median']:,.0f} |\n"
            report += f"| Min Price | ${stats['price_stats']['min']:,.0f} |\n"
            report += f"| Max Price | ${stats['price_stats']['max']:,.0f} |\n"
        report += f"| Leads with Email | {stats['with_email_count']} |\n"
        report += f"| Already Contacted | {stats['contacted_count']} |\n\n"

        report += f"## By Source\n\n"
        for source, count in stats["by_source"].items():
            report += f"- **{source}**: {count} listings\n"

        report += f"\n## By City\n\n"
        for city, data in stats["by_city"].items():
            avg = f" (avg ${data['avg_price']:,.0f})" if data['avg_price'] else ""
            report += f"- **{city}**: {data['count']} listings{avg}\n"

        if stats["bedroom_distribution"]:
            report += f"\n## Bedroom Distribution\n\n"
            for br, count in sorted(stats["bedroom_distribution"].items()):
                report += f"- {br}: {count}\n"
    else:
        report = f"Real Estate Market Report ({now})\n{'='*50}\n\n"
        report += f"{ai_text}\n\n"
        report += f"Statistics:\n"
        report += f"  Total Listings: {stats['total_leads']}\n"
        if stats['price_stats']['avg']:
            report += f"  Avg Price: ${stats['price_stats']['avg']:,.0f}\n"
        report += f"  Leads w/ Email: {stats['with_email_count']}\n"

    return report


def _run_analysis(config):
    """Execute one analysis cycle."""
    global _status

    leads_file = config.get("leads_file", "")
    leads = _load_leads(leads_file)

    if not leads:
        _logger.info("No leads found to analyze.")
        return

    # Run statistical analysis
    stats = _analyze_leads(leads)

    # Generate AI report if enabled
    ai_text = ""
    if config.get("generate_ai_report", True):
        _logger.info("Generating AI market report...")
        ai_text = _generate_ai_report(stats)
    else:
        ai_text = "AI report generation disabled."

    # Format report
    fmt = config.get("report_format", "markdown")
    report = _format_report(stats, ai_text, fmt)

    # Save report
    _ensure_dirs()
    ext = "md" if fmt == "markdown" else "txt"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = DATA_DIR / f"market_report_{timestamp}.{ext}"
    report_file.write_text(report, encoding="utf-8")

    # Also save latest
    latest_file = DATA_DIR / f"latest_report.{ext}"
    latest_file.write_text(report, encoding="utf-8")

    # Save raw stats
    stats_file = DATA_DIR / f"stats_{timestamp}.json"
    stats_file.write_text(json.dumps(stats, indent=2, default=str), encoding="utf-8")

    _status["reports_generated"] += 1
    _logger.info(f"Report saved: {report_file}")
    return report_file


def run(config=None):
    """Start the market analyzer bot loop."""
    global _running, _status
    _running = True
    _ensure_dirs()

    if config is None:
        config = {v: s["default"] for v, s in BOT_INFO["config_schema"].items()}

    _status = {"state": "running", "reports_generated": 0, "last_analysis": None, "errors": []}
    _logger.info("Market Analyzer started.")

    interval = config.get("interval_seconds", 7200)

    while _running:
        try:
            _status["state"] = "analyzing"
            _run_analysis(config)
            _status["last_analysis"] = datetime.now().isoformat()
            _status["state"] = "waiting"
            _logger.info(f"Next analysis in {interval}s...")
        except Exception as e:
            _logger.error(f"Analysis cycle error: {e}")
            _status["errors"].append(str(e))
            _status["state"] = "error"

        for _ in range(interval):
            if not _running:
                break
            time.sleep(1)

    _status["state"] = "stopped"
    _logger.info("Market Analyzer stopped.")


def stop():
    global _running
    _running = False
    _status["state"] = "stopping"


def get_status():
    return {**_status}


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        stop()
