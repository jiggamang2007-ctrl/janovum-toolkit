"""
Janovum Platform — Multi-Model Failover
If Claude API fails or is over budget, automatically fall back to free models.
Tries: Claude (paid) → Groq free → Pollinations free → Ollama local

This ensures the platform NEVER goes down even if one provider has issues.
"""

import os
import json
import time
import requests
from datetime import datetime
from pathlib import Path

PLATFORM_DIR = Path(__file__).parent.parent


class ModelProvider:
    def __init__(self, name, call_fn, cost_per_1k_tokens=0, requires_key=False, key_env=None):
        self.name = name
        self.call_fn = call_fn
        self.cost = cost_per_1k_tokens
        self.requires_key = requires_key
        self.key_env = key_env
        self.status = "active"
        self.cooldown_until = None
        self.total_calls = 0
        self.total_failures = 0

    def is_available(self):
        if self.status == "disabled":
            return False
        if self.cooldown_until and time.time() < self.cooldown_until:
            return False
        if self.requires_key and self.key_env and not os.environ.get(self.key_env):
            return False
        self.status = "active"
        return True

    def record_failure(self):
        self.total_failures += 1
        backoff = min(60 * (2 ** min(self.total_failures - 1, 5)), 3600)
        self.cooldown_until = time.time() + backoff
        self.status = "cooldown"

    def record_success(self):
        self.total_calls += 1
        self.total_failures = 0
        self.status = "active"


def _call_claude(messages, system_prompt=None, model=None, max_tokens=4096):
    """Call Claude API."""
    from core.config import get_api_key
    from core.engine import MODELS

    api_key = get_api_key()
    if not api_key:
        raise Exception("No Claude API key")

    model = model or MODELS.get("haiku")
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    body = {"model": model, "max_tokens": max_tokens, "messages": messages}
    if system_prompt:
        body["system"] = system_prompt

    resp = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=body, timeout=120)
    if resp.status_code != 200:
        raise Exception(f"Claude API error: {resp.status_code}")

    data = resp.json()
    text = ""
    for block in data.get("content", []):
        if block["type"] == "text":
            text += block["text"]
    return {"text": text, "usage": data.get("usage", {}), "provider": "claude", "model": model}


def _call_groq(messages, system_prompt=None, model="llama-3.1-8b-instant", max_tokens=4096):
    """Call Groq free API."""
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise Exception("No Groq API key")

    msgs = []
    if system_prompt:
        msgs.append({"role": "system", "content": system_prompt})
    msgs.extend(messages)

    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": msgs, "max_tokens": max_tokens},
        timeout=30
    )
    if resp.status_code != 200:
        raise Exception(f"Groq error: {resp.status_code}")

    data = resp.json()
    return {
        "text": data["choices"][0]["message"]["content"],
        "usage": data.get("usage", {}),
        "provider": "groq", "model": model
    }


def _call_pollinations(messages, system_prompt=None, **kwargs):
    """Call Pollinations.ai free text API."""
    import urllib.parse
    last_msg = messages[-1]["content"] if messages else ""
    if system_prompt:
        last_msg = f"{system_prompt}\n\n{last_msg}"
    encoded = urllib.parse.quote(last_msg)
    resp = requests.get(f"https://text.pollinations.ai/{encoded}", timeout=60)
    if resp.status_code == 200:
        return {"text": resp.text, "usage": {}, "provider": "pollinations", "model": "pollinations"}
    raise Exception(f"Pollinations error: {resp.status_code}")


def _call_ollama(messages, system_prompt=None, model="llama3.1", max_tokens=4096):
    """Call local Ollama."""
    msgs = []
    if system_prompt:
        msgs.append({"role": "system", "content": system_prompt})
    msgs.extend(messages)

    resp = requests.post(
        "http://localhost:11434/api/chat",
        json={"model": model, "messages": msgs, "stream": False},
        timeout=120
    )
    if resp.status_code != 200:
        raise Exception(f"Ollama error: {resp.status_code}")

    data = resp.json()
    return {"text": data["message"]["content"], "usage": {}, "provider": "ollama", "model": model}


class ModelFailover:
    """Try multiple LLM providers in order of preference."""

    def __init__(self):
        self.providers = [
            ModelProvider("claude", _call_claude, cost_per_1k_tokens=3.0, requires_key=True, key_env="ANTHROPIC_API_KEY"),
            ModelProvider("groq", _call_groq, cost_per_1k_tokens=0, requires_key=True, key_env="GROQ_API_KEY"),
            ModelProvider("pollinations", _call_pollinations, cost_per_1k_tokens=0),
            ModelProvider("ollama", _call_ollama, cost_per_1k_tokens=0),
        ]

    def call(self, messages, system_prompt=None, max_tokens=4096, preferred_provider=None):
        """Call LLM with automatic failover."""
        providers = list(self.providers)
        if preferred_provider:
            providers.sort(key=lambda p: 0 if p.name == preferred_provider else 1)

        errors = []
        for provider in providers:
            if not provider.is_available():
                continue
            try:
                result = provider.call_fn(messages, system_prompt=system_prompt, max_tokens=max_tokens)
                provider.record_success()
                return result
            except Exception as e:
                provider.record_failure()
                errors.append(f"{provider.name}: {e}")

        raise Exception(f"All LLM providers failed: {'; '.join(errors)}")

    def get_status(self):
        return [{
            "name": p.name, "status": p.status, "cost": p.cost,
            "total_calls": p.total_calls, "failures": p.total_failures,
            "available": p.is_available()
        } for p in self.providers]


_failover = None
def get_model_failover():
    global _failover
    if _failover is None:
        _failover = ModelFailover()
    return _failover
