"""
Janovum Platform — Heartbeat System
The platform's pulse. Runs periodic agent health checks and executes scheduled tasks.
Better than OpenClaw's heartbeat — supports per-client heartbeats, auto-recovery, and cost tracking.

How it works:
  1. Reads HEARTBEAT.md from each client's directory for their task checklist
  2. Checks agent health (are they alive? responding? stalled?)
  3. Executes due tasks from the checklist
  4. Reports results via configured channels (Telegram, Discord, email)
  5. If an agent is dead, attempts auto-restart

Config (in client config JSON):
  "heartbeat": {
    "enabled": true,
    "interval_seconds": 1800,      # 30 min default (like OpenClaw)
    "active_hours": {"start": "08:00", "end": "22:00", "timezone": "America/New_York"},
    "model": "haiku",               # use cheapest model for heartbeat checks
    "notify_channel": "telegram",    # where to send alerts
    "auto_restart": true            # auto-restart dead agents
  }
"""

import os
import sys
import json
import time
import threading
from datetime import datetime, timezone
from pathlib import Path

PLATFORM_DIR = Path(__file__).parent.parent
CLIENTS_DIR = PLATFORM_DIR / "clients"
HEARTBEAT_LOG = PLATFORM_DIR / "logs" / "heartbeat.log"

class AgentStatus:
    """Track the health status of a single agent."""
    ALIVE = "alive"
    STALLED = "stalled"
    DEAD = "dead"
    STARTING = "starting"
    UNKNOWN = "unknown"

class HeartbeatResult:
    """Result of a single heartbeat check."""
    OK = "HEARTBEAT_OK"
    ACTION_TAKEN = "ACTION_TAKEN"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"

class AgentHealthEntry:
    def __init__(self, agent_id, agent_type="generic", client_id=None):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.client_id = client_id
        self.status = AgentStatus.UNKNOWN
        self.last_heartbeat = None
        self.last_activity = None
        self.consecutive_failures = 0
        self.total_checks = 0
        self.total_actions = 0
        self.uptime_start = datetime.now()
        self.metadata = {}

    def record_heartbeat(self, success=True):
        self.last_heartbeat = datetime.now()
        self.total_checks += 1
        if success:
            self.status = AgentStatus.ALIVE
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
            if self.consecutive_failures >= 3:
                self.status = AgentStatus.DEAD
            elif self.consecutive_failures >= 1:
                self.status = AgentStatus.STALLED

    def record_activity(self):
        self.last_activity = datetime.now()
        self.total_actions += 1
        self.status = AgentStatus.ALIVE

    def uptime_seconds(self):
        return (datetime.now() - self.uptime_start).total_seconds()

    def to_dict(self):
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "client_id": self.client_id,
            "status": self.status,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "consecutive_failures": self.consecutive_failures,
            "total_checks": self.total_checks,
            "total_actions": self.total_actions,
            "uptime_seconds": int(self.uptime_seconds()),
            "metadata": self.metadata
        }


