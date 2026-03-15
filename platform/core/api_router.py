"""
Janovum Platform — Auto-API Router
Automatically routes to the cheapest/free API for any capability.
This is Janovum's secret weapon — full AI agent capabilities at $0/month.

How it works:
  1. Each capability (image_gen, tts, stt, llm, search, etc.) has multiple providers
  2. Providers are ranked by cost (free first, then cheapest paid)
  3. When a capability is requested, try the cheapest provider first
  4. If it fails, automatically fall back to the next cheapest
  5. Track which providers are working/broken to avoid repeated failures

No API keys needed for the free tier providers!
"""

import os
import json
import time
import hashlib
import requests
import threading
from datetime import datetime
from pathlib import Path

PLATFORM_DIR = Path(__file__).parent.parent
ROUTER_STATE_FILE = PLATFORM_DIR / "data" / "api_router_state.json"


class ProviderStatus:
    ACTIVE = "active"
    COOLDOWN = "cooldown"
    DISABLED = "disabled"


class Provider:
    """A single API provider for a capability."""

    def __init__(self, name, capability, cost_per_1k, call_fn, daily_limit=None, requires_key=False, key_env=None):
        self.name = name
        self.capability = capability
        self.cost_per_1k = cost_per_1k  # cost per 1000 requests, 0 = free
        self.call_fn = call_fn
        self.daily_limit = daily_limit
        self.requires_key = requires_key
        self.key_env = key_env

        # Runtime state
        self.status = ProviderStatus.ACTIVE
        self.calls_today = 0
        self.total_calls = 0
        self.total_failures = 0
        self.last_call = None
        self.last_failure = None
        self.cooldown_until = None
        self.avg_latency_ms = 0
        self._latency_samples = []

    def is_available(self):
        """Check if this provider can handle a request right now."""
        if self.status == ProviderStatus.DISABLED:
            return False
        if self.status == ProviderStatus.COOLDOWN:
            if self.cooldown_until and time.time() > self.cooldown_until:
                self.status = ProviderStatus.ACTIVE
            else:
                return False
        if self.requires_key and self.key_env:
            if not os.environ.get(self.key_env):
                return False
        if self.daily_limit and self.calls_today >= self.daily_limit:
            return False
        return True

    def record_success(self, latency_ms):
        self.total_calls += 1
        self.calls_today += 1
        self.last_call = time.time()
        self._latency_samples.append(latency_ms)
        if len(self._latency_samples) > 20:
            self._latency_samples = self._latency_samples[-20:]
        self.avg_latency_ms = sum(self._latency_samples) / len(self._latency_samples)

    def record_failure(self):
        self.total_failures += 1
        self.last_failure = time.time()
        # Exponential cooldown: 1min, 5min, 25min, 1hr max
        consecutive = min(self.total_failures, 4)
        cooldown_seconds = [60, 300, 1500, 3600][consecutive - 1]
        self.cooldown_until = time.time() + cooldown_seconds
        self.status = ProviderStatus.COOLDOWN

    def to_dict(self):
        return {
            "name": self.name,
            "capability": self.capability,
            "cost_per_1k": self.cost_per_1k,
            "status": self.status,
            "calls_today": self.calls_today,
            "total_calls": self.total_calls,
            "total_failures": self.total_failures,
            "avg_latency_ms": round(self.avg_latency_ms),
            "daily_limit": self.daily_limit,
            "requires_key": self.requires_key,
            "is_available": self.is_available()
        }


# ══════════════════════════════════════════
# FREE API IMPLEMENTATIONS
# ══════════════════════════════════════════

def _pollinations_image(prompt, width=512, height=512, **kwargs):
    """Pollinations.ai — 100% free, no API key, unlimited."""
    import urllib.parse
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&nologo=true"
    resp = requests.get(url, headers={"User-Agent": "Janovum/1.0"}, timeout=60)
    if resp.status_code == 200 and len(resp.content) > 1000:
        return {"image_data": resp.content, "format": "png", "provider": "pollinations"}
    raise Exception(f"Pollinations error: {resp.status_code}")


