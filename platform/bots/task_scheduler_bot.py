"""
Task Scheduler Bot
Cron-like task scheduler. Reads a schedule config, executes Python functions
or shell commands at specified times/intervals.
"""

import sys
import os
import json
import time
import logging
import subprocess
import importlib
import threading
from pathlib import Path
from datetime import datetime, timedelta

PLATFORM_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLATFORM_DIR))

BOT_INFO = {
    "name": "Task Scheduler",
    "category": "automation",
    "description": "Runs tasks on schedules -- cron for your toolkit",
    "icon": "\u23f0",
    "version": "1.0",
    "author": "Janovum",
    "config_schema": {
        "schedule_file": {"type": "str", "default": ""},
        "tick_interval_seconds": {"type": "int", "default": 30},
        "log_output": {"type": "bool", "default": True},
        "max_concurrent_tasks": {"type": "int", "default": 3},
        "shell": {"type": "str", "default": "bash"},
    }
}

# Schedule entry format:
# {
#   "name": "My Task",
#   "type": "shell" | "python" | "bot",
#   "command": "echo hello"  (for shell)
#   "module": "bots.lead_hunter" (for python/bot)
#   "function": "run"  (for python)
#   "args": {}  (optional args for python function)
#   "interval_minutes": 60,
#   "cron": "0 */2 * * *",  (alternative to interval_minutes -- simplified cron)
#   "enabled": true,
#   "run_on_start": false,
#   "last_run": null,
#   "next_run": null,
# }

_running = False
_status = {"state": "stopped", "tasks_executed": 0, "tasks_failed": 0, "last_tick": None, "errors": []}
_active_threads = []
_logger = logging.getLogger("TaskScheduler")
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    _logger.addHandler(logging.StreamHandler())

DATA_DIR = PLATFORM_DIR / "data" / "bots" / "task_scheduler"
SCHEDULE_FILE = DATA_DIR / "schedule.json"
TASK_LOG = DATA_DIR / "task_log.json"


def _ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_schedule(schedule_file=""):
    sf = Path(schedule_file) if schedule_file else SCHEDULE_FILE
    if sf.exists():
        try:
            return json.loads(sf.read_text(encoding="utf-8"))
        except Exception:
            return []

    # Create a default schedule with examples
    defaults = [
        {
            "name": "Example: Print Time",
            "type": "shell",
            "command": "echo Current time: $(date)",
            "interval_minutes": 60,
            "enabled": False,
            "run_on_start": False,
            "last_run": None,
            "next_run": None,
        },
        {
            "name": "Example: Run Lead Hunter",
            "type": "bot",
            "module": "bots.lead_hunter",
            "function": "run",
            "args": {},
            "interval_minutes": 120,
            "enabled": False,
            "run_on_start": False,
            "last_run": None,
            "next_run": None,
        }
    ]
    _ensure_dirs()
    SCHEDULE_FILE.write_text(json.dumps(defaults, indent=2), encoding="utf-8")
    return defaults


def _save_schedule(schedule, schedule_file=""):
    sf = Path(schedule_file) if schedule_file else SCHEDULE_FILE
    sf.write_text(json.dumps(schedule, indent=2, default=str), encoding="utf-8")


def _load_task_log():
    if TASK_LOG.exists():
        try:
            return json.loads(TASK_LOG.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_task_log(log):
    # Keep last 500 entries
    TASK_LOG.write_text(json.dumps(log[-500:], indent=2, default=str), encoding="utf-8")


def _parse_simple_cron(cron_str):
    """
    Parse a simplified cron expression: 'minute hour day_of_month month day_of_week'
    Supports: *, */N, specific numbers
    Returns True if current time matches.
    """
    if not cron_str:
        return False

    parts = cron_str.strip().split()
    if len(parts) != 5:
        return False

    now = datetime.now()
    fields = [now.minute, now.hour, now.day, now.month, now.weekday()]
    ranges = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 6)]

    for i, (part, current, (low, high)) in enumerate(zip(parts, fields, ranges)):
        if part == "*":
            continue
        elif part.startswith("*/"):
            try:
                step = int(part[2:])
                if current % step != 0:
                    return False
            except ValueError:
                return False
        else:
            try:
                values = [int(v) for v in part.split(",")]
                if current not in values:
                    return False
            except ValueError:
                return False

    return True


