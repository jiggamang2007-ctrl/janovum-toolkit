"""
Janovum Platform — Agent Registry
Central registry for all agents in the platform.
Manages agent lifecycle, capabilities, inter-agent communication, and the agent marketplace.

Features OpenClaw doesn't have:
  - Self-building: agents can register new tools/capabilities at runtime
  - Agent marketplace: pre-built agent templates ready to deploy
  - Agent-to-agent messaging with typed channels
  - Per-client agent isolation
"""

import json
import os
import time
import uuid
import threading
from datetime import datetime
from pathlib import Path
from enum import Enum

PLATFORM_DIR = Path(__file__).parent.parent
REGISTRY_FILE = PLATFORM_DIR / "data" / "agent_registry.json"
MARKETPLACE_DIR = PLATFORM_DIR / "marketplace"


class AgentState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


class AgentType(str, Enum):
    BROWSER = "browser"
    EMAIL = "email"
    MESSAGING = "messaging"
    SEARCH = "search"
    LEAD_GEN = "lead_gen"
    SCHEDULER = "scheduler"
    CUSTOM = "custom"


class Agent:
    """Represents a single agent instance in the platform."""

    def __init__(self, agent_id, name, agent_type, client_id=None, skill_name=None, config=None):
        self.id = agent_id
        self.name = name
        self.type = agent_type
        self.client_id = client_id
        self.skill_name = skill_name
        self.config = config or {}

        self.state = AgentState.IDLE
        self.created_at = datetime.now().isoformat()
        self.started_at = None
        self.last_activity = None
        self.error_message = None

        # Capabilities — what this agent can do
        self.capabilities = set()
        # Tools — specific tools this agent has access to
        self.tools = {}
        # Messages — inbox for inter-agent communication
        self.inbox = []
        self.outbox = []

        # Runtime stats
        self.total_actions = 0
        self.total_errors = 0
        self.total_messages_sent = 0
        self.total_messages_received = 0

    def add_capability(self, capability_name):
        """Add a capability to this agent."""
        self.capabilities.add(capability_name)

    def add_tool(self, tool_name, tool_fn, description=""):
        """Self-building: agent registers a new tool at runtime."""
        self.tools[tool_name] = {
            "fn": tool_fn,
            "description": description,
            "added_at": datetime.now().isoformat(),
            "call_count": 0
        }

    def send_message(self, to_agent_id, message, message_type="text"):
        """Send a message to another agent."""
        msg = {
            "id": str(uuid.uuid4())[:8],
            "from": self.id,
            "to": to_agent_id,
            "type": message_type,
            "content": message,
            "timestamp": datetime.now().isoformat()
        }
        self.outbox.append(msg)
        self.total_messages_sent += 1
        return msg

    def receive_message(self, message):
        """Receive a message from another agent."""
        self.inbox.append(message)
        self.total_messages_received += 1

    def get_messages(self, unread_only=True):
        """Get messages from inbox."""
        if unread_only:
            messages = [m for m in self.inbox if not m.get("read")]
            for m in messages:
                m["read"] = True
            return messages
        return list(self.inbox)

    def record_action(self, action_description=""):
        """Record that the agent took an action."""
        self.total_actions += 1
        self.last_activity = datetime.now().isoformat()

    def record_error(self, error_message):
        """Record an error."""
        self.total_errors += 1
        self.error_message = error_message
        if self.total_errors >= 5 and self.state == AgentState.RUNNING:
            self.state = AgentState.ERROR

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "client_id": self.client_id,
            "skill_name": self.skill_name,
            "config": self.config,
            "state": self.state,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "last_activity": self.last_activity,
            "error_message": self.error_message,
            "capabilities": list(self.capabilities),
            "tools": {k: {"description": v["description"], "call_count": v["call_count"]} for k, v in self.tools.items()},
            "stats": {
                "total_actions": self.total_actions,
                "total_errors": self.total_errors,
                "messages_sent": self.total_messages_sent,
                "messages_received": self.total_messages_received,
                "inbox_size": len(self.inbox),
            }
        }


class AgentTemplate:
    """A pre-built agent template in the marketplace."""

    def __init__(self, template_id, name, description, agent_type, skill_name, default_config=None, capabilities=None, tags=None):
        self.id = template_id
        self.name = name
        self.description = description
        self.type = agent_type
        self.skill_name = skill_name
        self.default_config = default_config or {}
        self.capabilities = capabilities or []
        self.tags = tags or []
        self.deploy_count = 0
        self.rating = 0

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "skill_name": self.skill_name,
            "default_config": self.default_config,
            "capabilities": self.capabilities,
            "tags": self.tags,
            "deploy_count": self.deploy_count,
            "rating": self.rating
        }