def _pollinations_text(prompt, model="openai", **kwargs):
    """Pollinations.ai text generation — free, no API key."""
    import urllib.parse
    encoded = urllib.parse.quote(prompt)
    url = f"https://text.pollinations.ai/{encoded}?model={model}"
    resp = requests.get(url, headers={"User-Agent": "Janovum/1.0"}, timeout=60)
    if resp.status_code == 200:
        return {"text": resp.text, "provider": "pollinations_text"}
    raise Exception(f"Pollinations text error: {resp.status_code}")


def _duckduckgo_search(query, max_results=10, **kwargs):
    """DuckDuckGo search — free, no API key."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return {"results": results, "provider": "duckduckgo", "count": len(results)}
    except ImportError:
        # Fallback: use the HTML search
        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Janovum/1.0"},
            timeout=15
        )
        # Basic parsing of results
        return {"results": [{"title": "Install duckduckgo-search for better results", "body": resp.text[:500]}], "provider": "duckduckgo_html"}


def _edge_tts(text, voice="en-US-AriaNeural", output_path=None, **kwargs):
    """Microsoft Edge TTS — free, unlimited, 400+ voices, no API key."""
    try:
        import asyncio
        import edge_tts

        if output_path is None:
            output_path = str(PLATFORM_DIR / "data" / "tts_output.mp3")

        async def _generate():
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)

        # Run async in sync context
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    pool.submit(asyncio.run, _generate()).result()
            else:
                loop.run_until_complete(_generate())
        except RuntimeError:
            asyncio.run(_generate())

        return {"audio_path": output_path, "provider": "edge_tts", "voice": voice}
    except ImportError:
        raise Exception("edge-tts not installed. Run: pip install edge-tts")


def _open_meteo_weather(latitude, longitude, **kwargs):
    """Open-Meteo — free weather API, no key needed."""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true&hourly=temperature_2m,precipitation"
    resp = requests.get(url, timeout=15)
    if resp.status_code == 200:
        return {"weather": resp.json(), "provider": "open_meteo"}
    raise Exception(f"Open-Meteo error: {resp.status_code}")


def _wttr_weather(location, **kwargs):
    """wttr.in — free weather, no API key, simple."""
    resp = requests.get(f"https://wttr.in/{location}?format=j1", headers={"User-Agent": "Janovum/1.0"}, timeout=15)
    if resp.status_code == 200:
        return {"weather": resp.json(), "provider": "wttr"}
    raise Exception(f"wttr.in error: {resp.status_code}")


def _google_news_rss(query=None, **kwargs):
    """Google News RSS — free, unlimited, no API key."""
    import xml.etree.ElementTree as ET
    if query:
        import urllib.parse
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-US&gl=US&ceid=US:en"
    else:
        url = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"

    resp = requests.get(url, timeout=15)
    if resp.status_code == 200:
        root = ET.fromstring(resp.content)
        items = []
        for item in root.findall(".//item")[:20]:
            items.append({
                "title": item.findtext("title", ""),
                "link": item.findtext("link", ""),
                "pubDate": item.findtext("pubDate", ""),
                "source": item.findtext("source", "")
            })
        return {"articles": items, "provider": "google_news_rss", "count": len(items)}
    raise Exception(f"Google News RSS error: {resp.status_code}")


def _mymemory_translate(text, source_lang="en", target_lang="es", **kwargs):
    """MyMemory Translation — free, 5000 chars/day, no API key."""
    url = f"https://api.mymemory.translated.net/get?q={requests.utils.quote(text)}&langpair={source_lang}|{target_lang}"
    resp = requests.get(url, timeout=15)
    if resp.status_code == 200:
        data = resp.json()
        translated = data.get("responseData", {}).get("translatedText", "")
        return {"translated_text": translated, "provider": "mymemory", "source": source_lang, "target": target_lang}
    raise Exception(f"MyMemory error: {resp.status_code}")


def _gmail_send(to, subject, body, from_email=None, app_password=None, **kwargs):
    """Send email via Gmail SMTP — free, 500/day."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    sender = from_email or os.environ.get("GMAIL_ADDRESS", "")
    password = app_password or os.environ.get("GMAIL_APP_PASSWORD", "")
    if not sender or not password:
        raise Exception("Gmail credentials not configured. Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD env vars.")

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)

    return {"status": "sent", "provider": "gmail", "to": to}