def _should_run(task, now):
    """Determine if a task should run now."""
    if not task.get("enabled", True):
        return False

    # Check cron expression
    cron = task.get("cron", "")
    if cron:
        return _parse_simple_cron(cron)

    # Check interval
    interval = task.get("interval_minutes", 60)
    last_run = task.get("last_run")

    if last_run is None:
        return task.get("run_on_start", False) or True  # Run if never ran

    try:
        last_dt = datetime.fromisoformat(last_run)
        next_run = last_dt + timedelta(minutes=interval)
        return now >= next_run
    except (ValueError, TypeError):
        return True


def _execute_shell(command, shell="bash"):
    """Execute a shell command and return output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,
            executable=shell if shell != "cmd" else None,
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout[:5000],
            "stderr": result.stderr[:2000],
        }
    except subprocess.TimeoutExpired:
        return {"returncode": -1, "stdout": "", "stderr": "Task timed out (300s)"}
    except Exception as e:
        return {"returncode": -1, "stdout": "", "stderr": str(e)}


def _execute_python(module_path, function_name, args=None):
    """Execute a Python function from a module."""
    try:
        # Handle relative module paths
        if module_path.startswith("bots."):
            bot_file = PLATFORM_DIR / module_path.replace(".", "/")
            bot_file = bot_file.with_suffix(".py")
            if not bot_file.exists():
                return {"returncode": -1, "error": f"Module not found: {bot_file}"}

            import importlib.util
            spec = importlib.util.spec_from_file_location(module_path, str(bot_file))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        else:
            module = importlib.import_module(module_path)

        func = getattr(module, function_name)
        if args:
            result = func(**args) if isinstance(args, dict) else func(args)
        else:
            result = func()

        return {"returncode": 0, "result": str(result)[:5000]}

    except Exception as e:
        return {"returncode": -1, "error": str(e)}


def _run_task(task, config, task_log):
    """Execute a single task."""
    global _status

    task_name = task.get("name", "unnamed")
    task_type = task.get("type", "shell")
    _logger.info(f"Executing task: {task_name} (type={task_type})")

    start_time = datetime.now()
    result = {}

    try:
        if task_type == "shell":
            result = _execute_shell(task.get("command", "echo no command"), config.get("shell", "bash"))
        elif task_type in ("python", "bot"):
            result = _execute_python(
                task.get("module", ""),
                task.get("function", "run"),
                task.get("args")
            )
        else:
            result = {"returncode": -1, "error": f"Unknown task type: {task_type}"}

        duration = (datetime.now() - start_time).total_seconds()
        success = result.get("returncode", -1) == 0

        if success:
            _status["tasks_executed"] += 1
            _logger.info(f"  Task '{task_name}' completed in {duration:.1f}s")
        else:
            _status["tasks_failed"] += 1
            error_msg = result.get("stderr", result.get("error", "unknown error"))
            _logger.error(f"  Task '{task_name}' failed: {error_msg[:200]}")
            _status["errors"].append(f"{task_name}: {error_msg[:100]}")

        # Log entry
        log_entry = {
            "task": task_name,
            "type": task_type,
            "started_at": start_time.isoformat(),
            "duration_seconds": round(duration, 2),
            "success": success,
            "result_preview": str(result)[:500],
        }

        if config.get("log_output", True):
            log_entry["full_output"] = result

        task_log.append(log_entry)

        # Update last_run
        task["last_run"] = start_time.isoformat()

    except Exception as e:
        _logger.error(f"  Task execution error: {e}")
        _status["tasks_failed"] += 1
        _status["errors"].append(str(e))


def _tick(schedule, config, task_log):
    """One scheduler tick -- check all tasks and run if due."""
    now = datetime.now()
    max_concurrent = config.get("max_concurrent_tasks", 3)

    # Clean up finished threads
    global _active_threads
    _active_threads = [t for t in _active_threads if t.is_alive()]

    for task in schedule:
        if not _running:
            break

        if _should_run(task, now):
            if len(_active_threads) >= max_concurrent:
                _logger.warning(f"Max concurrent tasks reached ({max_concurrent}). Skipping {task.get('name')}")
                continue

            # Run task in a thread to avoid blocking
            t = threading.Thread(target=_run_task, args=(task, config, task_log), daemon=True)
            t.start()
            _active_threads.append(t)


def run(config=None):
    """Start the task scheduler bot loop."""
    global _running, _status
    _running = True
    _ensure_dirs()

    if config is None:
        config = {v: s["default"] for v, s in BOT_INFO["config_schema"].items()}

    _status = {"state": "running", "tasks_executed": 0, "tasks_failed": 0, "last_tick": None, "errors": []}
    _logger.info("Task Scheduler started.")

    tick_interval = config.get("tick_interval_seconds", 30)
    schedule_file = config.get("schedule_file", "")
    schedule = _load_schedule(schedule_file)
    task_log = _load_task_log()

    _logger.info(f"Loaded {len(schedule)} tasks ({sum(1 for t in schedule if t.get('enabled', True))} enabled)")

    # Run run_on_start tasks
    for task in schedule:
        if task.get("run_on_start", False) and task.get("enabled", True) and task.get("last_run") is None:
            t = threading.Thread(target=_run_task, args=(task, config, task_log), daemon=True)
            t.start()
            _active_threads.append(t)

    while _running:
        try:
            _status["state"] = "ticking"
            _tick(schedule, config, task_log)
            _status["last_tick"] = datetime.now().isoformat()
            _status["state"] = "waiting"

            # Periodically save
            _save_schedule(schedule, schedule_file)
            _save_task_log(task_log)

        except Exception as e:
            _logger.error(f"Scheduler tick error: {e}")
            _status["errors"].append(str(e))
            _status["state"] = "error"

        for _ in range(tick_interval):
            if not _running:
                break
            time.sleep(1)

    # Wait for active tasks to finish
    for t in _active_threads:
        t.join(timeout=10)

    _save_schedule(schedule, schedule_file)
    _save_task_log(task_log)
    _status["state"] = "stopped"
    _logger.info("Task Scheduler stopped.")


def stop():
    global _running
    _running = False
    _status["state"] = "stopping"


def get_status():
    schedule = _load_schedule() if SCHEDULE_FILE.exists() else []
    enabled = sum(1 for t in schedule if t.get("enabled", True))
    return {**_status, "total_tasks": len(schedule), "enabled_tasks": enabled, "active_threads": len([t for t in _active_threads if t.is_alive()])}


# ── Helpers to manage schedule at runtime ──

def add_task(name, task_type="shell", command="", module="", function="run", args=None,
             interval_minutes=60, cron="", enabled=True, run_on_start=False):
    """Add a task to the schedule."""
    _ensure_dirs()
    schedule = _load_schedule()
    task = {
        "name": name,
        "type": task_type,
        "command": command,
        "module": module,
        "function": function,
        "args": args or {},
        "interval_minutes": interval_minutes,
        "cron": cron,
        "enabled": enabled,
        "run_on_start": run_on_start,
        "last_run": None,
        "next_run": None,
    }
    schedule.append(task)
    _save_schedule(schedule)
    _logger.info(f"Added task: {name}")
    return task


def remove_task(name):
    """Remove a task from the schedule by name."""
    schedule = _load_schedule()
    schedule = [t for t in schedule if t.get("name") != name]
    _save_schedule(schedule)
    _logger.info(f"Removed task: {name}")


def list_tasks():
    """List all scheduled tasks."""
    return _load_schedule()


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        stop()
