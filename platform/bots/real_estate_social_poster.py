"""
Real Estate Social Media Poster Bot
Takes property listings and generates social media posts with AI images
(Pollinations.ai) and captions. Posts to Discord/Telegram webhooks or saves for manual posting.
"""

import sys
import os
import json
import time
import logging
import urllib.parse
from pathlib import Path
from datetime import datetime

PLATFORM_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLATFORM_DIR))

try:
    from core.api_router import generate_text_free, generate_image
except ImportError:
    generate_text_free = None
    generate_image = None

import requests

BOT_INFO = {
    "name": "Social Media Poster",
    "category": "real_estate",
    "description": "Creates social media posts with AI images for property listings",
    "icon": "\U0001f4f1",
    "version": "1.0",
    "author": "Janovum",
    "config_schema": {
        "leads_file": {"type": "str", "default": ""},
        "interval_seconds": {"type": "int", "default": 3600},
        "max_posts_per_run": {"type": "int", "default": 5},
        "discord_webhook_url": {"type": "str", "default": ""},
        "telegram_bot_token": {"type": "str", "default": ""},
        "telegram_chat_id": {"type": "str", "default": ""},
        "image_width": {"type": "int", "default": 1024},
        "image_height": {"type": "int", "default": 1024},
        "auto_post": {"type": "bool", "default": False},
        "platforms": {"type": "list", "default": ["save_local"]},
    }
}

_running = False
_status = {"state": "stopped", "posts_created": 0, "last_run": None, "errors": []}
_logger = logging.getLogger("SocialPoster")
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    _logger.addHandler(logging.StreamHandler())

DATA_DIR = PLATFORM_DIR / "data" / "bots" / "real_estate_social_poster"
POSTS_DIR = DATA_DIR / "posts"
IMAGES_DIR = DATA_DIR / "images"
POSTED_LOG = DATA_DIR / "posted_log.json"
DEFAULT_LEADS_FILE = PLATFORM_DIR / "data" / "bots" / "real_estate_lead_scraper" / "leads.json"