def _telegram_send(chat_id, message, bot_token=None, **kwargs):
    """Send message via Telegram Bot — free, unlimited."""
    token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise Exception("Telegram bot token not configured.")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, timeout=15)
    if resp.status_code == 200:
        return {"status": "sent", "provider": "telegram"}
    raise Exception(f"Telegram error: {resp.status_code} — {resp.text}")


def _discord_webhook(webhook_url, message, **kwargs):
    """Send message via Discord webhook — free, unlimited."""
    resp = requests.post(webhook_url, json={"content": message}, timeout=15)
    if resp.status_code in (200, 204):
        return {"status": "sent", "provider": "discord_webhook"}
    raise Exception(f"Discord webhook error: {resp.status_code}")


# ══════════════════════════════════════════
# THE ROUTER
# ══════════════════════════════════════════

class APIRouter:
    """
    The Auto-API Router. Routes requests to the cheapest available provider.
    Tracks failures and auto-falls-back to alternatives.
    """

    def __init__(self):
        self.providers = {}  # capability -> [Provider, ...] sorted by cost
        self._lock = threading.Lock()
        self._daily_reset_time = None
        self._setup_default_providers()
        self._load_state()

    def _setup_default_providers(self):
        """Register all default free/cheap providers."""

        # ── IMAGE GENERATION ──
        self._register(Provider("pollinations", "image_gen", 0, _pollinations_image))

        # ── TEXT GENERATION (non-Claude) ──
        self._register(Provider("pollinations_text", "text_gen_free", 0, _pollinations_text))

        # ── WEB SEARCH ──
        self._register(Provider("duckduckgo", "web_search", 0, _duckduckgo_search))

        # ── TEXT TO SPEECH ──
        self._register(Provider("edge_tts", "tts", 0, _edge_tts))

        # ── WEATHER ──
        self._register(Provider("open_meteo", "weather", 0, _open_meteo_weather))
        self._register(Provider("wttr", "weather", 0, _wttr_weather))

        # ── NEWS ──
        self._register(Provider("google_news_rss", "news", 0, _google_news_rss))

        # ── TRANSLATION ──
        self._register(Provider("mymemory", "translation", 0, _mymemory_translate, daily_limit=5000))

        # ── EMAIL ──
        self._register(Provider("gmail", "email", 0, _gmail_send, daily_limit=500, requires_key=True, key_env="GMAIL_APP_PASSWORD"))

        # ── MESSAGING ──
        self._register(Provider("telegram", "messaging", 0, _telegram_send, requires_key=True, key_env="TELEGRAM_BOT_TOKEN"))
        self._register(Provider("discord_webhook", "messaging", 0, _discord_webhook))

    def _register(self, provider):
        """Register a provider, keeping the list sorted by cost."""
        cap = provider.capability
        if cap not in self.providers:
            self.providers[cap] = []
        self.providers[cap].append(provider)
        self.providers[cap].sort(key=lambda p: p.cost_per_1k)

    def add_provider(self, provider):
        """Add a custom provider at runtime."""
        with self._lock:
            self._register(provider)

    def route(self, capability, **kwargs):
        """
        Route a request to the cheapest available provider.
        Automatically falls back on failure.

        Returns dict with result + provider info, or raises if all fail.
        """
        self._check_daily_reset()

        providers = self.providers.get(capability, [])
        if not providers:
            raise Exception(f"No providers registered for capability: {capability}")

        errors = []
        for provider in providers:
            if not provider.is_available():
                continue

            try:
                start = time.time()
                result = provider.call_fn(**kwargs)
                latency = (time.time() - start) * 1000
                provider.record_success(latency)

                if isinstance(result, dict):
                    result["_routed_via"] = provider.name
                    result["_latency_ms"] = round(latency)
                    result["_cost"] = provider.cost_per_1k

                self._save_state()
                return result

            except Exception as e:
                provider.record_failure()
                errors.append(f"{provider.name}: {str(e)}")
                continue

        self._save_state()
        raise Exception(f"All providers failed for {capability}: {'; '.join(errors)}")

    def get_providers(self, capability=None):
        """Get provider info, optionally filtered by capability."""
        with self._lock:
            if capability:
                return [p.to_dict() for p in self.providers.get(capability, [])]
            result = {}
            for cap, providers in self.providers.items():
                result[cap] = [p.to_dict() for p in providers]
            return result

    def get_capabilities(self):
        """List all available capabilities."""
        return list(self.providers.keys())

    def get_stats(self):
        """Get overall routing statistics."""
        total_calls = 0
        total_failures = 0
        by_capability = {}

        for cap, providers in self.providers.items():
            cap_calls = sum(p.total_calls for p in providers)
            cap_failures = sum(p.total_failures for p in providers)
            free_calls = sum(p.total_calls for p in providers if p.cost_per_1k == 0)

            total_calls += cap_calls
            total_failures += cap_failures

            by_capability[cap] = {
                "total_calls": cap_calls,
                "failures": cap_failures,
                "free_calls": free_calls,
                "providers_available": sum(1 for p in providers if p.is_available()),
                "providers_total": len(providers)
            }

        return {
            "total_calls": total_calls,
            "total_failures": total_failures,
            "free_percentage": round((sum(p.total_calls for ps in self.providers.values() for p in ps if p.cost_per_1k == 0) / max(total_calls, 1)) * 100, 1),
            "capabilities": by_capability,
            "estimated_cost_saved": f"${total_calls * 0.002:.2f}"  # rough estimate vs paid APIs
        }

    def _check_daily_reset(self):
        """Reset daily call counters at midnight."""
        today = datetime.now().date()
        if self._daily_reset_time != today:
            for providers in self.providers.values():
                for p in providers:
                    p.calls_today = 0
            self._daily_reset_time = today

    def _save_state(self):
        """Save provider state to disk."""
        try:
            ROUTER_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            state = {}
            for cap, providers in self.providers.items():
                state[cap] = {}
                for p in providers:
                    state[cap][p.name] = {
                        "total_calls": p.total_calls,
                        "total_failures": p.total_failures,
                        "calls_today": p.calls_today,
                        "avg_latency_ms": round(p.avg_latency_ms)
                    }
            ROUTER_STATE_FILE.write_text(json.dumps(state, indent=2))
        except Exception:
            pass

    def _load_state(self):
        """Load provider state from disk."""
        try:
            if ROUTER_STATE_FILE.exists():
                state = json.loads(ROUTER_STATE_FILE.read_text())
                for cap, providers_state in state.items():
                    for p in self.providers.get(cap, []):
                        if p.name in providers_state:
                            s = providers_state[p.name]
                            p.total_calls = s.get("total_calls", 0)
                            p.total_failures = s.get("total_failures", 0)
        except Exception:
            pass


