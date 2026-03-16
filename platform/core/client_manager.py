"""
Janovum Client Manager
Manages multiple receptionist instances — one per client, each on its own port.
Add clients via the toolkit dashboard, and they auto-start on the next available port.

Processes run INDEPENDENTLY — they survive server restarts.
We check if a client is running by pinging their port, not tracking child processes.

Features:
  - Auto Twilio webhook update on start
  - Port-in-use checking before start
  - Stderr logging per client
  - Health monitoring with response time
  - Toolkit config (domain, Twilio creds)
"""

import json
import os
import sys
import subprocess
import socket
import time
import urllib.request
from pathlib import Path
from datetime import datetime
from collections import deque

PLATFORM_DIR = Path(__file__).parent.parent
CLIENTS_DIR = PLATFORM_DIR / "data" / "clients"
CLIENTS_DIR.mkdir(parents=True, exist_ok=True)

# PID file directory
PIDS_DIR = CLIENTS_DIR / "pids"
PIDS_DIR.mkdir(parents=True, exist_ok=True)

# Log directory for client stderr
LOGS_DIR = CLIENTS_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Toolkit config path
TOOLKIT_CONFIG_PATH = PLATFORM_DIR / "data" / "toolkit_config.json"

# Port range for client receptionists
BASE_PORT = 5051


# ══════════════════════════════════════════
# TOOLKIT CONFIG
# ══════════════════════════════════════════

def load_toolkit_config():
    """Load toolkit-wide config (domain, Twilio creds, etc.)."""
    if TOOLKIT_CONFIG_PATH.exists():
        try:
            with open(TOOLKIT_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "domain": "",
        "twilio_account_sid": "",
        "twilio_auth_token": "",
        "auto_update_webhooks": True,
        "setup_complete": False,
    }


def save_toolkit_config(cfg):
    """Save toolkit-wide config."""
    with open(TOOLKIT_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


# ══════════════════════════════════════════
# TWILIO WEBHOOK AUTO-UPDATE
# ══════════════════════════════════════════

def _update_twilio_webhook(phone_number, webhook_url, toolkit_cfg=None):
    """Update a Twilio phone number's voice webhook URL.
    Returns (success: bool, message: str).
    """
    if toolkit_cfg is None:
        toolkit_cfg = load_toolkit_config()

    account_sid = toolkit_cfg.get("twilio_account_sid", "")
    auth_token = toolkit_cfg.get("twilio_auth_token", "")

    if not account_sid or not auth_token:
        return False, "Twilio credentials not configured in toolkit config"

    try:
        import base64

        # Step 1: Look up the phone number SID
        list_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/IncomingPhoneNumbers.json?PhoneNumber={urllib.request.quote(phone_number)}"
        auth_header = "Basic " + base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()

        req = urllib.request.Request(list_url, method="GET")
        req.add_header("Authorization", auth_header)
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read().decode())

        numbers = data.get("incoming_phone_numbers", [])
        if not numbers:
            return False, f"Phone number {phone_number} not found in Twilio account"

        phone_sid = numbers[0]["sid"]

        # Step 2: Update the voice webhook URL
        update_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/IncomingPhoneNumbers/{phone_sid}.json"
        post_data = urllib.request.urlencode({
            "VoiceUrl": webhook_url,
            "VoiceMethod": "POST",
        }).encode()

        req2 = urllib.request.Request(update_url, data=post_data, method="POST")
        req2.add_header("Authorization", auth_header)
        req2.add_header("Content-Type", "application/x-www-form-urlencoded")
        resp2 = urllib.request.urlopen(req2, timeout=10)

        if resp2.status == 200:
            return True, f"Webhook updated for {phone_number} -> {webhook_url}"
        else:
            return False, f"Twilio returned status {resp2.status}"

    except Exception as e:
        return False, f"Twilio webhook update failed: {str(e)}"


def update_all_webhooks(domain=None):
    """Update Twilio webhooks for ALL running clients. Called when domain changes."""
    toolkit_cfg = load_toolkit_config()
    if domain:
        toolkit_cfg["domain"] = domain
    else:
        domain = toolkit_cfg.get("domain", "")

    if not domain:
        return {"error": "No domain configured"}

    clients = _load_clients_index()
    results = []
    for c in clients:
        if _is_port_alive(c["port"]):
            config = get_client(c["client_id"])
            if config and config.get("twilio_phone_number"):
                webhook_url = f"https://{domain}/incoming"
                ok, msg = _update_twilio_webhook(config["twilio_phone_number"], webhook_url, toolkit_cfg)
                results.append({"client_id": c["client_id"], "success": ok, "message": msg})

    return {"updated": len(results), "results": results}


