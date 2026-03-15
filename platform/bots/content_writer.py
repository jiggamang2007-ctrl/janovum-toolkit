"""
AI Content Writer Bot
Generates blog posts, product descriptions, social captions, and more
using Pollinations text API. Saves outputs to files.
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
    from core.api_router import generate_text_free
except ImportError:
    generate_text_free = None

import requests

BOT_INFO = {
    "name": "AI Content Writer",
    "category": "marketing",
    "description": "Generates blog posts, descriptions, and social content with AI",
    "icon": "\u270d\ufe0f",
    "version": "1.0",
    "author": "Janovum",
    "config_schema": {
        "content_queue_file": {"type": "str", "default": ""},
        "interval_seconds": {"type": "int", "default": 600},
        "default_tone": {"type": "str", "default": "professional"},
        "default_language": {"type": "str", "default": "english"},
        "max_items_per_run": {"type": "int", "default": 5},
        "output_format": {"type": "str", "default": "markdown"},
        "auto_generate_titles": {"type": "bool", "default": True},
    }
}

# Content queue entry format:
# {
#   "id": "uuid",
#   "type": "blog_post" | "product_description" | "social_caption" | "email_copy" | "custom",
#   "topic": "The main topic or prompt",
#   "keywords": ["keyword1", "keyword2"],
#   "tone": "professional" | "casual" | "persuasive" | "informative",
#   "word_count": 500,
#   "additional_context": "",
#   "status": "pending" | "generating" | "completed" | "failed",
#   "output_file": "",
# }

_running = False
_status = {"state": "stopped", "items_generated": 0, "last_run": None, "errors": []}
_logger = logging.getLogger("ContentWriter")
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    _logger.addHandler(logging.StreamHandler())

DATA_DIR = PLATFORM_DIR / "data" / "bots" / "content_writer"
OUTPUT_DIR = DATA_DIR / "output"
QUEUE_FILE = DATA_DIR / "content_queue.json"


def _ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _load_queue(queue_file=""):
    qf = Path(queue_file) if queue_file else QUEUE_FILE
    if qf.exists():
        try:
            return json.loads(qf.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_queue(queue, queue_file=""):
    qf = Path(queue_file) if queue_file else QUEUE_FILE
    _ensure_dirs()
    qf.write_text(json.dumps(queue, indent=2, default=str), encoding="utf-8")


def _call_pollinations(prompt):
    """Call Pollinations text API."""
    try:
        if generate_text_free:
            result = generate_text_free(prompt)
            return result.get("text", "").strip()
        else:
            encoded = urllib.parse.quote(prompt)
            url = f"https://text.pollinations.ai/{encoded}"
            resp = requests.get(url, headers={"User-Agent": "Janovum/1.0"}, timeout=90)
            if resp.status_code == 200:
                return resp.text.strip()
    except Exception as e:
        _logger.error(f"Pollinations API error: {e}")
    return None


def _generate_blog_post(item, config):
    """Generate a blog post."""
    topic = item.get("topic", "")
    keywords = item.get("keywords", [])
    tone = item.get("tone", config.get("default_tone", "professional"))
    word_count = item.get("word_count", 800)
    context = item.get("additional_context", "")

    prompt = (
        f"Write a {word_count}-word blog post about: {topic}. "
        f"Tone: {tone}. "
        f"{'Keywords to include: ' + ', '.join(keywords) + '. ' if keywords else ''}"
        f"{'Additional context: ' + context + '. ' if context else ''}"
        f"Include an introduction, 3-4 main sections with subheadings, and a conclusion. "
        f"Write in {config.get('default_language', 'english')}. "
        f"Make it engaging and informative."
    )

    return _call_pollinations(prompt)


def _generate_product_description(item, config):
    """Generate a product description."""
    topic = item.get("topic", "")
    keywords = item.get("keywords", [])
    tone = item.get("tone", "persuasive")
    word_count = item.get("word_count", 200)
    context = item.get("additional_context", "")

    prompt = (
        f"Write a {word_count}-word product description for: {topic}. "
        f"Tone: {tone}. "
        f"{'Features to highlight: ' + ', '.join(keywords) + '. ' if keywords else ''}"
        f"{'Details: ' + context + '. ' if context else ''}"
        f"Include key benefits, features, and a compelling call-to-action. "
        f"Write in {config.get('default_language', 'english')}."
    )

    return _call_pollinations(prompt)


def _generate_social_caption(item, config):
    """Generate social media captions."""
    topic = item.get("topic", "")
    keywords = item.get("keywords", [])
    tone = item.get("tone", "casual")
    context = item.get("additional_context", "")

    prompt = (
        f"Write 5 different social media captions for: {topic}. "
        f"Tone: {tone}. "
        f"{'Hashtags to include: ' + ', '.join(keywords) + '. ' if keywords else ''}"
        f"{'Context: ' + context + '. ' if context else ''}"
        f"Each caption should be under 280 characters. "
        f"Include relevant emojis. Separate each caption with a blank line. "
        f"Format: number followed by the caption text."
    )

    return _call_pollinations(prompt)


def _generate_email_copy(item, config):
    """Generate email marketing copy."""
    topic = item.get("topic", "")
    keywords = item.get("keywords", [])
    tone = item.get("tone", "professional")
    word_count = item.get("word_count", 300)
    context = item.get("additional_context", "")

    prompt = (
        f"Write email marketing copy about: {topic}. "
        f"Tone: {tone}. Length: ~{word_count} words. "
        f"{'Key points: ' + ', '.join(keywords) + '. ' if keywords else ''}"
        f"{'Context: ' + context + '. ' if context else ''}"
        f"Include: a compelling subject line, preview text, main body with clear CTA. "
        f"Format with SUBJECT LINE: and BODY: sections."
    )

    return _call_pollinations(prompt)


def _generate_custom(item, config):
    """Generate custom content from a free-form prompt."""
    topic = item.get("topic", "")
    context = item.get("additional_context", "")
    word_count = item.get("word_count", 500)

    prompt = f"{topic}. {'Context: ' + context + '. ' if context else ''}Target length: ~{word_count} words."

    return _call_pollinations(prompt)


def _generate_title(content_type, topic):
    """Generate a title for the content."""
    prompt = f"Write a single catchy title for a {content_type} about: {topic}. Only the title, no quotes."
    result = _call_pollinations(prompt)
    if result:
        return result.strip().strip('"').strip("'")[:100]
    return topic[:80]


def _save_content(item, content, config):
    """Save generated content to a file."""
    _ensure_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    content_type = item.get("type", "custom")
    topic_slug = item.get("topic", "content")[:40].replace(" ", "_").replace("/", "_")

    fmt = config.get("output_format", "markdown")
    ext = "md" if fmt == "markdown" else "txt"

    filename = f"{content_type}_{topic_slug}_{timestamp}.{ext}"
    filepath = OUTPUT_DIR / filename

    if fmt == "markdown":
        header = f"# {item.get('title', item.get('topic', 'Untitled'))}\n\n"
        header += f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Type: {content_type}*\n\n---\n\n"
        full_content = header + content
    else:
        full_content = content

    filepath.write_text(full_content, encoding="utf-8")
    return str(filepath)


def _process_queue(config):
    """Process pending items in the content queue."""
    global _status

    queue_file = config.get("content_queue_file", "")
    queue = _load_queue(queue_file)

    if not queue:
        _logger.info("Content queue is empty. Add items to content_queue.json")
        return 0

    max_items = config.get("max_items_per_run", 5)
    generated = 0

    generators = {
        "blog_post": _generate_blog_post,
        "product_description": _generate_product_description,
        "social_caption": _generate_social_caption,
        "email_copy": _generate_email_copy,
        "custom": _generate_custom,
    }

    for item in queue:
        if generated >= max_items:
            break
        if not _running:
            break
        if item.get("status") != "pending":
            continue

        content_type = item.get("type", "custom")
        topic = item.get("topic", "")
        _logger.info(f"Generating {content_type}: {topic[:50]}...")

        item["status"] = "generating"

        try:
            # Generate title if enabled
            if config.get("auto_generate_titles", True) and "title" not in item:
                item["title"] = _generate_title(content_type, topic)

            # Generate content
            generator = generators.get(content_type, _generate_custom)
            content = generator(item, config)

            if content:
                filepath = _save_content(item, content, config)
                item["status"] = "completed"
                item["output_file"] = filepath
                item["completed_at"] = datetime.now().isoformat()
                item["word_count_actual"] = len(content.split())

                _status["items_generated"] += 1
                generated += 1
                _logger.info(f"  Saved: {filepath} ({item['word_count_actual']} words)")
            else:
                item["status"] = "failed"
                item["error"] = "AI generation returned empty result"
                _logger.error(f"  Failed: empty result for '{topic}'")

            time.sleep(3)  # Rate limit

        except Exception as e:
            item["status"] = "failed"
            item["error"] = str(e)
            _logger.error(f"  Generation error: {e}")
            _status["errors"].append(str(e))

    _save_queue(queue, queue_file)
    return generated


def run(config=None):
    """Start the content writer bot loop."""
    global _running, _status
    _running = True
    _ensure_dirs()

    if config is None:
        config = {v: s["default"] for v, s in BOT_INFO["config_schema"].items()}

    _status = {"state": "running", "items_generated": 0, "last_run": None, "errors": []}
    _logger.info("AI Content Writer started.")

    interval = config.get("interval_seconds", 600)

    while _running:
        try:
            _status["state"] = "generating"
            count = _process_queue(config)
            _status["last_run"] = datetime.now().isoformat()
            _status["state"] = "waiting"
            _logger.info(f"Generated {count} items. Next run in {interval}s...")
        except Exception as e:
            _logger.error(f"Writer cycle error: {e}")
            _status["errors"].append(str(e))
            _status["state"] = "error"

        for _ in range(interval):
            if not _running:
                break
            time.sleep(1)

    _status["state"] = "stopped"
    _logger.info("AI Content Writer stopped.")


def stop():
    global _running
    _running = False
    _status["state"] = "stopping"


def get_status():
    queue = _load_queue() if QUEUE_FILE.exists() else []
    pending = sum(1 for i in queue if i.get("status") == "pending")
    completed = sum(1 for i in queue if i.get("status") == "completed")
    return {**_status, "queue_pending": pending, "queue_completed": completed, "queue_total": len(queue)}


# ── Helpers to add items at runtime ──

def add_to_queue(topic, content_type="blog_post", keywords=None, tone="professional",
                 word_count=500, additional_context=""):
    """Add a content item to the generation queue."""
    import uuid
    _ensure_dirs()
    queue = _load_queue()
    item = {
        "id": str(uuid.uuid4())[:8],
        "type": content_type,
        "topic": topic,
        "keywords": keywords or [],
        "tone": tone,
        "word_count": word_count,
        "additional_context": additional_context,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
    }
    queue.append(item)
    _save_queue(queue)
    _logger.info(f"Added to queue: {content_type} - {topic}")
    return item


def generate_now(topic, content_type="blog_post", **kwargs):
    """Generate content immediately without the queue/loop."""
    _ensure_dirs()
    config = {v: s["default"] for v, s in BOT_INFO["config_schema"].items()}
    config.update(kwargs)

    item = {
        "type": content_type,
        "topic": topic,
        "keywords": kwargs.get("keywords", []),
        "tone": kwargs.get("tone", "professional"),
        "word_count": kwargs.get("word_count", 500),
        "additional_context": kwargs.get("additional_context", ""),
    }

    generators = {
        "blog_post": _generate_blog_post,
        "product_description": _generate_product_description,
        "social_caption": _generate_social_caption,
        "email_copy": _generate_email_copy,
        "custom": _generate_custom,
    }

    generator = generators.get(content_type, _generate_custom)
    content = generator(item, config)

    if content:
        filepath = _save_content(item, content, config)
        return {"content": content, "file": filepath}
    return None


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        stop()
