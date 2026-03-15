"""
Janovum Platform — Cost Tracker
Tracks API spending per client in real-time.
Prevents cost overruns with configurable limits.
Better than OpenClaw — per-client budgets, daily/monthly tracking, automatic alerts.
"""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

PLATFORM_DIR = Path(__file__).parent.parent
COST_DATA_DIR = PLATFORM_DIR / "data" / "costs"

# Pricing per 1M tokens (as of 2026)
MODEL_PRICING = {
    "claude-haiku-4-5-20251001": {"input": 0.25, "output": 1.25},
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
}


class CostTracker:
    """Track and limit API costs per client."""

    def __init__(self):
        COST_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.alerts = []  # callback functions for budget alerts

    def record_usage(self, client_id, model_id, input_tokens, output_tokens, capability="llm"):
        """Record a single API call's cost."""
        pricing = MODEL_PRICING.get(model_id, {"input": 3.0, "output": 15.0})
        cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000

        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")

        # Load or create client cost file
        cost_file = COST_DATA_DIR / f"{client_id}.json"
        data = self._load_cost_data(client_id)

        # Update daily
        if today not in data["daily"]:
            data["daily"][today] = {"cost": 0, "calls": 0, "input_tokens": 0, "output_tokens": 0}
        data["daily"][today]["cost"] += cost
        data["daily"][today]["calls"] += 1
        data["daily"][today]["input_tokens"] += input_tokens
        data["daily"][today]["output_tokens"] += output_tokens

        # Update monthly
        if month not in data["monthly"]:
            data["monthly"][month] = {"cost": 0, "calls": 0}
        data["monthly"][month]["cost"] += cost
        data["monthly"][month]["calls"] += 1

        # Update totals
        data["total_cost"] += cost
        data["total_calls"] += 1
        data["last_call"] = datetime.now().isoformat()

        # Track by capability
        if capability not in data["by_capability"]:
            data["by_capability"][capability] = {"cost": 0, "calls": 0}
        data["by_capability"][capability]["cost"] += cost
        data["by_capability"][capability]["calls"] += 1

        # Track by model
        model_name = model_id.split("-")[1] if "-" in model_id else model_id
        if model_name not in data["by_model"]:
            data["by_model"][model_name] = {"cost": 0, "calls": 0}
        data["by_model"][model_name]["cost"] += cost
        data["by_model"][model_name]["calls"] += 1

        self._save_cost_data(client_id, data)

        # Check budget limits
        self._check_limits(client_id, data)

        return {"cost": round(cost, 6), "daily_total": round(data["daily"][today]["cost"], 4), "monthly_total": round(data["monthly"][month]["cost"], 2)}

    def get_client_costs(self, client_id):
        """Get cost breakdown for a client."""
        data = self._load_cost_data(client_id)
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")

        return {
            "client_id": client_id,
            "today": data["daily"].get(today, {"cost": 0, "calls": 0}),
            "this_month": data["monthly"].get(month, {"cost": 0, "calls": 0}),
            "total": {"cost": round(data["total_cost"], 4), "calls": data["total_calls"]},
            "by_capability": data["by_capability"],
            "by_model": data["by_model"],
            "budget": data.get("budget", {}),
            "last_call": data.get("last_call")
        }

    def get_all_costs(self):
        """Get cost summary for all clients."""
        clients = {}
        if COST_DATA_DIR.exists():
            for f in COST_DATA_DIR.iterdir():
                if f.suffix == ".json":
                    client_id = f.stem
                    clients[client_id] = self.get_client_costs(client_id)

        total_cost = sum(c["total"]["cost"] for c in clients.values())
        month = datetime.now().strftime("%Y-%m")
        monthly_cost = sum(c["this_month"].get("cost", 0) for c in clients.values())

        return {
            "total_cost": round(total_cost, 2),
            "monthly_cost": round(monthly_cost, 2),
            "client_count": len(clients),
            "clients": clients
        }

    def set_budget(self, client_id, daily_limit=None, monthly_limit=None):
        """Set spending limits for a client."""
        data = self._load_cost_data(client_id)
        if daily_limit is not None:
            data["budget"]["daily_limit"] = daily_limit
        if monthly_limit is not None:
            data["budget"]["monthly_limit"] = monthly_limit
        self._save_cost_data(client_id, data)

    def check_budget(self, client_id):
        """Check if client is within budget. Returns (allowed, reason)."""
        data = self._load_cost_data(client_id)
        budget = data.get("budget", {})
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")

        daily_cost = data["daily"].get(today, {}).get("cost", 0)
        monthly_cost = data["monthly"].get(month, {}).get("cost", 0)

        if budget.get("daily_limit") and daily_cost >= budget["daily_limit"]:
            return False, f"Daily budget exceeded: ${daily_cost:.2f} / ${budget['daily_limit']:.2f}"
        if budget.get("monthly_limit") and monthly_cost >= budget["monthly_limit"]:
            return False, f"Monthly budget exceeded: ${monthly_cost:.2f} / ${budget['monthly_limit']:.2f}"

        return True, "Within budget"

    def on_budget_alert(self, callback):
        """Register a callback for budget alerts."""
        self.alerts.append(callback)

    def _check_limits(self, client_id, data):
        """Check if approaching or exceeding limits."""
        budget = data.get("budget", {})
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")

        daily_cost = data["daily"].get(today, {}).get("cost", 0)
        monthly_cost = data["monthly"].get(month, {}).get("cost", 0)

        for cb in self.alerts:
            try:
                if budget.get("daily_limit") and daily_cost >= budget["daily_limit"] * 0.8:
                    cb(client_id, "daily", daily_cost, budget["daily_limit"])
                if budget.get("monthly_limit") and monthly_cost >= budget["monthly_limit"] * 0.8:
                    cb(client_id, "monthly", monthly_cost, budget["monthly_limit"])
            except Exception:
                pass

    def _load_cost_data(self, client_id):
        cost_file = COST_DATA_DIR / f"{client_id}.json"
        if cost_file.exists():
            try:
                return json.loads(cost_file.read_text())
            except Exception:
                pass
        return {
            "client_id": client_id,
            "daily": {},
            "monthly": {},
            "total_cost": 0,
            "total_calls": 0,
            "by_capability": {},
            "by_model": {},
            "budget": {},
            "last_call": None
        }

    def _save_cost_data(self, client_id, data):
        cost_file = COST_DATA_DIR / f"{client_id}.json"
        cost_file.write_text(json.dumps(data, indent=2))


# ── SINGLETON ──
_tracker = None

def get_cost_tracker():
    global _tracker
    if _tracker is None:
        _tracker = CostTracker()
    return _tracker
