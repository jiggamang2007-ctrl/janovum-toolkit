"""
Janovum Platform — Human-in-the-Loop Approval System
Agents must get approval before taking sensitive actions.
A feature OpenClaw DOESN'T have — this makes Janovum safer.

How it works:
  1. Agent wants to take an action (send email, spend money, post publicly)
  2. System checks if that action requires approval
  3. If yes, creates an approval request and pauses the agent
  4. Human approves/denies via dashboard or Telegram/Discord
  5. Agent continues or aborts based on the decision
"""

import json
import time
import uuid
import threading
from datetime import datetime
from pathlib import Path
from enum import Enum

PLATFORM_DIR = Path(__file__).parent.parent
APPROVALS_DIR = PLATFORM_DIR / "data" / "approvals"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    AUTO_APPROVED = "auto_approved"


class ApprovalPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Actions that ALWAYS require approval
DEFAULT_SENSITIVE_ACTIONS = {
    "send_email": ApprovalPriority.MEDIUM,
    "send_sms": ApprovalPriority.MEDIUM,
    "post_social_media": ApprovalPriority.HIGH,
    "make_payment": ApprovalPriority.CRITICAL,
    "delete_file": ApprovalPriority.HIGH,
    "modify_client_data": ApprovalPriority.MEDIUM,
    "api_key_change": ApprovalPriority.CRITICAL,
    "deploy_agent": ApprovalPriority.MEDIUM,
    "execute_code": ApprovalPriority.HIGH,
    "web_form_submit": ApprovalPriority.MEDIUM,
}


class ApprovalRequest:
    def __init__(self, agent_id, action, description, priority=ApprovalPriority.MEDIUM,
                 client_id=None, metadata=None, timeout_seconds=3600):
        self.id = f"apr_{int(time.time())}_{str(uuid.uuid4())[:6]}"
        self.agent_id = agent_id
        self.client_id = client_id
        self.action = action
        self.description = description
        self.priority = priority
        self.metadata = metadata or {}
        self.status = ApprovalStatus.PENDING
        self.created_at = datetime.now().isoformat()
        self.decided_at = None
        self.decided_by = None
        self.reason = None
        self.timeout_seconds = timeout_seconds
        self.expires_at = time.time() + timeout_seconds
        self._event = threading.Event()

    def approve(self, decided_by="dashboard", reason=None):
        self.status = ApprovalStatus.APPROVED
        self.decided_at = datetime.now().isoformat()
        self.decided_by = decided_by
        self.reason = reason
        self._event.set()

    def deny(self, decided_by="dashboard", reason=None):
        self.status = ApprovalStatus.DENIED
        self.decided_at = datetime.now().isoformat()
        self.decided_by = decided_by
        self.reason = reason
        self._event.set()

    def wait(self, timeout=None):
        """Block until a decision is made. Returns the status."""
        timeout = timeout or self.timeout_seconds
        self._event.wait(timeout=timeout)
        if self.status == ApprovalStatus.PENDING:
            self.status = ApprovalStatus.EXPIRED
        return self.status

    def is_expired(self):
        return time.time() > self.expires_at and self.status == ApprovalStatus.PENDING

    def to_dict(self):
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "client_id": self.client_id,
            "action": self.action,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "created_at": self.created_at,
            "decided_at": self.decided_at,
            "decided_by": self.decided_by,
            "reason": self.reason,
            "expires_at": self.expires_at,
            "is_expired": self.is_expired(),
            "metadata": self.metadata
        }


class ApprovalManager:
    def __init__(self):
        APPROVALS_DIR.mkdir(parents=True, exist_ok=True)
        self.pending = {}  # request_id -> ApprovalRequest
        self.history = []  # completed requests (last 200)
        self.rules = dict(DEFAULT_SENSITIVE_ACTIONS)
        self.auto_approve_rules = {}  # action -> conditions for auto-approval
        self.callbacks = []  # notify when new approval needed
        self._lock = threading.Lock()

    def request_approval(self, agent_id, action, description, client_id=None,
                         metadata=None, priority=None, blocking=False, timeout=3600):
        """
        Request approval for an action.
        If blocking=True, waits for decision before returning.
        Returns (ApprovalRequest, status)
        """
        if priority is None:
            priority = self.rules.get(action, ApprovalPriority.MEDIUM)

        # Check auto-approve rules
        if action in self.auto_approve_rules:
            req = ApprovalRequest(agent_id, action, description, priority, client_id, metadata)
            req.status = ApprovalStatus.AUTO_APPROVED
            req.decided_at = datetime.now().isoformat()
            req.decided_by = "auto_rule"
            self.history.append(req)
            return req, ApprovalStatus.AUTO_APPROVED

        # Check if action requires approval
        if action not in self.rules:
            req = ApprovalRequest(agent_id, action, description, priority, client_id, metadata)
            req.status = ApprovalStatus.AUTO_APPROVED
            req.decided_at = datetime.now().isoformat()
            req.decided_by = "not_restricted"
            return req, ApprovalStatus.AUTO_APPROVED

        with self._lock:
            req = ApprovalRequest(agent_id, action, description, priority, client_id, metadata, timeout)
            self.pending[req.id] = req
            self._notify_new_approval(req)

        if blocking:
            status = req.wait(timeout)
            with self._lock:
                if req.id in self.pending:
                    del self.pending[req.id]
                self.history.append(req)
                if len(self.history) > 200:
                    self.history = self.history[-200:]
            return req, status

        return req, ApprovalStatus.PENDING

    def approve(self, request_id, decided_by="dashboard", reason=None):
        with self._lock:
            req = self.pending.get(request_id)
            if req:
                req.approve(decided_by, reason)
                del self.pending[request_id]
                self.history.append(req)
                return True
        return False

    def deny(self, request_id, decided_by="dashboard", reason=None):
        with self._lock:
            req = self.pending.get(request_id)
            if req:
                req.deny(decided_by, reason)
                del self.pending[request_id]
                self.history.append(req)
                return True
        return False

    def get_pending(self, agent_id=None, client_id=None):
        self._cleanup_expired()
        requests = list(self.pending.values())
        if agent_id:
            requests = [r for r in requests if r.agent_id == agent_id]
        if client_id:
            requests = [r for r in requests if r.client_id == client_id]
        return sorted(requests, key=lambda r: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(r.priority, 2))

    def get_history(self, limit=50):
        return [r.to_dict() for r in self.history[-limit:]]

    def add_sensitive_action(self, action, priority=ApprovalPriority.MEDIUM):
        self.rules[action] = priority

    def remove_sensitive_action(self, action):
        self.rules.pop(action, None)

    def set_auto_approve(self, action, conditions=None):
        self.auto_approve_rules[action] = conditions or {}

    def on_new_approval(self, callback):
        self.callbacks.append(callback)

    def get_rules(self):
        return {
            "sensitive_actions": {k: v for k, v in self.rules.items()},
            "auto_approve": list(self.auto_approve_rules.keys()),
            "pending_count": len(self.pending)
        }

    def _cleanup_expired(self):
        with self._lock:
            expired = [rid for rid, req in self.pending.items() if req.is_expired()]
            for rid in expired:
                req = self.pending.pop(rid)
                req.status = ApprovalStatus.EXPIRED
                self.history.append(req)

    def _notify_new_approval(self, req):
        for cb in self.callbacks:
            try:
                cb(req)
            except Exception:
                pass


_manager = None
def get_approval_manager():
    global _manager
    if _manager is None:
        _manager = ApprovalManager()
    return _manager
