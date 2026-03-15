"""
Janovum Platform — Director Agent
The brain of the platform. Receives messages (from Telegram, webhooks, chat),
analyzes what the user wants, and routes tasks to the right bot/agent.

Flow:
  1. Message comes in (Telegram, webhook, API)
  2. Director analyzes it with AI (cheapest model first)
  3. Determines which bot/agent should handle it
  4. Sends the task to that bot
  5. Reports back the result

The Director knows about ALL bots in the library and ALL agents in the registry.
"""

import os
import sys
import json
import time
import threading
from datetime import datetime

PLATFORM_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOTS_DIR = os.path.join(PLATFORM_DIR, "bots")
sys.path.insert(0, PLATFORM_DIR)

# Bot routing map — keywords that map to bot IDs
BOT_ROUTING = {
    "real_estate_lead_scraper": {
        "keywords": ["scrape", "find listings", "search properties", "find homes", "find houses", "real estate leads", "property search"],
        "description": "Scrapes real estate listings from free sources"
    },
    "real_estate_auto_responder": {
        "keywords": ["respond to lead", "email lead", "reply to", "follow up", "auto respond", "contact lead"],
        "description": "Auto-responds to real estate leads via email"
    },
    "real_estate_market_analyzer": {
        "keywords": ["analyze market", "market report", "price analysis", "market data", "property values", "comps"],
        "description": "Analyzes property market data"
    },
    "real_estate_social_poster": {
        "keywords": ["post listing", "social media", "instagram", "facebook post", "create post", "share listing"],
        "description": "Creates social media posts for property listings"
    },
    "lead_hunter": {
        "keywords": ["find leads", "hunt leads", "business leads", "find contacts", "prospect", "find clients"],
        "description": "Finds business leads from web searches"
    },
    "email_campaign_bot": {
        "keywords": ["send emails", "email campaign", "mass email", "newsletter", "email blast", "outreach"],
        "description": "Sends AI-personalized email campaigns"
    },
    "web_monitor": {
        "keywords": ["monitor website", "watch page", "track changes", "price alert", "notify when"],
        "description": "Monitors websites for changes"
    },
    "task_scheduler_bot": {
        "keywords": ["schedule", "run at", "every hour", "every day", "cron", "recurring"],
        "description": "Schedules and runs tasks on timers"
    },
    "content_writer": {
        "keywords": ["write content", "blog post", "article", "description", "write about", "generate text"],
        "description": "Generates content with AI"
    },
    "discord_assistant": {
        "keywords": ["discord", "discord bot", "respond in discord"],
        "description": "AI assistant for Discord channels"
    },
}

# Direct commands the director handles itself
DIRECTOR_COMMANDS = {
    "status": "Get platform status",
    "list bots": "List all available bots",
    "help": "Show what I can do",
    "stop all": "Stop all running bots",
}