class AgentRegistry:
    """
    Central registry for all agents.
    Manages lifecycle, communication, and the marketplace.
    """

    def __init__(self):
        self.agents = {}  # agent_id -> Agent
        self.templates = {}  # template_id -> AgentTemplate
        self._lock = threading.Lock()
        self._message_queue = []
        self._setup_default_templates()
        REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)

    def _setup_default_templates(self):
        """Set up the built-in agent marketplace templates."""
        defaults = [
            AgentTemplate("email_responder", "Email Auto-Responder",
                "Monitors inbox and drafts intelligent responses using AI. Handles inquiries, support tickets, and routine emails.",
                AgentType.EMAIL, "email_responder",
                {"check_interval": 300, "auto_send": False},
                ["email_read", "email_send", "ai_draft"],
                ["email", "automation", "support"]),

            AgentTemplate("lead_hunter", "Lead Hunter",
                "Scans the web for potential leads based on configurable criteria. Scores leads and adds them to your pipeline.",
                AgentType.LEAD_GEN, "lead_responder",
                {"scan_interval": 3600, "platforms": ["google", "linkedin"]},
                ["web_search", "lead_scoring", "crm_update"],
                ["leads", "sales", "prospecting"]),

            AgentTemplate("social_monitor", "Social Media Monitor",
                "Monitors Reddit, Twitter, and forums for mentions of your brand or keywords. Alerts you to opportunities.",
                AgentType.SEARCH, "reddit_agent",
                {"keywords": [], "platforms": ["reddit"], "alert_channel": "telegram"},
                ["web_search", "social_scrape", "alert_send"],
                ["social", "monitoring", "brand"]),

            AgentTemplate("browser_researcher", "Web Researcher",
                "Autonomous browser agent that researches topics, visits websites, extracts data, and compiles reports.",
                AgentType.BROWSER, "browser_agent",
                {"headless": True, "max_pages": 20},
                ["browser_navigate", "page_extract", "report_compile"],
                ["research", "browser", "data"]),

            AgentTemplate("scheduler_bot", "Task Scheduler",
                "Manages recurring tasks and cron jobs. Runs health checks, sends reports, and triggers other agents on schedule.",
                AgentType.SCHEDULER, "scheduler",
                {"timezone": "America/New_York"},
                ["schedule_create", "schedule_manage", "agent_trigger"],
                ["scheduling", "automation", "cron"]),

            AgentTemplate("discord_assistant", "Discord Assistant",
                "AI-powered Discord bot that answers questions, moderates, and provides support in your server.",
                AgentType.MESSAGING, "discord_bot",
                {"prefix": "!", "auto_moderate": False},
                ["discord_send", "discord_read", "ai_respond"],
                ["discord", "chat", "support"]),

            AgentTemplate("telegram_assistant", "Telegram Assistant",
                "AI-powered Telegram bot for client communication, notifications, and task management.",
                AgentType.MESSAGING, "telegram_bot",
                {"parse_mode": "Markdown"},
                ["telegram_send", "telegram_read", "ai_respond"],
                ["telegram", "chat", "notifications"]),

            AgentTemplate("roi_analyzer", "ROI Analyzer",
                "Scans deals, investments, and opportunities to calculate potential ROI. Sends daily reports.",
                AgentType.SEARCH, "roi_scanner",
                {"scan_sources": ["zillow", "realtor"], "min_roi": 15},
                ["web_search", "data_analysis", "report_generate"],
                ["finance", "roi", "analysis"]),

            AgentTemplate("file_organizer", "File Organizer",
                "AI-powered file manager that organizes, renames, and categorizes documents automatically.",
                AgentType.CUSTOM, "file_manager",
                {"watch_dirs": [], "auto_organize": True},
                ["file_read", "file_write", "file_move", "ai_categorize"],
                ["files", "organization", "automation"]),

            AgentTemplate("multi_channel", "Multi-Channel Hub",
                "Central hub that routes messages across WhatsApp, Telegram, Discord, Slack, and email.",
                AgentType.MESSAGING, "multi_channel",
                {"channels": ["telegram", "discord"]},
                ["multi_send", "multi_read", "channel_route"],
                ["messaging", "multi-channel", "hub"]),
        ]

        for template in defaults:
            self.templates[template.id] = template

    # ── AGENT LIFECYCLE ──

    def create_agent(self, name, agent_type, client_id=None, skill_name=None, config=None, from_template=None):
        """Create a new agent instance."""
        with self._lock:
            if from_template and from_template in self.templates:
                template = self.templates[from_template]
                agent_type = agent_type or template.type
                skill_name = skill_name or template.skill_name
                merged_config = dict(template.default_config)
                if config:
                    merged_config.update(config)
                config = merged_config
                template.deploy_count += 1

            agent_id = f"{agent_type}_{int(time.time())}_{str(uuid.uuid4())[:4]}"
            agent = Agent(agent_id, name, agent_type, client_id, skill_name, config)
            self.agents[agent_id] = agent
            self._save_registry()
            return agent

    def start_agent(self, agent_id):
        """Start an agent."""
        with self._lock:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                agent.state = AgentState.RUNNING
                agent.started_at = datetime.now().isoformat()
                self._save_registry()
                return True
            return False

    def stop_agent(self, agent_id):
        """Stop an agent."""
        with self._lock:
            if agent_id in self.agents:
                self.agents[agent_id].state = AgentState.STOPPED
                self._save_registry()
                return True
            return False

    def pause_agent(self, agent_id):
        """Pause an agent."""
        with self._lock:
            if agent_id in self.agents:
                self.agents[agent_id].state = AgentState.PAUSED
                self._save_registry()
                return True
            return False

    def remove_agent(self, agent_id):
        """Remove an agent from the registry."""
        with self._lock:
            if agent_id in self.agents:
                del self.agents[agent_id]
                self._save_registry()
                return True
            return False

    def get_agent(self, agent_id):
        """Get a specific agent."""
        return self.agents.get(agent_id)

    def get_all_agents(self, client_id=None, state=None, agent_type=None):
        """Get all agents, optionally filtered."""
        agents = list(self.agents.values())
        if client_id:
            agents = [a for a in agents if a.client_id == client_id]
        if state:
            agents = [a for a in agents if a.state == state]
        if agent_type:
            agents = [a for a in agents if a.type == agent_type]
        return agents

    def get_dashboard(self):
        """Get a dashboard summary of all agents."""
        agents = list(self.agents.values())
        return {
            "total": len(agents),
            "running": sum(1 for a in agents if a.state == AgentState.RUNNING),
            "idle": sum(1 for a in agents if a.state == AgentState.IDLE),
            "paused": sum(1 for a in agents if a.state == AgentState.PAUSED),
            "error": sum(1 for a in agents if a.state == AgentState.ERROR),
            "stopped": sum(1 for a in agents if a.state == AgentState.STOPPED),
            "agents": [a.to_dict() for a in agents],
            "marketplace_templates": len(self.templates)
        }

    # ── INTER-AGENT COMMUNICATION ──

    def send_message(self, from_agent_id, to_agent_id, message, message_type="text"):
        """Send a message from one agent to another."""
        with self._lock:
            sender = self.agents.get(from_agent_id)
            receiver = self.agents.get(to_agent_id)

            if not sender:
                return None, "Sender agent not found"
            if not receiver:
                return None, "Receiver agent not found"

            msg = sender.send_message(to_agent_id, message, message_type)
            receiver.receive_message(msg)
            return msg, None

    def broadcast(self, from_agent_id, message, message_type="broadcast", filter_type=None, filter_client=None):
        """Broadcast a message to multiple agents."""
        with self._lock:
            sender = self.agents.get(from_agent_id)
            if not sender:
                return 0

            count = 0
            for agent_id, agent in self.agents.items():
                if agent_id == from_agent_id:
                    continue
                if filter_type and agent.type != filter_type:
                    continue
                if filter_client and agent.client_id != filter_client:
                    continue

                msg = sender.send_message(agent_id, message, message_type)
                agent.receive_message(msg)
                count += 1

            return count

    # ── MARKETPLACE ──

    def get_marketplace(self, tag=None, search=None):
        """Browse the agent marketplace."""
        templates = list(self.templates.values())

        if tag:
            templates = [t for t in templates if tag in t.tags]
        if search:
            search_lower = search.lower()
            templates = [t for t in templates if search_lower in t.name.lower() or search_lower in t.description.lower()]

        return [t.to_dict() for t in templates]

    def add_template(self, template):
        """Add a new template to the marketplace."""
        self.templates[template.id] = template

    def deploy_from_marketplace(self, template_id, client_id, name=None, config_overrides=None):
        """Deploy an agent from a marketplace template."""
        template = self.templates.get(template_id)
        if not template:
            return None, f"Template '{template_id}' not found"

        agent_name = name or f"{template.name} ({client_id})"
        agent = self.create_agent(
            name=agent_name,
            agent_type=template.type,
            client_id=client_id,
            skill_name=template.skill_name,
            config=config_overrides,
            from_template=template_id
        )

        for cap in template.capabilities:
            agent.add_capability(cap)

        return agent, None

    # ── PERSISTENCE ──

    def _save_registry(self):
        """Save agent registry to disk."""
        try:
            data = {
                "agents": {aid: a.to_dict() for aid, a in self.agents.items()},
                "saved_at": datetime.now().isoformat()
            }
            REGISTRY_FILE.write_text(json.dumps(data, indent=2))
        except Exception:
            pass

    def _load_registry(self):
        """Load agent registry from disk."""
        try:
            if REGISTRY_FILE.exists():
                data = json.loads(REGISTRY_FILE.read_text())
                # Reconstruct agents from saved state
                for aid, adict in data.get("agents", {}).items():
                    agent = Agent(
                        adict["id"], adict["name"], adict["type"],
                        adict.get("client_id"), adict.get("skill_name"), adict.get("config")
                    )
                    agent.state = adict.get("state", AgentState.STOPPED)
                    agent.created_at = adict.get("created_at")
                    agent.last_activity = adict.get("last_activity")
                    for cap in adict.get("capabilities", []):
                        agent.capabilities.add(cap)
                    self.agents[aid] = agent
        except Exception:
            pass


# ── SINGLETON ──
_registry = None

def get_registry():
    """Get the global agent registry instance."""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
        _registry._load_registry()
    return _registry