# ══════════════════════════════════════════
# PORT CHECKING
# ══════════════════════════════════════════

def _is_port_in_use(port):
    """Check if a port is already bound by any process (not just our receptionist)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(("localhost", port))
            return result == 0
    except Exception:
        return False


def _clients_index_path():
    return CLIENTS_DIR / "clients_index.json"


def _load_clients_index():
    path = _clients_index_path()
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_clients_index(clients):
    with open(_clients_index_path(), "w", encoding="utf-8") as f:
        json.dump(clients, f, indent=2)


def _next_available_port():
    clients = _load_clients_index()
    used_ports = {c["port"] for c in clients}
    port = BASE_PORT
    while port in used_ports:
        port += 1
    return port


def _generate_client_id(business_name):
    clean = "".join(c if c.isalnum() else "_" for c in business_name.lower()).strip("_")
    while "__" in clean:
        clean = clean.replace("__", "_")
    return clean[:30]


def _is_port_alive(port):
    """Check if a receptionist is actually running on this port."""
    try:
        req = urllib.request.Request(f"http://localhost:{port}/status", method="GET")
        resp = urllib.request.urlopen(req, timeout=2)
        return resp.status == 200
    except Exception:
        return False


def _save_pid(client_id, pid):
    pid_file = PIDS_DIR / f"{client_id}.pid"
    with open(pid_file, "w") as f:
        f.write(str(pid))


def _read_pid(client_id):
    pid_file = PIDS_DIR / f"{client_id}.pid"
    if pid_file.exists():
        try:
            with open(pid_file, "r") as f:
                return int(f.read().strip())
        except Exception:
            pass
    return None


def _remove_pid(client_id):
    pid_file = PIDS_DIR / f"{client_id}.pid"
    if pid_file.exists():
        os.remove(pid_file)


def _is_pid_alive(pid):
    """Check if a process with this PID is still running."""
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def list_clients():
    """Get all registered clients."""
    clients = _load_clients_index()
    for c in clients:
        c["running"] = _is_port_alive(c["port"])
    return clients


def get_client(client_id):
    """Get a single client's full config."""
    config_path = CLIENTS_DIR / f"{client_id}.json"
    if not config_path.exists():
        return None
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def add_client(data):
    """Add a new client."""
    business_name = data.get("business_name", "").strip()
    if not business_name:
        return {"error": "business_name is required"}

    twilio_phone = data.get("twilio_phone_number", "").strip()
    if not twilio_phone:
        return {"error": "twilio_phone_number is required — buy one from Twilio first"}

    client_id = _generate_client_id(business_name)

    existing = _load_clients_index()
    if any(c["client_id"] == client_id for c in existing):
        return {"error": f"Client '{business_name}' already exists (id: {client_id})"}

    port = _next_available_port()

    default_hours = {
        "monday": {"open": "09:00", "close": "17:00"},
        "tuesday": {"open": "09:00", "close": "17:00"},
        "wednesday": {"open": "09:00", "close": "17:00"},
        "thursday": {"open": "09:00", "close": "17:00"},
        "friday": {"open": "09:00", "close": "17:00"},
        "saturday": "closed",
        "sunday": "closed",
    }

    config = {
        "client_id": client_id,
        "business_name": business_name,
        "business_type": data.get("business_type", "General Business"),
        "twilio_phone_number": twilio_phone,
        "port": port,
        "timezone": data.get("timezone", "America/New_York"),
        "business_hours": data.get("hours", default_hours),
        "services": data.get("services", [
            {"name": "General Appointment", "duration_minutes": 30}
        ]),
        "staff": data.get("staff", []),
        "personality": {
            "greeting": data.get("greeting", f"Hi there! Thanks for calling {business_name}. How can I help you today?"),
            "farewell": data.get("farewell", "Thanks so much for calling! Have a great day."),
            "tone": data.get("tone", "warm and professional"),
        },
        "notification_email": data.get("notification_email", ""),
        "daily_spend_cap": float(data.get("daily_spend_cap", 5.00)),
        "daily_call_limit": int(data.get("daily_call_limit", 50)),
        "created_at": datetime.now().isoformat(),
        "status": "stopped",
    }

    config_path = CLIENTS_DIR / f"{client_id}.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    appts_path = CLIENTS_DIR / f"{client_id}_appointments.json"
    if not appts_path.exists():
        with open(appts_path, "w", encoding="utf-8") as f:
            json.dump([], f)

    existing.append({
        "client_id": client_id,
        "business_name": business_name,
        "twilio_phone_number": twilio_phone,
        "port": port,
        "created_at": config["created_at"],
        "status": "stopped",
    })
    _save_clients_index(existing)

    return {"success": True, "client_id": client_id, "port": port, "config": config}