def _ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def _load_leads(leads_file):
    lf = Path(leads_file) if leads_file else DEFAULT_LEADS_FILE
    if lf.exists():
        try:
            return json.loads(lf.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _load_posted_log():
    if POSTED_LOG.exists():
        try:
            return json.loads(POSTED_LOG.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_posted_log(log):
    POSTED_LOG.write_text(json.dumps(log, indent=2, default=str), encoding="utf-8")


def _generate_caption(lead):
    """Generate a social media caption for a listing using AI."""
    prompt = (
        f"Write a short, engaging social media post for a real estate listing. "
        f"Include relevant emojis. Max 200 characters. Do not use hashtags more than 3. "
        f"Property: {lead.get('title', 'Amazing property')}. "
        f"Price: {lead.get('price', 'Contact for price')}. "
        f"Location: {lead.get('city', '')}. "
        f"Bedrooms: {lead.get('bedrooms', 'N/A')}."
    )

    try:
        if generate_text_free:
            result = generate_text_free(prompt)
            text = result.get("text", "").strip()
            # Trim to social-media length
            if len(text) > 280:
                text = text[:277] + "..."
            return text
        else:
            encoded = urllib.parse.quote(prompt)
            url = f"https://text.pollinations.ai/{encoded}"
            resp = requests.get(url, headers={"User-Agent": "Janovum/1.0"}, timeout=60)
            if resp.status_code == 200:
                text = resp.text.strip()
                if len(text) > 280:
                    text = text[:277] + "..."
                return text
    except Exception as e:
        _logger.error(f"Caption generation failed: {e}")

    # Fallback
    price = lead.get("price", "")
    city = lead.get("city", "")
    return f"Check out this property in {city}! {price} - {lead.get('title', 'Great listing')} #RealEstate #HomeForSale"


def _generate_listing_image(lead, width=1024, height=1024):
    """Generate an AI image for the listing using Pollinations."""
    city = lead.get("city", "modern city")
    price = lead.get("price", "")
    bedrooms = lead.get("bedrooms", "")

    prompt = (
        f"Professional real estate photography of a beautiful "
        f"{''+bedrooms+' bedroom ' if bedrooms else ''}"
        f"home in {city}, exterior view, golden hour lighting, "
        f"well-maintained lawn, inviting entrance, high quality, 4K, photorealistic"
    )

    try:
        if generate_image:
            result = generate_image(prompt, width=width, height=height)
            return result.get("image_data")
        else:
            encoded = urllib.parse.quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&nologo=true"
            resp = requests.get(url, headers={"User-Agent": "Janovum/1.0"}, timeout=90)
            if resp.status_code == 200 and len(resp.content) > 1000:
                return resp.content
    except Exception as e:
        _logger.error(f"Image generation failed: {e}")

    return None


def _post_to_discord(webhook_url, caption, image_path=None):
    """Post to a Discord webhook."""
    if not webhook_url:
        return False

    try:
        if image_path and Path(image_path).exists():
            with open(image_path, "rb") as f:
                files = {"file": ("listing.png", f, "image/png")}
                data = {"content": caption}
                resp = requests.post(webhook_url, data=data, files=files, timeout=30)
        else:
            resp = requests.post(webhook_url, json={"content": caption}, timeout=15)

        if resp.status_code in (200, 204):
            _logger.info("Posted to Discord successfully")
            return True
        else:
            _logger.error(f"Discord post failed: {resp.status_code}")
    except Exception as e:
        _logger.error(f"Discord post error: {e}")

    return False


def _post_to_telegram(bot_token, chat_id, caption, image_path=None):
    """Post to a Telegram channel/group."""
    if not bot_token or not chat_id:
        return False

    try:
        if image_path and Path(image_path).exists():
            url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
            with open(image_path, "rb") as f:
                files = {"photo": f}
                data = {"chat_id": chat_id, "caption": caption}
                resp = requests.post(url, data=data, files=files, timeout=30)
        else:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            resp = requests.post(url, json={"chat_id": chat_id, "text": caption}, timeout=15)

        if resp.status_code == 200:
            _logger.info("Posted to Telegram successfully")
            return True
        else:
            _logger.error(f"Telegram post failed: {resp.status_code} {resp.text}")
    except Exception as e:
        _logger.error(f"Telegram post error: {e}")

    return False


def _create_posts(config):
    """Generate and optionally post social media content for new leads."""
    global _status

    leads_file = config.get("leads_file", "")
    leads = _load_leads(leads_file)
    posted_log = _load_posted_log()
    posted_ids = {entry["lead_id"] for entry in posted_log}

    max_posts = config.get("max_posts_per_run", 5)
    auto_post = config.get("auto_post", False)
    posts_created = 0

    for lead in leads:
        if posts_created >= max_posts:
            break

        lead_id = lead.get("id", "")
        if lead_id in posted_ids:
            continue

        try:
            _logger.info(f"Creating post for: {lead.get('title', 'listing')}")

            # Generate caption
            caption = _generate_caption(lead)

            # Generate image
            img_data = _generate_listing_image(
                lead,
                width=config.get("image_width", 1024),
                height=config.get("image_height", 1024)
            )

            image_path = None
            if img_data:
                image_path = str(IMAGES_DIR / f"{lead_id[:12]}.png")
                Path(image_path).write_bytes(img_data)
                _logger.info(f"Image saved: {image_path}")

            # Save post locally
            post_data = {
                "lead_id": lead_id,
                "caption": caption,
                "image_path": image_path,
                "listing_url": lead.get("url", ""),
                "created_at": datetime.now().isoformat(),
                "posted_to": [],
            }

            post_file = POSTS_DIR / f"post_{lead_id[:12]}.json"
            post_file.write_text(json.dumps(post_data, indent=2), encoding="utf-8")

            # Auto-post if enabled
            if auto_post:
                platforms = config.get("platforms", ["save_local"])

                if "discord" in platforms and config.get("discord_webhook_url"):
                    if _post_to_discord(config["discord_webhook_url"], caption, image_path):
                        post_data["posted_to"].append("discord")

                if "telegram" in platforms and config.get("telegram_bot_token"):
                    if _post_to_telegram(config["telegram_bot_token"], config.get("telegram_chat_id", ""), caption, image_path):
                        post_data["posted_to"].append("telegram")

            # Log
            posted_log.append({
                "lead_id": lead_id,
                "caption": caption[:100],
                "image_path": image_path,
                "posted_to": post_data["posted_to"],
                "created_at": datetime.now().isoformat(),
            })

            posts_created += 1
            _status["posts_created"] += 1

            time.sleep(3)  # Be polite to APIs

        except Exception as e:
            _logger.error(f"Error creating post for {lead_id}: {e}")
            _status["errors"].append(str(e))

    _save_posted_log(posted_log)
    return posts_created


def run(config=None):
    """Start the social poster bot loop."""
    global _running, _status
    _running = True
    _ensure_dirs()

    if config is None:
        config = {v: s["default"] for v, s in BOT_INFO["config_schema"].items()}

    _status = {"state": "running", "posts_created": 0, "last_run": None, "errors": []}
    _logger.info("Social Media Poster started.")

    interval = config.get("interval_seconds", 3600)

    while _running:
        try:
            _status["state"] = "generating"
            count = _create_posts(config)
            _status["last_run"] = datetime.now().isoformat()
            _status["state"] = "waiting"
            _logger.info(f"Created {count} posts. Next run in {interval}s...")
        except Exception as e:
            _logger.error(f"Poster cycle error: {e}")
            _status["errors"].append(str(e))
            _status["state"] = "error"

        for _ in range(interval):
            if not _running:
                break
            time.sleep(1)

    _status["state"] = "stopped"
    _logger.info("Social Media Poster stopped.")


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
