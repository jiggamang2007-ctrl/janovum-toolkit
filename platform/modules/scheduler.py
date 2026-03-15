"""
Janovum Module — Scheduler (Cron / Heartbeat)
Runs tasks at specific times or intervals.
Like OpenClaw's Heartbeat — the system's clock.

How it works:
  1. You define scheduled tasks (check email every 5 min, scan deals every hour, send daily report at 9am)
  2. Python scheduler runs 24/7 checking the clock
  3. When it's time, triggers the appropriate module
  4. Results can be sent to client via Telegram/email

Requirements:
  pip install schedule (or use built-in sched)
"""

import json
import os
import sys
import time
import threading
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MODULE_NAME = "scheduler"
MODULE_DESC = "Scheduler — run tasks at specific times or intervals (cron/heartbeat)"

# Active scheduled jobs
active_jobs = {}


class Job:
    def __init__(self, job_id, name, interval_seconds, callback, args=None):
        self.job_id = job_id
        self.name = name
        self.interval = interval_seconds
        self.callback = callback
        self.args = args or []
        self.running = False
        self.last_run = None
        self.run_count = 0
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False

    def _loop(self):
        while self.running:
            try:
                self.callback(*self.args)
                self.last_run = datetime.now()
                self.run_count += 1
            except Exception as e:
                print(f"[scheduler] Job '{self.name}' error: {e}")

            # Sleep in 1-second chunks so we can stop quickly
            for _ in range(self.interval):
                if not self.running:
                    break
                time.sleep(1)

    def to_dict(self):
        return {
            "id": self.job_id,
            "name": self.name,
            "interval_seconds": self.interval,
            "running": self.running,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "run_count": self.run_count
        }


def add_job(job_id, name, interval_seconds, callback, args=None, start_now=True):
    """Add and optionally start a scheduled job."""
    job = Job(job_id, name, interval_seconds, callback, args)
    active_jobs[job_id] = job
    if start_now:
        job.start()
    print(f"[scheduler] Added job '{name}' — every {format_interval(interval_seconds)}")
    return job


def remove_job(job_id):
    """Stop and remove a scheduled job."""
    if job_id in active_jobs:
        active_jobs[job_id].stop()
        name = active_jobs[job_id].name
        del active_jobs[job_id]
        print(f"[scheduler] Removed job '{name}'")
        return True
    return False


def get_all_jobs():
    """Get status of all scheduled jobs."""
    return [job.to_dict() for job in active_jobs.values()]


def stop_all():
    """Stop all scheduled jobs."""
    for job in active_jobs.values():
        job.stop()
    active_jobs.clear()
    print("[scheduler] All jobs stopped")


def format_interval(seconds):
    """Format seconds into readable interval."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m"
    elif seconds < 86400:
        return f"{seconds // 3600}h"
    else:
        return f"{seconds // 86400}d"


# ── PRESET SCHEDULES ──
PRESETS = {
    "every_minute": 60,
    "every_5_minutes": 300,
    "every_15_minutes": 900,
    "every_30_minutes": 1800,
    "every_hour": 3600,
    "every_6_hours": 21600,
    "every_12_hours": 43200,
    "every_day": 86400,
}


def schedule_module(job_id, module_name, interval, client_config):
    """
    Schedule a module to run on an interval.

    module_name: which module to run (roi_scanner, email_responder, etc.)
    interval: seconds between runs, or a preset name
    """
    if isinstance(interval, str):
        interval = PRESETS.get(interval, 3600)

    def run_module():
        print(f"[scheduler] Running {module_name}...")
        if module_name == "roi_scanner":
            from modules.roi_scanner import run_scan
            run_scan(client_config)
        elif module_name == "email_responder":
            from modules.email_responder import check_inbox
            import imaplib
            try:
                imap = imaplib.IMAP4_SSL(client_config.get("imap_server", "imap.gmail.com"))
                imap.login(client_config["email"], client_config["email_password"])
                emails = check_inbox(imap)
                imap.logout()
                if emails:
                    print(f"[scheduler] Found {len(emails)} new emails")
            except Exception as e:
                print(f"[scheduler] Email check error: {e}")
        elif module_name == "web_search":
            from modules.web_search import search
            query = client_config.get("search_query", "")
            if query:
                results = search(query)
                print(f"[scheduler] Search found {len(results)} results")
        else:
            print(f"[scheduler] Unknown module: {module_name}")

    return add_job(job_id, f"{module_name} (scheduled)", interval, run_module)


TOOLS = [
    {
        "name": "schedule_task",
        "description": "Schedule a task to run at a regular interval",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name for this scheduled task"},
                "module": {"type": "string", "description": "Module to run"},
                "interval": {"type": "string", "description": "How often: every_minute, every_5_minutes, every_hour, every_day"}
            },
            "required": ["name", "module", "interval"]
        }
    },
    {
        "name": "list_scheduled",
        "description": "List all active scheduled tasks",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "cancel_scheduled",
        "description": "Cancel a scheduled task by ID",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "The job ID to cancel"}
            },
            "required": ["job_id"]
        }
    }
]


def execute_tool(tool_name, tool_input):
    if tool_name == "schedule_task":
        return json.dumps({"status": "scheduled", "name": tool_input["name"]})
    elif tool_name == "list_scheduled":
        return json.dumps(get_all_jobs())
    elif tool_name == "cancel_scheduled":
        removed = remove_job(tool_input["job_id"])
        return json.dumps({"removed": removed})
    return json.dumps({"error": f"Unknown tool: {tool_name}"})
