"""
Web Monitor Bot
Monitors websites for changes (price drops, new listings, content updates).
Compares snapshots over time and alerts via email or webhook when changes detected.
"""

import sys
import os
import json
import time
import logging
import hashlib
import difflib
import smtplib
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

PLATFORM_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLATFORM_DIR))

import requests
from bs4 import BeautifulSoup

BOT_INFO = {
    "name": "Web Monitor",
    "category": "automation",
    "description": "Monitors websites for changes and sends alerts",
    "icon": "\U0001f441",
    "version": "1.0",
    "author": "Janovum",
    "config_schema": {
        "targets": {"type": "list", "default": []},
        "check_interval_seconds": {"type": "int", "default": 1800},
        "alert_email": {"type": "str", "default": ""},
        "gmail_address": {"type": "str", "default": ""},
        "gmail_app_password": {"type": "str", "default": ""},
        "discord_webhook_url": {"type": "str", "default": ""},
        "change_threshold_percent": {"type": "float", "default": 5.0},
        "save_snapshots": {"type": "bool", "default": True},
    }
}

# Target format:
# {
#   "url": "https://example.com",
#   "name": "Example Site",
#   "selector": "div.price",   (optional CSS selector to watch specific element)
#   "check_type": "text" | "hash" | "price",
#   "alert_on": "any_change" | "price_drop" | "new_content",
# }

_running = False
_status = {"state": "stopped", "checks_done": 0, "changes_found": 0, "last_check": None, "errors": []}
_logger = logging.getLogger("WebMonitor")
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    _logger.addHandler(logging.StreamHandler())

DATA_DIR = PLATFORM_DIR / "data" / "bots" / "web_monitor"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
CHANGES_LOG = DATA_DIR / "changes_log.json"
TARGETS_FILE = DATA_DIR / "targets.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}