class Director:
    """The Director agent — routes messages to the right bot."""

    def __init__(self):
        self.log = []
        self.running_bots = {}  # bot_id -> {"started": timestamp, "config": {}}
        self._lock = threading.Lock()

    def process_message(self, message, source="telegram", metadata=None):
        """
        Process an incoming message and route it.
        Returns a response dict: {response, action, bot_id, details}
        """
        message = message.strip()
        if not message:
            return {"response": "Empty message received.", "action": "ignored"}

        entry = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "message": message[:200],
            "metadata": metadata
        }

        # Check for direct commands first
        msg_lower = message.lower().strip()

        if msg_lower in ("status", "/status", "what's running", "whats running"):
            response = self._handle_status()
            entry["action"] = "status"
            entry["response"] = response
            self.log.append(entry)
            return {"response": response, "action": "status"}

        if msg_lower in ("list bots", "/bots", "show bots", "what bots"):
            response = self._handle_list_bots()
            entry["action"] = "list_bots"
            entry["response"] = response
            self.log.append(entry)
            return {"response": response, "action": "list_bots"}

        if msg_lower in ("help", "/help", "what can you do"):
            response = self._handle_help()
            entry["action"] = "help"
            entry["response"] = response
            self.log.append(entry)
            return {"response": response, "action": "help"}

        if msg_lower.startswith(("stop all", "/stopall")):
            response = self._handle_stop_all()
            entry["action"] = "stop_all"
            entry["response"] = response
            self.log.append(entry)
            return {"response": response, "action": "stop_all"}

        # Check for explicit bot commands: "start <bot_name>" / "stop <bot_name>"
        if msg_lower.startswith(("start ", "run ", "/start ")):
            bot_name = message.split(None, 1)[1].strip() if len(message.split(None, 1)) > 1 else ""
            return self._handle_start_bot(bot_name, entry)

        if msg_lower.startswith(("stop ", "/stop ")):
            bot_name = message.split(None, 1)[1].strip() if len(message.split(None, 1)) > 1 else ""
            return self._handle_stop_bot(bot_name, entry)

        # AI routing — figure out what the user wants
        bot_id, confidence = self._route_message(message)

        if bot_id and confidence > 0.5:
            response = self._handle_start_bot(bot_id, entry, auto=True)
            response["confidence"] = confidence
            return response

        # If we can't route, use AI to respond directly
        response = self._ai_respond(message)
        entry["action"] = "ai_response"
        entry["response"] = response[:200]
        self.log.append(entry)
        return {"response": response, "action": "ai_response"}

    def _route_message(self, message):
        """Use keyword matching to find the best bot for this message."""
        msg_lower = message.lower()
        best_bot = None
        best_score = 0

        for bot_id, info in BOT_ROUTING.items():
            score = 0
            for keyword in info["keywords"]:
                if keyword in msg_lower:
                    # Longer keywords = more specific = higher score
                    score += len(keyword.split())
            if score > best_score:
                best_score = score
                best_bot = bot_id

        # Normalize confidence (max possible score ~3-4 words matched)
        confidence = min(best_score / 3.0, 1.0)
        return best_bot, confidence

    def _handle_status(self):
        """Get platform status."""
        running = []
        for bot_id, info in self.running_bots.items():
            running.append(f"  - {bot_id} (since {info.get('started', '?')})")

        if running:
            return "Running bots:\n" + "\n".join(running)
        return "No bots currently running. Send a message to start one, or say 'list bots' to see what's available."

    def _handle_list_bots(self):
        """List all available bots."""
        lines = ["Available bots:\n"]
        for bot_id, info in BOT_ROUTING.items():
            name = bot_id.replace("_", " ").title()
            status = "RUNNING" if bot_id in self.running_bots else "stopped"
            lines.append(f"  [{status}] {name} — {info['description']}")
        lines.append("\nSay 'start <bot name>' to run one.")
        return "\n".join(lines)

    def _handle_help(self):
        return """I'm the Janovum Director. I route your messages to the right bot.

You can:
  - Send a task and I'll figure out which bot handles it
  - "start lead scraper" — start a specific bot
  - "stop lead scraper" — stop a bot
  - "status" — see what's running
  - "list bots" — see all available bots
  - "stop all" — stop everything
  - Or just describe what you need and I'll handle it!

Categories: Real Estate, Sales, Marketing, Automation, Messaging"""

    def _handle_stop_all(self):
        """Stop all running bots."""
        stopped = []
        for bot_id in list(self.running_bots.keys()):
            self._stop_bot(bot_id)
            stopped.append(bot_id)
        if stopped:
            return f"Stopped {len(stopped)} bots: {', '.join(stopped)}"
        return "No bots were running."

    def _handle_start_bot(self, bot_name, entry, auto=False):
        """Start a bot by name or ID."""
        bot_id = self._resolve_bot_name(bot_name)
        if not bot_id:
            entry["action"] = "bot_not_found"
            self.log.append(entry)
            return {"response": f"Bot '{bot_name}' not found. Say 'list bots' to see options.", "action": "not_found"}

        success = self._start_bot(bot_id)
        if success:
            action = "auto_started" if auto else "started"
            response = f"Started {bot_id.replace('_', ' ').title()}."
            if auto:
                response = f"I matched your request to the {bot_id.replace('_', ' ').title()} bot and started it."
        else:
            action = "already_running"
            response = f"{bot_id.replace('_', ' ').title()} is already running."

        entry["action"] = action
        entry["bot_id"] = bot_id
        entry["response"] = response
        self.log.append(entry)
        return {"response": response, "action": action, "bot_id": bot_id}

    def _handle_stop_bot(self, bot_name, entry):
        """Stop a bot by name or ID."""
        bot_id = self._resolve_bot_name(bot_name)
        if not bot_id:
            entry["action"] = "bot_not_found"
            self.log.append(entry)
            return {"response": f"Bot '{bot_name}' not found.", "action": "not_found"}

        success = self._stop_bot(bot_id)
        response = f"Stopped {bot_id.replace('_', ' ').title()}." if success else f"{bot_id.replace('_', ' ').title()} wasn't running."
        entry["action"] = "stopped" if success else "not_running"
        entry["bot_id"] = bot_id
        self.log.append(entry)
        return {"response": response, "action": entry["action"], "bot_id": bot_id}

    def _resolve_bot_name(self, name):
        """Fuzzy-match a bot name to a bot ID."""
        name_lower = name.lower().replace(" ", "_").replace("-", "_")

        # Exact match
        if name_lower in BOT_ROUTING:
            return name_lower

        # Partial match
        for bot_id in BOT_ROUTING:
            if name_lower in bot_id or bot_id in name_lower:
                return bot_id

        # Keyword match
        for bot_id, info in BOT_ROUTING.items():
            for kw in info["keywords"]:
                if name_lower in kw or kw in name_lower:
                    return bot_id

        return None

    def _start_bot(self, bot_id):
        """Actually start a bot via the server API."""
        with self._lock:
            if bot_id in self.running_bots:
                return False

            try:
                import importlib.util
                bot_file = os.path.join(BOTS_DIR, f"{bot_id}.py")
                if not os.path.exists(bot_file):
                    return False

                spec = importlib.util.spec_from_file_location(f"bots.{bot_id}", bot_file)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)

                # Load saved config
                config = {}
                config_path = os.path.join(PLATFORM_DIR, "data", "bots", bot_id, "config.json")
                if os.path.exists(config_path):
                    with open(config_path) as f:
                        config = json.load(f)

                def run():
                    try:
                        mod.run(config)
                    except Exception as e:
                        print(f"[director] Bot {bot_id} error: {e}")

                t = threading.Thread(target=run, daemon=True, name=f"director-{bot_id}")
                t.start()

                self.running_bots[bot_id] = {
                    "thread": t,
                    "module": mod,
                    "started": datetime.now().isoformat(),
                    "config": config
                }
                return True
            except Exception as e:
                print(f"[director] Failed to start {bot_id}: {e}")
                return False

    def _stop_bot(self, bot_id):
        """Stop a running bot."""
        with self._lock:
            if bot_id not in self.running_bots:
                return False
            info = self.running_bots[bot_id]
            mod = info.get("module")
            if mod:
                try:
                    mod.stop()
                except Exception:
                    pass
            del self.running_bots[bot_id]
            return True

    def _ai_respond(self, message):
        """Use AI to respond when we can't route to a specific bot."""
        try:
            # Try local Claude Code auth first (free with subscription)
            creds_path = os.path.expanduser("~/.claude/.credentials.json")
            if os.path.exists(creds_path):
                with open(creds_path) as f:
                    creds = json.load(f)
                token = creds.get("claudeAiOauth", {}).get("accessToken")
                if token:
                    import requests
                    resp = requests.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={
                            "Authorization": f"Bearer {token}",
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json"
                        },
                        json={
                            "model": "claude-haiku-4-5-20251001",
                            "max_tokens": 500,
                            "system": "You are the Janovum Director — a concise AI assistant. Keep responses under 3 sentences. You manage bots for real estate, sales, marketing, and automation.",
                            "messages": [{"role": "user", "content": message}]
                        },
                        timeout=30
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for block in data.get("content", []):
                            if block.get("type") == "text":
                                return block["text"]
        except Exception:
            pass

        # Fallback to Pollinations (free, no key)
        try:
            import requests
            resp = requests.get(
                f"https://text.pollinations.ai/{message[:200]}",
                params={"model": "openai", "seed": 42},
                timeout=30
            )
            if resp.status_code == 200:
                return resp.text[:500]
        except Exception:
            pass

        return "I received your message but couldn't process it right now. Try a specific command like 'start lead scraper' or 'list bots'."

    def get_log(self, limit=50):
        return self.log[-limit:]

    def get_dashboard(self):
        return {
            "running_bots": list(self.running_bots.keys()),
            "running_count": len(self.running_bots),
            "total_messages": len(self.log),
            "last_message": self.log[-1] if self.log else None
        }


# ── SINGLETON ──
_director = None

def get_director():
    global _director
    if _director is None:
        _director = Director()
    return _director
