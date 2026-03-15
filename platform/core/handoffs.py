"""
Janovum Platform — Agent Handoff System
Seamless delegation between specialized agents.
Agent A says "this needs a browser expert" -> system routes to browser agent automatically.

Like CrewAI/OpenAI SDK handoffs but simpler and more flexible.
"""

import json
import time
import uuid
import threading
from datetime import datetime
from pathlib import Path
from enum import Enum

PLATFORM_DIR = Path(__file__).parent.parent


class HandoffStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class HandoffRequest:
    """A request to hand off work from one agent to another."""

    def __init__(self, from_agent_id, to_agent_id=None, to_agent_type=None,
                 task_description="", context=None, priority="medium", client_id=None):
        self.id = f"hoff_{int(time.time())}_{str(uuid.uuid4())[:6]}"
        self.from_agent_id = from_agent_id
        self.to_agent_id = to_agent_id  # specific agent, or None for type-based routing
        self.to_agent_type = to_agent_type  # route to any agent of this type
        self.task_description = task_description
        self.context = context or {}
        self.priority = priority
        self.client_id = client_id
        self.status = HandoffStatus.PENDING
        self.created_at = datetime.now().isoformat()
        self.accepted_at = None
        self.completed_at = None
        self.result = None
        self.error = None
        self._event = threading.Event()

    def accept(self, agent_id):
        self.to_agent_id = agent_id
        self.status = HandoffStatus.ACCEPTED
        self.accepted_at = datetime.now().isoformat()

    def start(self):
        self.status = HandoffStatus.IN_PROGRESS

    def complete(self, result):
        self.status = HandoffStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now().isoformat()
        self._event.set()

    def fail(self, error):
        self.status = HandoffStatus.FAILED
        self.error = str(error)
        self.completed_at = datetime.now().isoformat()
        self._event.set()

    def reject(self, reason=""):
        self.status = HandoffStatus.REJECTED
        self.error = reason
        self._event.set()

    def wait(self, timeout=300):
        self._event.wait(timeout=timeout)
        return self.status

    def to_dict(self):
        return {
            "id": self.id,
            "from_agent_id": self.from_agent_id,
            "to_agent_id": self.to_agent_id,
            "to_agent_type": self.to_agent_type,
            "task_description": self.task_description,
            "context": self.context,
            "priority": self.priority,
            "client_id": self.client_id,
            "status": self.status,
            "created_at": self.created_at,
            "accepted_at": self.accepted_at,
            "completed_at": self.completed_at,
            "result": str(self.result)[:500] if self.result else None,
            "error": self.error
        }


