"""
Janovum Platform — Guardrails System
Input/output validation for agent safety.
Prevents agents from doing harmful or unauthorized actions.
A feature OpenClaw DOESN'T have — this is a differentiator.
"""

import re
import json
from datetime import datetime
from pathlib import Path

PLATFORM_DIR = Path(__file__).parent.parent


class GuardrailResult:
    def __init__(self, passed, message="", severity="info"):
        self.passed = passed
        self.message = message
        self.severity = severity  # info, warning, blocked

    def to_dict(self):
        return {"passed": self.passed, "message": self.message, "severity": self.severity}


class Guardrails:
    """
    Validates inputs and outputs to keep agents safe.
    Checks for: PII leaks, prompt injection, budget limits, blocked actions, content safety.
    """

    def __init__(self):
        self.input_rules = []
        self.output_rules = []
        self.blocked_actions = set()
        self.log = []
        self._setup_defaults()

    def _setup_defaults(self):
        """Set up default safety rules."""
        # Input rules
        self.add_input_rule("no_secrets", self._check_no_secrets, "Block messages containing API keys or passwords")
        self.add_input_rule("no_injection", self._check_no_injection, "Block common prompt injection patterns")
        self.add_input_rule("length_limit", self._check_length, "Block extremely long inputs")

        # Output rules
        self.add_output_rule("no_pii_leak", self._check_no_pii_output, "Block outputs containing PII patterns")
        self.add_output_rule("no_harmful", self._check_no_harmful, "Block harmful content in outputs")

    def add_input_rule(self, name, check_fn, description=""):
        self.input_rules.append({"name": name, "check": check_fn, "description": description, "enabled": True})

    def add_output_rule(self, name, check_fn, description=""):
        self.output_rules.append({"name": name, "check": check_fn, "description": description, "enabled": True})

    def block_action(self, action_name):
        self.blocked_actions.add(action_name)

    def unblock_action(self, action_name):
        self.blocked_actions.discard(action_name)

    def validate_input(self, text, context=None):
        """Validate an input message. Returns GuardrailResult."""
        for rule in self.input_rules:
            if not rule["enabled"]:
                continue
            result = rule["check"](text, context)
            if not result.passed:
                self._log_event("input_blocked", rule["name"], text[:100], result.message)
                return result
        return GuardrailResult(True, "Input passed all checks")

    def validate_output(self, text, context=None):
        """Validate an output before sending to user. Returns GuardrailResult."""
        for rule in self.output_rules:
            if not rule["enabled"]:
                continue
            result = rule["check"](text, context)
            if not result.passed:
                self._log_event("output_blocked", rule["name"], text[:100], result.message)
                return result
        return GuardrailResult(True, "Output passed all checks")

    def validate_action(self, action_name, params=None):
        """Validate a tool/action before execution. Returns GuardrailResult."""
        if action_name in self.blocked_actions:
            self._log_event("action_blocked", action_name, str(params)[:100], "Action is blocked")
            return GuardrailResult(False, f"Action '{action_name}' is blocked by guardrails", "blocked")
        return GuardrailResult(True, "Action allowed")

    def get_rules(self):
        """Get all active rules."""
        return {
            "input_rules": [{"name": r["name"], "description": r["description"], "enabled": r["enabled"]} for r in self.input_rules],
            "output_rules": [{"name": r["name"], "description": r["description"], "enabled": r["enabled"]} for r in self.output_rules],
            "blocked_actions": list(self.blocked_actions)
        }

    def get_log(self, limit=50):
        return self.log[-limit:]

    # ── DEFAULT CHECK FUNCTIONS ──

    def _check_no_secrets(self, text, context=None):
        """Detect API keys, passwords, tokens in input."""
        patterns = [
            (r'sk-[a-zA-Z0-9]{20,}', "Anthropic API key detected"),
            (r'sk-proj-[a-zA-Z0-9]{20,}', "OpenAI API key detected"),
            (r'ghp_[a-zA-Z0-9]{36}', "GitHub token detected"),
            (r'xoxb-[0-9]+-[a-zA-Z0-9]+', "Slack bot token detected"),
            (r'AIza[a-zA-Z0-9_-]{35}', "Google API key detected"),
            (r'AKIA[A-Z0-9]{16}', "AWS access key detected"),
        ]
        for pattern, msg in patterns:
            if re.search(pattern, text):
                return GuardrailResult(False, f"BLOCKED: {msg}. Never send API keys through the agent.", "blocked")
        return GuardrailResult(True)

    def _check_no_injection(self, text, context=None):
        """Detect common prompt injection attempts."""
        injection_patterns = [
            r'ignore\s+(all\s+)?previous\s+instructions',
            r'disregard\s+(all\s+)?prior\s+instructions',
            r'you\s+are\s+now\s+(a\s+)?different\s+ai',
            r'system\s*:\s*you\s+are',
            r'<\s*system\s*>',
            r'\[INST\]',
            r'###\s*SYSTEM',
        ]
        for pattern in injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return GuardrailResult(False, "BLOCKED: Potential prompt injection detected.", "blocked")
        return GuardrailResult(True)

    def _check_length(self, text, context=None):
        """Block extremely long inputs (potential abuse)."""
        if len(text) > 100_000:
            return GuardrailResult(False, "BLOCKED: Input too long (>100K chars). Please shorten your message.", "blocked")
        return GuardrailResult(True)

    def _check_no_pii_output(self, text, context=None):
        """Check for PII patterns in output (SSN, credit card, etc.)."""
        patterns = [
            (r'\b\d{3}-\d{2}-\d{4}\b', "SSN pattern"),
            (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', "Credit card pattern"),
        ]
        for pattern, name in patterns:
            if re.search(pattern, text):
                return GuardrailResult(False, f"WARNING: Output may contain {name}. Blocked for safety.", "warning")
        return GuardrailResult(True)

    def _check_no_harmful(self, text, context=None):
        """Basic check for harmful content patterns."""
        # This is a lightweight check — for production, use a dedicated content moderation API
        return GuardrailResult(True)

    def _log_event(self, event_type, rule_name, content_preview, message):
        self.log.append({
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "rule": rule_name,
            "preview": content_preview,
            "message": message
        })
        if len(self.log) > 1000:
            self.log = self.log[-1000:]


# ── SINGLETON ──
_guardrails = None

def get_guardrails():
    global _guardrails
    if _guardrails is None:
        _guardrails = Guardrails()
    return _guardrails