# ── SINGLETON ──
_router = None

def get_router():
    """Get the global API router instance."""
    global _router
    if _router is None:
        _router = APIRouter()
    return _router


# ── CONVENIENCE FUNCTIONS ──

def generate_image(prompt, width=512, height=512):
    """Generate an image using the cheapest available provider."""
    return get_router().route("image_gen", prompt=prompt, width=width, height=height)

def search_web(query, max_results=10):
    """Search the web using the cheapest available provider."""
    return get_router().route("web_search", query=query, max_results=max_results)

def text_to_speech(text, voice="en-US-AriaNeural", output_path=None):
    """Convert text to speech using the cheapest available provider."""
    return get_router().route("tts", text=text, voice=voice, output_path=output_path)

def get_weather(location=None, latitude=None, longitude=None):
    """Get weather data using the cheapest available provider."""
    if location:
        return get_router().route("weather", location=location)
    return get_router().route("weather", latitude=latitude, longitude=longitude)

def get_news(query=None):
    """Get news using the cheapest available provider."""
    return get_router().route("news", query=query)

def translate(text, source_lang="en", target_lang="es"):
    """Translate text using the cheapest available provider."""
    return get_router().route("translation", text=text, source_lang=source_lang, target_lang=target_lang)

def send_email(to, subject, body):
    """Send email using the cheapest available provider."""
    return get_router().route("email", to=to, subject=subject, body=body)

def send_message(chat_id=None, message="", webhook_url=None, bot_token=None):
    """Send a message using the cheapest available provider."""
    if webhook_url:
        return get_router().route("messaging", webhook_url=webhook_url, message=message)
    return get_router().route("messaging", chat_id=chat_id, message=message, bot_token=bot_token)

def generate_text_free(prompt):
    """Generate text using free (non-Claude) providers."""
    return get_router().route("text_gen_free", prompt=prompt)