class HandoffRouter:
    """Routes handoff requests to the right agent."""

    def __init__(self):
        self.pending_handoffs = {}  # handoff_id -> HandoffRequest
        self.completed_handoffs = []
        self.routing_rules = {}  # agent_type -> [capability_keywords]
        self._lock = threading.Lock()
        self._setup_default_routes()

    def _setup_default_routes(self):
        self.routing_rules = {
            "browser": ["browse", "scrape", "website", "navigate", "screenshot", "web page", "click"],
            "email": ["email", "inbox", "send mail", "reply", "draft", "smtp", "imap"],
            "messaging": ["message", "telegram", "discord", "slack", "chat", "notify", "alert"],
            "search": ["search", "find", "look up", "research", "google", "scan"],
            "lead_gen": ["lead", "prospect", "contact", "outreach", "pipeline", "sales"],
            "scheduler": ["schedule", "cron", "timer", "recurring", "interval", "daily"],
            "custom": []
        }

    def request_handoff(self, from_agent_id, task_description, context=None,
                        to_agent_id=None, to_agent_type=None, priority="medium",
                        client_id=None, blocking=False):
        """
        Request a handoff. If to_agent_type is not specified, auto-detect from task description.
        """
        if not to_agent_id and not to_agent_type:
            to_agent_type = self._auto_route(task_description)

        handoff = HandoffRequest(
            from_agent_id, to_agent_id, to_agent_type,
            task_description, context, priority, client_id
        )

        with self._lock:
            self.pending_handoffs[handoff.id] = handoff

        # Try to find and assign a target agent
        self._try_assign(handoff)

        if blocking:
            status = handoff.wait(timeout=300)
            with self._lock:
                if handoff.id in self.pending_handoffs:
                    del self.pending_handoffs[handoff.id]
                self.completed_handoffs.append(handoff)
                if len(self.completed_handoffs) > 200:
                    self.completed_handoffs = self.completed_handoffs[-200:]
            return handoff

        return handoff

    def accept_handoff(self, handoff_id, agent_id):
        with self._lock:
            handoff = self.pending_handoffs.get(handoff_id)
            if handoff:
                handoff.accept(agent_id)
                return True
        return False

    def complete_handoff(self, handoff_id, result):
        with self._lock:
            handoff = self.pending_handoffs.get(handoff_id)
            if handoff:
                handoff.complete(result)
                del self.pending_handoffs[handoff_id]
                self.completed_handoffs.append(handoff)
                return True
        return False

    def fail_handoff(self, handoff_id, error):
        with self._lock:
            handoff = self.pending_handoffs.get(handoff_id)
            if handoff:
                handoff.fail(error)
                del self.pending_handoffs[handoff_id]
                self.completed_handoffs.append(handoff)
                return True
        return False

    def get_pending(self, agent_type=None):
        handoffs = list(self.pending_handoffs.values())
        if agent_type:
            handoffs = [h for h in handoffs if h.to_agent_type == agent_type]
        return [h.to_dict() for h in handoffs]

    def get_history(self, limit=50, agent_id=None):
        handoffs = list(self.completed_handoffs)
        if agent_id:
            handoffs = [h for h in handoffs if h.from_agent_id == agent_id or h.to_agent_id == agent_id]
        return [h.to_dict() for h in handoffs[-limit:]]

    def get_stats(self):
        all_handoffs = self.completed_handoffs
        if not all_handoffs:
            return {"total": 0, "completed": 0, "failed": 0, "pending": len(self.pending_handoffs)}
        return {
            "total": len(all_handoffs),
            "completed": sum(1 for h in all_handoffs if h.status == HandoffStatus.COMPLETED),
            "failed": sum(1 for h in all_handoffs if h.status == HandoffStatus.FAILED),
            "rejected": sum(1 for h in all_handoffs if h.status == HandoffStatus.REJECTED),
            "pending": len(self.pending_handoffs),
            "by_type": self._count_by_type()
        }

    def _auto_route(self, task_description):
        """Auto-detect agent type from task description."""
        desc_lower = task_description.lower()
        best_type = "custom"
        best_score = 0
        for agent_type, keywords in self.routing_rules.items():
            score = sum(1 for kw in keywords if kw in desc_lower)
            if score > best_score:
                best_score = score
                best_type = agent_type
        return best_type

    def _try_assign(self, handoff):
        """Try to assign the handoff to an available agent."""
        try:
            from core.agent_registry import get_registry
            registry = get_registry()
            if handoff.to_agent_id:
                agent = registry.get_agent(handoff.to_agent_id)
                if agent:
                    handoff.accept(agent.id)
                    return
            if handoff.to_agent_type:
                agents = registry.get_all_agents(
                    client_id=handoff.client_id,
                    agent_type=handoff.to_agent_type,
                    state="running"
                )
                if agents:
                    handoff.accept(agents[0].id)
                    return
                agents = registry.get_all_agents(
                    client_id=handoff.client_id,
                    agent_type=handoff.to_agent_type,
                    state="idle"
                )
                if agents:
                    handoff.accept(agents[0].id)
        except Exception:
            pass

    def _count_by_type(self):
        counts = {}
        for h in self.completed_handoffs:
            t = h.to_agent_type or "direct"
            counts[t] = counts.get(t, 0) + 1
        return counts


_router = None
def get_handoff_router():
    global _router
    if _router is None:
        _router = HandoffRouter()
    return _router