def update_client(client_id, data):
    """Update a client's config."""
    config_path = CLIENTS_DIR / f"{client_id}.json"
    if not config_path.exists():
        return {"error": f"Client '{client_id}' not found"}

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    updatable = [
        "business_name", "business_type", "twilio_phone_number", "timezone",
        "business_hours", "services", "staff", "personality",
        "notification_email", "daily_spend_cap", "daily_call_limit",
    ]
    for key in updatable:
        if key in data:
            config[key] = data[key]

    config["updated_at"] = datetime.now().isoformat()

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    clients = _load_clients_index()
    for c in clients:
        if c["client_id"] == client_id:
            if "business_name" in data:
                c["business_name"] = data["business_name"]
            if "twilio_phone_number" in data:
                c["twilio_phone_number"] = data["twilio_phone_number"]
            break
    _save_clients_index(clients)

    return {"success": True, "config": config}


def delete_client(client_id):
    """Remove a client. Stops their receptionist first."""
    stop_client(client_id)

    config_path = CLIENTS_DIR / f"{client_id}.json"
    appts_path = CLIENTS_DIR / f"{client_id}_appointments.json"

    if config_path.exists():
        os.remove(config_path)
    if appts_path.exists():
        os.remove(appts_path)

    clients = _load_clients_index()
    clients = [c for c in clients if c["client_id"] != client_id]
    _save_clients_index(clients)

    return {"success": True, "message": f"Client '{client_id}' removed"}


def start_client(client_id):
    """Start a client's receptionist as an independent process.
    Includes: port-in-use check, stderr logging, auto Twilio webhook update.
    """
    config = get_client(client_id)
    if not config:
        return {"error": f"Client '{client_id}' not found"}

    port = config["port"]

    # Already running? Check the actual port
    if _is_port_alive(port):
        return {"error": "Already running", "port": port}

    # Check if port is in use by something else
    if _is_port_in_use(port):
        return {"error": f"Port {port} is already in use by another process. Stop it or change this client's port.", "port": port}

    receptionist_script = PLATFORM_DIR / "receptionist_client.py"
    config_path = CLIENTS_DIR / f"{client_id}.json"

    if not receptionist_script.exists():
        return {"error": f"receptionist_client.py not found at {receptionist_script}"}

    # Open log file for stderr capture
    log_file_path = LOGS_DIR / f"{client_id}.log"
    try:
        log_file = open(log_file_path, "a", encoding="utf-8")
        log_file.write(f"\n{'='*60}\n[{datetime.now().isoformat()}] Starting client: {client_id} on port {port}\n{'='*60}\n")
        log_file.flush()
    except Exception as e:
        return {"error": f"Could not open log file: {e}"}

    # Start as a fully independent process (survives server restarts)
    # CREATE_NEW_PROCESS_GROUP on Windows makes it independent
    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

    # Use venv python on Linux if available
    python_exe = sys.executable
    venv_python = Path("/root/janovum-venv/bin/python")
    if sys.platform != "win32" and venv_python.exists():
        python_exe = str(venv_python)

    try:
        proc = subprocess.Popen(
            [python_exe, str(receptionist_script), str(config_path)],
            cwd=str(PLATFORM_DIR),
            stdout=log_file,
            stderr=log_file,
            creationflags=creation_flags,
            start_new_session=(sys.platform != "win32"),
        )
    except Exception as e:
        log_file.close()
        return {"error": f"Failed to start process: {str(e)}"}

    # Save PID to file so we can stop it later
    _save_pid(client_id, proc.pid)

    # Check if process died immediately (give it a moment)
    time.sleep(0.5)
    if proc.poll() is not None:
        exit_code = proc.returncode
        # Read last few lines of log for error details
        log_file.close()
        error_lines = get_client_logs(client_id, lines=20)
        _remove_pid(client_id)
        return {
            "error": f"Process exited immediately with code {exit_code}",
            "exit_code": exit_code,
            "recent_logs": error_lines,
        }

    _update_client_status(client_id, "running")

    # Auto-update Twilio webhook if domain is configured
    webhook_result = None
    toolkit_cfg = load_toolkit_config()
    domain = toolkit_cfg.get("domain", "")
    if domain and toolkit_cfg.get("auto_update_webhooks", True):
        phone = config.get("twilio_phone_number", "")
        if phone:
            webhook_url = f"https://{domain}/incoming"
            ok, msg = _update_twilio_webhook(phone, webhook_url, toolkit_cfg)
            webhook_result = {"success": ok, "message": msg}

    result = {"success": True, "client_id": client_id, "port": port, "pid": proc.pid}
    if webhook_result:
        result["webhook"] = webhook_result

    return result