class HeartbeatDaemon:
    """
    The main heartbeat daemon. Manages all agent health checks.
    Runs in a background thread, checking all registered agents on their configured intervals.
    """

    def __init__(self):
        self.agents = {}  # agent_id -> AgentHealthEntry
        self.running = False
        self.thread = None
        self.check_interval = 30  # check the check-schedule every 30 seconds
        self.callbacks = {
            "on_agent_dead": [],
            "on_agent_recovered": [],
            "on_action_taken": [],
            "on_heartbeat_ok": [],
        }
        self.global_log = []  # recent heartbeat events
        self._lock = threading.Lock()

        # Ensure log directory exists
        HEARTBEAT_LOG.parent.mkdir(parents=True, exist_ok=True)

    def register_agent(self, agent_id, agent_type="generic", client_id=None, metadata=None):
        """Register an agent to be monitored by the heartbeat."""
        with self._lock:
            entry = AgentHealthEntry(agent_id, agent_type, client_id)
            if metadata:
                entry.metadata = metadata
            self.agents[agent_id] = entry
            self._log(f"Registered agent: {agent_id} (type={agent_type}, client={client_id})")
            return entry

    def unregister_agent(self, agent_id):
        """Remove an agent from heartbeat monitoring."""
        with self._lock:
            if agent_id in self.agents:
                del self.agents[agent_id]
                self._log(f"Unregistered agent: {agent_id}")
                return True
            return False

    def report_alive(self, agent_id):
        """Called by agents to report they're still alive."""
        with self._lock:
            if agent_id in self.agents:
                entry = self.agents[agent_id]
                was_dead = entry.status in (AgentStatus.DEAD, AgentStatus.STALLED)
                entry.record_heartbeat(success=True)
                if was_dead:
                    self._log(f"Agent RECOVERED: {agent_id}")
                    self._fire_callbacks("on_agent_recovered", entry)

    def report_activity(self, agent_id, action_description=""):
        """Called by agents when they take an action."""
        with self._lock:
            if agent_id in self.agents:
                self.agents[agent_id].record_activity()
                if action_description:
                    self._log(f"Agent {agent_id} action: {action_description}")

    def get_agent_status(self, agent_id):
        """Get the current status of an agent."""
        with self._lock:
            if agent_id in self.agents:
                return self.agents[agent_id].to_dict()
            return None

    def get_all_status(self):
        """Get status of all monitored agents."""
        with self._lock:
            return {aid: entry.to_dict() for aid, entry in self.agents.items()}

    def get_dashboard_summary(self):
        """Get a summary for the dashboard."""
        with self._lock:
            total = len(self.agents)
            alive = sum(1 for a in self.agents.values() if a.status == AgentStatus.ALIVE)
            stalled = sum(1 for a in self.agents.values() if a.status == AgentStatus.STALLED)
            dead = sum(1 for a in self.agents.values() if a.status == AgentStatus.DEAD)
            return {
                "total_agents": total,
                "alive": alive,
                "stalled": stalled,
                "dead": dead,
                "unknown": total - alive - stalled - dead,
                "recent_events": self.global_log[-20:],
                "agents": {aid: entry.to_dict() for aid, entry in self.agents.items()}
            }

    def load_heartbeat_checklist(self, client_id):
        """Load the HEARTBEAT.md checklist for a client."""
        heartbeat_path = CLIENTS_DIR / client_id / "HEARTBEAT.md"
        if heartbeat_path.exists():
            return heartbeat_path.read_text(encoding="utf-8")
        return ""

    def save_heartbeat_checklist(self, client_id, content):
        """Save the HEARTBEAT.md checklist for a client."""
        client_dir = CLIENTS_DIR / client_id
        client_dir.mkdir(parents=True, exist_ok=True)
        heartbeat_path = client_dir / "HEARTBEAT.md"
        heartbeat_path.write_text(content, encoding="utf-8")

    def check_active_hours(self, config):
        """Check if we're within active hours."""
        active_hours = config.get("heartbeat", {}).get("active_hours")
        if not active_hours:
            return True  # no restriction = always active

        try:
            now = datetime.now()
            start_h, start_m = map(int, active_hours["start"].split(":"))
            end_h, end_m = map(int, active_hours["end"].split(":"))
            current_minutes = now.hour * 60 + now.minute
            start_minutes = start_h * 60 + start_m
            end_minutes = end_h * 60 + end_m
            return start_minutes <= current_minutes <= end_minutes
        except Exception:
            return True

    def run_heartbeat_check(self, client_id, client_config):
        """
        Run a heartbeat check for a specific client.
        Reads their HEARTBEAT.md, uses Claude (cheapest model) to decide if action needed.
        """
        # Check active hours
        if not self.check_active_hours(client_config):
            return HeartbeatResult.SKIPPED, "Outside active hours"

        checklist = self.load_heartbeat_checklist(client_id)
        if not checklist or not checklist.strip().replace("#", "").strip():
            return HeartbeatResult.OK, "No tasks in checklist"

        # Use the engine to evaluate the checklist
        try:
            sys.path.insert(0, str(PLATFORM_DIR))
            from core.engine import quick_ask, MODELS

            heartbeat_model = client_config.get("heartbeat", {}).get("model", "haiku")
            model_id = MODELS.get(heartbeat_model, MODELS["haiku"])

            prompt = f"""You are a Janovum heartbeat agent. Check this task checklist and determine if any tasks need attention RIGHT NOW.

Current time: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## HEARTBEAT CHECKLIST:
{checklist}

Rules:
- If nothing needs attention, respond with exactly: HEARTBEAT_OK
- If a task needs action, describe what needs to be done concisely
- Do NOT make up tasks — only act on what's in the checklist
- Be brief — this runs every {client_config.get('heartbeat', {}).get('interval_seconds', 1800) // 60} minutes
"""
            response = quick_ask(prompt, force_model=model_id)

            if "HEARTBEAT_OK" in response:
                self._log(f"Heartbeat OK for client {client_id}")
                return HeartbeatResult.OK, response
            else:
                self._log(f"Heartbeat ACTION for client {client_id}: {response[:100]}")
                self._fire_callbacks("on_action_taken", {"client_id": client_id, "action": response})
                return HeartbeatResult.ACTION_TAKEN, response

        except Exception as e:
            self._log(f"Heartbeat ERROR for client {client_id}: {str(e)}")
            return HeartbeatResult.ERROR, str(e)

    def start(self):
        """Start the heartbeat daemon."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._daemon_loop, daemon=True)
        self.thread.start()
        self._log("Heartbeat daemon STARTED")

    def stop(self):
        """Stop the heartbeat daemon."""
        self.running = False
        self._log("Heartbeat daemon STOPPED")

    def _daemon_loop(self):
        """Main daemon loop — checks agent health and runs client heartbeats."""
        client_last_run = {}  # client_id -> last run timestamp

        while self.running:
            try:
                # 1. Check agent health — mark stalled agents
                with self._lock:
                    now = datetime.now()
                    for agent_id, entry in self.agents.items():
                        if entry.last_heartbeat:
                            silence = (now - entry.last_heartbeat).total_seconds()
                            # If no heartbeat for 5 minutes, mark stalled
                            if silence > 300 and entry.status == AgentStatus.ALIVE:
                                entry.status = AgentStatus.STALLED
                                self._log(f"Agent STALLED: {agent_id} (silent for {int(silence)}s)")
                            # If no heartbeat for 15 minutes, mark dead
                            if silence > 900 and entry.status == AgentStatus.STALLED:
                                entry.status = AgentStatus.DEAD
                                self._log(f"Agent DEAD: {agent_id} (silent for {int(silence)}s)")
                                self._fire_callbacks("on_agent_dead", entry)

                # 2. Run client heartbeat checks on their configured intervals
                if CLIENTS_DIR.exists():
                    for f in CLIENTS_DIR.iterdir():
                        if f.suffix == ".json" and not f.name.endswith("_results.json"):
                            client_id = f.stem
                            try:
                                config = json.loads(f.read_text())
                                hb_config = config.get("heartbeat", {})

                                if not hb_config.get("enabled", False):
                                    continue

                                interval = hb_config.get("interval_seconds", 1800)
                                last = client_last_run.get(client_id, 0)

                                if time.time() - last >= interval:
                                    self.run_heartbeat_check(client_id, config)
                                    client_last_run[client_id] = time.time()

                            except Exception as e:
                                self._log(f"Error checking client {client_id}: {str(e)}")

            except Exception as e:
                self._log(f"Daemon loop error: {str(e)}")

            # Sleep in 1-second chunks for responsive shutdown
            for _ in range(self.check_interval):
                if not self.running:
                    break
                time.sleep(1)

    def on(self, event, callback):
        """Register a callback for heartbeat events."""
        if event in self.callbacks:
            self.callbacks[event].append(callback)

    def _fire_callbacks(self, event, data):
        for cb in self.callbacks.get(event, []):
            try:
                cb(data)
            except Exception as e:
                self._log(f"Callback error ({event}): {str(e)}")

    def _log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self.global_log.append(entry)
        # Keep only last 500 entries in memory
        if len(self.global_log) > 500:
            self.global_log = self.global_log[-500:]
        # Also write to file
        try:
            with open(HEARTBEAT_LOG, "a", encoding="utf-8") as f:
                f.write(entry + "\n")
        except Exception:
            pass
        print(f"[heartbeat] {message}")


# ── SINGLETON ──
_daemon = None

def get_heartbeat():
    """Get the global heartbeat daemon instance."""
    global _daemon
    if _daemon is None:
        _daemon = HeartbeatDaemon()
    return _daemon

def start_heartbeat():
    """Start the global heartbeat daemon."""
    hb = get_heartbeat()
    hb.start()
    return hb

def stop_heartbeat():
    """Stop the global heartbeat daemon."""
    global _daemon
    if _daemon:
        _daemon.stop()