def _ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def _load_targets(config_targets):
    """Load monitoring targets from config or file."""
    if config_targets:
        return config_targets

    if TARGETS_FILE.exists():
        try:
            return json.loads(TARGETS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Default example targets
    defaults = [
        {
            "url": "https://news.ycombinator.com",
            "name": "Hacker News",
            "selector": "",
            "check_type": "hash",
            "alert_on": "any_change",
        }
    ]
    TARGETS_FILE.write_text(json.dumps(defaults, indent=2), encoding="utf-8")
    return defaults


def _load_changes_log():
    if CHANGES_LOG.exists():
        try:
            return json.loads(CHANGES_LOG.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_changes_log(log):
    CHANGES_LOG.write_text(json.dumps(log, indent=2, default=str), encoding="utf-8")


def _url_to_filename(url):
    """Convert URL to a safe filename."""
    return hashlib.md5(url.encode()).hexdigest()


def _fetch_content(url, selector=""):
    """Fetch a webpage and optionally extract content from a CSS selector."""
    resp = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove script/style elements
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    if selector:
        elements = soup.select(selector)
        if elements:
            text = "\n".join(el.get_text(strip=True) for el in elements)
        else:
            text = soup.get_text(separator="\n", strip=True)
    else:
        text = soup.get_text(separator="\n", strip=True)

    # Clean up whitespace
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    clean_text = "\n".join(lines)

    return clean_text


def _load_snapshot(url):
    """Load the last snapshot for a URL."""
    fname = _url_to_filename(url)
    snap_file = SNAPSHOTS_DIR / f"{fname}.json"
    if snap_file.exists():
        try:
            return json.loads(snap_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def _save_snapshot(url, content, content_hash):
    """Save a snapshot."""
    fname = _url_to_filename(url)
    snap_file = SNAPSHOTS_DIR / f"{fname}.json"
    data = {
        "url": url,
        "content": content[:50000],  # Limit size
        "hash": content_hash,
        "timestamp": datetime.now().isoformat(),
    }
    snap_file.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _compute_diff(old_text, new_text):
    """Compute a readable diff between old and new content."""
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()

    diff = difflib.unified_diff(old_lines, new_lines, lineterm="", n=2)
    diff_text = "\n".join(list(diff)[:100])  # Limit diff size
    return diff_text


def _extract_price(text):
    """Extract a numeric price from text."""
    import re
    match = re.search(r'\$[\d,]+\.?\d*', text)
    if match:
        price_str = match.group(0).replace("$", "").replace(",", "")
        try:
            return float(price_str)
        except ValueError:
            pass
    return None


def _calculate_change_percent(old_text, new_text):
    """Calculate how different two texts are as a percentage."""
    if not old_text and not new_text:
        return 0.0
    if not old_text or not new_text:
        return 100.0

    matcher = difflib.SequenceMatcher(None, old_text, new_text)
    similarity = matcher.ratio()
    return (1.0 - similarity) * 100.0


def _send_alert_email(subject, body, config):
    """Send an alert email."""
    alert_email = config.get("alert_email", "")
    gmail_addr = config.get("gmail_address") or os.environ.get("GMAIL_ADDRESS", "")
    gmail_pass = config.get("gmail_app_password") or os.environ.get("GMAIL_APP_PASSWORD", "")

    if not alert_email or not gmail_addr or not gmail_pass:
        _logger.warning("Email alert not configured. Skipping.")
        return

    try:
        msg = MIMEMultipart()
        msg["From"] = f"Web Monitor <{gmail_addr}>"
        msg["To"] = alert_email
        msg["Subject"] = f"[Web Monitor] {subject}"
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(gmail_addr, gmail_pass)
            server.send_message(msg)

        _logger.info(f"Alert email sent to {alert_email}")
    except Exception as e:
        _logger.error(f"Failed to send alert email: {e}")


def _send_alert_webhook(message, config):
    """Send alert to Discord webhook."""
    webhook_url = config.get("discord_webhook_url", "")
    if not webhook_url:
        return

    try:
        resp = requests.post(webhook_url, json={"content": message[:2000]}, timeout=15)
        if resp.status_code in (200, 204):
            _logger.info("Alert sent to Discord webhook")
        else:
            _logger.error(f"Webhook alert failed: {resp.status_code}")
    except Exception as e:
        _logger.error(f"Webhook error: {e}")


def _check_target(target, config):
    """Check a single target for changes."""
    url = target.get("url", "")
    name = target.get("name", url)
    selector = target.get("selector", "")
    check_type = target.get("check_type", "hash")
    alert_on = target.get("alert_on", "any_change")
    threshold = config.get("change_threshold_percent", 5.0)

    _logger.info(f"Checking: {name} ({url})")

    try:
        new_content = _fetch_content(url, selector)
        new_hash = hashlib.md5(new_content.encode()).hexdigest()

        old_snapshot = _load_snapshot(url)

        # Save new snapshot
        if config.get("save_snapshots", True):
            _save_snapshot(url, new_content, new_hash)

        if old_snapshot is None:
            _logger.info(f"  First snapshot saved for {name}")
            return None  # No comparison possible on first run

        old_content = old_snapshot.get("content", "")
        old_hash = old_snapshot.get("hash", "")

        # Check for changes based on type
        changed = False
        change_info = {}

        if check_type == "hash":
            if new_hash != old_hash:
                changed = True
                change_percent = _calculate_change_percent(old_content, new_content)
                change_info = {"type": "hash_change", "change_percent": round(change_percent, 1)}
                if change_percent < threshold:
                    _logger.info(f"  Minor change ({change_percent:.1f}%) below threshold ({threshold}%)")
                    changed = False

        elif check_type == "text":
            change_percent = _calculate_change_percent(old_content, new_content)
            if change_percent >= threshold:
                changed = True
                diff = _compute_diff(old_content, new_content)
                change_info = {"type": "text_change", "change_percent": round(change_percent, 1), "diff_preview": diff[:500]}

        elif check_type == "price":
            old_price = _extract_price(old_content)
            new_price = _extract_price(new_content)
            if old_price and new_price and old_price != new_price:
                if alert_on == "price_drop" and new_price < old_price:
                    changed = True
                    change_info = {"type": "price_drop", "old_price": old_price, "new_price": new_price, "drop_percent": round(((old_price - new_price) / old_price) * 100, 1)}
                elif alert_on != "price_drop":
                    changed = True
                    change_info = {"type": "price_change", "old_price": old_price, "new_price": new_price}

        if changed:
            _logger.info(f"  CHANGE DETECTED: {change_info}")
            _status["changes_found"] += 1

            # Send alerts
            alert_subject = f"Change detected: {name}"
            alert_body = (
                f"Website change detected!\n\n"
                f"Target: {name}\n"
                f"URL: {url}\n"
                f"Time: {datetime.now().isoformat()}\n"
                f"Change: {json.dumps(change_info, indent=2)}\n"
            )

            _send_alert_email(alert_subject, alert_body, config)
            _send_alert_webhook(f"**{alert_subject}**\n{url}\n{json.dumps(change_info)}", config)

            return {
                "target": name,
                "url": url,
                "change": change_info,
                "detected_at": datetime.now().isoformat(),
            }
        else:
            _logger.info(f"  No significant changes for {name}")

    except Exception as e:
        _logger.error(f"  Error checking {name}: {e}")
        _status["errors"].append(f"{name}: {str(e)}")

    return None


def _run_checks(config):
    """Run one monitoring cycle across all targets."""
    global _status

    targets = _load_targets(config.get("targets", []))
    if not targets:
        _logger.info("No targets configured. Add targets to targets.json")
        return

    changes_log = _load_changes_log()
    new_changes = []

    for target in targets:
        if not _running:
            break

        _status["checks_done"] += 1
        change = _check_target(target, config)
        if change:
            new_changes.append(change)
            changes_log.append(change)

        time.sleep(2)  # Polite delay between checks

    _save_changes_log(changes_log)

    if new_changes:
        _logger.info(f"Detected {len(new_changes)} changes this cycle")
    return new_changes


def run(config=None):
    """Start the web monitor bot loop."""
    global _running, _status
    _running = True
    _ensure_dirs()

    if config is None:
        config = {v: s["default"] for v, s in BOT_INFO["config_schema"].items()}

    _status = {"state": "running", "checks_done": 0, "changes_found": 0, "last_check": None, "errors": []}
    _logger.info("Web Monitor started.")

    interval = config.get("check_interval_seconds", 1800)

    while _running:
        try:
            _status["state"] = "checking"
            _run_checks(config)
            _status["last_check"] = datetime.now().isoformat()
            _status["state"] = "waiting"
            _logger.info(f"Next check in {interval}s...")
        except Exception as e:
            _logger.error(f"Monitor cycle error: {e}")
            _status["errors"].append(str(e))
            _status["state"] = "error"

        for _ in range(interval):
            if not _running:
                break
            time.sleep(1)

    _status["state"] = "stopped"
    _logger.info("Web Monitor stopped.")


def stop():
    global _running
    _running = False
    _status["state"] = "stopping"


def get_status():
    return {**_status}


# ── Helper to add targets at runtime ──

def add_target(url, name="", selector="", check_type="hash", alert_on="any_change"):
    """Add a monitoring target."""
    _ensure_dirs()
    targets = []
    if TARGETS_FILE.exists():
        try:
            targets = json.loads(TARGETS_FILE.read_text(encoding="utf-8"))
        except Exception:
            targets = []

    targets.append({
        "url": url,
        "name": name or url,
        "selector": selector,
        "check_type": check_type,
        "alert_on": alert_on,
    })
    TARGETS_FILE.write_text(json.dumps(targets, indent=2), encoding="utf-8")
    _logger.info(f"Added target: {name or url}")


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        stop()