def stop_client(client_id):
    """Stop a client's receptionist process."""
    config = get_client(client_id)
    port = config["port"] if config else None

    # Try to kill by saved PID
    pid = _read_pid(client_id)
    if pid and _is_pid_alive(pid):
        try:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
            else:
                import signal
                os.kill(pid, signal.SIGTERM)
        except Exception:
            pass

    _remove_pid(client_id)
    _update_client_status(client_id, "stopped")
    return {"success": True, "message": f"Client '{client_id}' stopped"}


def get_client_appointments(client_id):
    """Get appointments for a specific client."""
    appts_path = CLIENTS_DIR / f"{client_id}_appointments.json"
    if not appts_path.exists():
        return []
    with open(appts_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_all_stats():
    """Get overview stats across all clients, including health/response time."""
    clients = _load_clients_index()
    total_appointments = 0
    running_count = 0

    for c in clients:
        appts = get_client_appointments(c["client_id"])
        c["appointment_count"] = len(appts)
        total_appointments += len(appts)
        is_running = _is_port_alive(c["port"])
        c["running"] = is_running
        if is_running:
            running_count += 1
            # Quick health ping for response time
            health = check_client_health(c["client_id"])
            c["response_time_ms"] = health.get("response_time_ms")
        else:
            c["response_time_ms"] = None

    # Check if domain is configured for first-time setup detection
    toolkit_cfg = load_toolkit_config()
    domain_configured = bool(toolkit_cfg.get("domain", ""))

    return {
        "total_clients": len(clients),
        "running": running_count,
        "stopped": len(clients) - running_count,
        "total_appointments": total_appointments,
        "clients": clients,
        "domain_configured": domain_configured,
    }


def _get_client_port(client_id):
    clients = _load_clients_index()
    for c in clients:
        if c["client_id"] == client_id:
            return c["port"]
    return None


def _update_client_status(client_id, status):
    clients = _load_clients_index()
    for c in clients:
        if c["client_id"] == client_id:
            c["status"] = status
            break
    _save_clients_index(clients)


# ══════════════════════════════════════════
# HEALTH CHECK
# ══════════════════════════════════════════

def check_client_health(client_id):
    """Ping a client's receptionist and return health info."""
    config = get_client(client_id)
    if not config:
        return {"status": "not_found", "error": f"Client '{client_id}' not found"}

    port = config["port"]
    pid = _read_pid(client_id)

    result = {
        "client_id": client_id,
        "port": port,
        "pid": pid,
        "pid_alive": _is_pid_alive(pid),
    }

    # Ping the port and measure response time
    try:
        start = time.time()
        req = urllib.request.Request(f"http://localhost:{port}/status", method="GET")
        resp = urllib.request.urlopen(req, timeout=5)
        elapsed = (time.time() - start) * 1000  # ms

        result["status"] = "healthy"
        result["http_status"] = resp.status
        result["response_time_ms"] = round(elapsed, 1)

        # Try to read response body for extra info
        try:
            body = json.loads(resp.read().decode())
            result["uptime"] = body.get("uptime")
            result["calls_handled"] = body.get("calls_handled")
        except Exception:
            pass

    except Exception as e:
        result["status"] = "unhealthy"
        result["response_time_ms"] = None
        result["error"] = str(e)

    return result


# ══════════════════════════════════════════
# CLIENT LOGS
# ══════════════════════════════════════════

def get_client_logs(client_id, lines=100):
    """Read the last N lines from a client's log file."""
    log_path = LOGS_DIR / f"{client_id}.log"
    if not log_path.exists():
        return []

    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
        return [line.rstrip("\n") for line in all_lines[-lines:]]
    except Exception:
        return []


def clear_client_logs(client_id):
    """Clear a client's log file."""
    log_path = LOGS_DIR / f"{client_id}.log"
    if log_path.exists():
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(f"[{datetime.now().isoformat()}] Logs cleared.\n")
            return True
        except Exception:
            pass
    return False
