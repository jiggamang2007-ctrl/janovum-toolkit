"""
Janovum User Client Manager
Per-user client management — mirrors client_manager.py but scopes all data
to a specific user's directory under data/users/{user_id}/.

Each user has their own clients, configs, logs, and processes.
Port allocation is global (6000+) to avoid collisions across all users.
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

PLATFORM_DIR = Path(__file__).parent.parent
USERS_DIR = PLATFORM_DIR / "data" / "users"
ADMIN_CLIENTS_DIR = PLATFORM_DIR / "data" / "clients"

# Tenant users get ports starting at 6000 (admin uses 5051-5999)
TENANT_BASE_PORT = 6000


class UserClientManager:
    """Client manager scoped to a single user's data directory."""

    def __init__(self, user_id):
        self.user_id = user_id
        self.base_dir = USERS_DIR / user_id
        self.clients_dir = self.base_dir / "clients"
        self.pids_dir = self.clients_dir / "pids"
        self.logs_dir = self.clients_dir / "logs"
        self.toolkit_config_path = self.base_dir / "toolkit_config.json"

        # Ensure directories exist
        self.clients_dir.mkdir(parents=True, exist_ok=True)
        self.pids_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    # ── Toolkit Config ──────────────────────────

    def load_toolkit_config(self):
        if self.toolkit_config_path.exists():
            try:
                with open(self.toolkit_config_path, "r", encoding="utf-8") as f:
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

    def save_toolkit_config(self, cfg):
        with open(self.toolkit_config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)

    # ── Clients Index ───────────────────────────

    def _index_path(self):
        return self.clients_dir / "clients_index.json"

    def _load_index(self):
        path = self._index_path()
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save_index(self, clients):
        with open(self._index_path(), "w", encoding="utf-8") as f:
            json.dump(clients, f, indent=2)

    # ── Port Allocation (global across all users) ──

    def _next_available_port(self):
        """Scan all user directories + admin for used ports."""
        used = set()

        # Admin ports
        admin_idx = ADMIN_CLIENTS_DIR / "clients_index.json"
        if admin_idx.exists():
            try:
                with open(admin_idx, "r", encoding="utf-8") as f:
                    for c in json.load(f):
                        used.add(c.get("port", 0))
            except Exception:
                pass

        # All tenant user ports
        if USERS_DIR.exists():
            for uid in os.listdir(USERS_DIR):
                idx = USERS_DIR / uid / "clients" / "clients_index.json"
                if idx.exists():
                    try:
                        with open(idx, "r", encoding="utf-8") as f:
                            for c in json.load(f):
                                used.add(c.get("port", 0))
                    except Exception:
                        pass

        port = TENANT_BASE_PORT
        while port in used:
            port += 1
        return port

    # ── Client ID ───────────────────────────────

    def _generate_client_id(self, business_name):
        clean = "".join(c if c.isalnum() else "_" for c in business_name.lower()).strip("_")
        while "__" in clean:
            clean = clean.replace("__", "_")
        base_id = clean[:30]

        # Ensure unique within this user's clients
        existing = self._load_index()
        existing_ids = {c["client_id"] for c in existing}
        if base_id not in existing_ids:
            return base_id
        counter = 2
        while f"{base_id}_{counter}" in existing_ids:
            counter += 1
        return f"{base_id}_{counter}"

    # ── Port / Process Helpers ──────────────────

    def _is_port_in_use(self, port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                return s.connect_ex(("localhost", port)) == 0
        except Exception:
            return False

    def _is_port_alive(self, port):
        try:
            req = urllib.request.Request(f"http://localhost:{port}/status", method="GET")
            resp = urllib.request.urlopen(req, timeout=2)
            return resp.status == 200
        except Exception:
            return False

    def _save_pid(self, client_id, pid):
        with open(self.pids_dir / f"{client_id}.pid", "w") as f:
            f.write(str(pid))

    def _read_pid(self, client_id):
        pid_file = self.pids_dir / f"{client_id}.pid"
        if pid_file.exists():
            try:
                with open(pid_file, "r") as f:
                    return int(f.read().strip())
            except Exception:
                pass
        return None

    def _remove_pid(self, client_id):
        pid_file = self.pids_dir / f"{client_id}.pid"
        if pid_file.exists():
            os.remove(pid_file)

    def _is_pid_alive(self, pid):
        if pid is None:
            return False
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def _update_status(self, client_id, status):
        clients = self._load_index()
        for c in clients:
            if c["client_id"] == client_id:
                c["status"] = status
                break
        self._save_index(clients)

    # ── CRUD Operations ─────────────────────────

    def get_client(self, client_id):
        config_path = self.clients_dir / f"{client_id}.json"
        if not config_path.exists():
            return None
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def add_client(self, data):
        business_name = data.get("business_name", "").strip()
        if not business_name:
            return {"error": "business_name is required"}

        twilio_phone = data.get("twilio_phone_number", "").strip()
        if not twilio_phone:
            return {"error": "twilio_phone_number is required — buy one from Twilio first"}

        client_id = self._generate_client_id(business_name)
        port = self._next_available_port()

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
            "cartesia": {
                "api_key": data.get("cartesia_api_key", ""),
                "voice_id": data.get("cartesia_voice_id", "f786b574-daa5-4673-aa0c-cbe3e8534c02"),
            },
            "notification_email": data.get("notification_email", ""),
            "daily_spend_cap": float(data.get("daily_spend_cap", 5.00)),
            "daily_call_limit": int(data.get("daily_call_limit", 50)),
            "created_at": datetime.now().isoformat(),
            "status": "stopped",
        }

        config_path = self.clients_dir / f"{client_id}.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        appts_path = self.clients_dir / f"{client_id}_appointments.json"
        if not appts_path.exists():
            with open(appts_path, "w", encoding="utf-8") as f:
                json.dump([], f)

        index = self._load_index()
        index.append({
            "client_id": client_id,
            "business_name": business_name,
            "twilio_phone_number": twilio_phone,
            "port": port,
            "created_at": config["created_at"],
            "status": "stopped",
        })
        self._save_index(index)

        return {"success": True, "client_id": client_id, "port": port, "config": config}

    def update_client(self, client_id, data):
        config_path = self.clients_dir / f"{client_id}.json"
        if not config_path.exists():
            return {"error": f"Client '{client_id}' not found"}

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        updatable = [
            "business_name", "business_type", "twilio_phone_number", "timezone",
            "business_hours", "services", "staff", "personality",
            "notification_email", "daily_spend_cap", "daily_call_limit", "cartesia",
        ]
        for key in updatable:
            if key in data:
                if key == "cartesia" and isinstance(data[key], dict):
                    existing = config.get("cartesia", {})
                    existing.update(data[key])
                    config[key] = existing
                else:
                    config[key] = data[key]

        config["updated_at"] = datetime.now().isoformat()

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        clients = self._load_index()
        for c in clients:
            if c["client_id"] == client_id:
                if "business_name" in data:
                    c["business_name"] = data["business_name"]
                if "twilio_phone_number" in data:
                    c["twilio_phone_number"] = data["twilio_phone_number"]
                break
        self._save_index(clients)

        return {"success": True, "config": config}

    def delete_client(self, client_id):
        self.stop_client(client_id)

        config_path = self.clients_dir / f"{client_id}.json"
        appts_path = self.clients_dir / f"{client_id}_appointments.json"

        if config_path.exists():
            os.remove(config_path)
        if appts_path.exists():
            os.remove(appts_path)

        clients = self._load_index()
        clients = [c for c in clients if c["client_id"] != client_id]
        self._save_index(clients)

        return {"success": True, "message": f"Client '{client_id}' removed"}

    # ── Process Management ──────────────────────

    def start_client(self, client_id):
        config = self.get_client(client_id)
        if not config:
            return {"error": f"Client '{client_id}' not found"}

        port = config["port"]

        if self._is_port_alive(port):
            return {"error": "Already running", "port": port}

        if self._is_port_in_use(port):
            return {"error": f"Port {port} is already in use by another process.", "port": port}

        receptionist_script = PLATFORM_DIR / "receptionist_client.py"
        config_path = self.clients_dir / f"{client_id}.json"

        if not receptionist_script.exists():
            return {"error": f"receptionist_client.py not found at {receptionist_script}"}

        log_file_path = self.logs_dir / f"{client_id}.log"
        try:
            log_file = open(log_file_path, "a", encoding="utf-8")
            log_file.write(f"\n{'='*60}\n[{datetime.now().isoformat()}] Starting client: {client_id} on port {port}\n{'='*60}\n")
            log_file.flush()
        except Exception as e:
            return {"error": f"Could not open log file: {e}"}

        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

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

        self._save_pid(client_id, proc.pid)

        time.sleep(0.5)
        if proc.poll() is not None:
            exit_code = proc.returncode
            log_file.close()
            error_lines = self.get_logs(client_id, lines=20)
            self._remove_pid(client_id)
            return {
                "error": f"Process exited immediately with code {exit_code}",
                "exit_code": exit_code,
                "recent_logs": error_lines,
            }

        self._update_status(client_id, "running")

        # Auto-update Twilio webhook if domain is configured
        webhook_result = None
        toolkit_cfg = self.load_toolkit_config()
        domain = toolkit_cfg.get("domain", "")
        if domain and toolkit_cfg.get("auto_update_webhooks", True):
            phone = config.get("twilio_phone_number", "")
            if phone:
                webhook_url = f"https://{domain}/incoming"
                ok, msg = self._update_twilio_webhook(phone, webhook_url, toolkit_cfg)
                webhook_result = {"success": ok, "message": msg}

        result = {"success": True, "client_id": client_id, "port": port, "pid": proc.pid}
        if webhook_result:
            result["webhook"] = webhook_result
        return result

    def stop_client(self, client_id):
        config = self.get_client(client_id)

        pid = self._read_pid(client_id)
        if pid and self._is_pid_alive(pid):
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
                else:
                    import signal
                    os.kill(pid, signal.SIGTERM)
            except Exception:
                pass

        self._remove_pid(client_id)
        self._update_status(client_id, "stopped")
        return {"success": True, "message": f"Client '{client_id}' stopped"}

    # ── Appointments ────────────────────────────

    def get_appointments(self, client_id):
        appts_path = self.clients_dir / f"{client_id}_appointments.json"
        if not appts_path.exists():
            return []
        with open(appts_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_all_appointments(self):
        """Get appointments across all this user's clients."""
        all_appts = []
        clients = self._load_index()
        for c in clients:
            appts = self.get_appointments(c["client_id"])
            for a in appts:
                a["client_id"] = c["client_id"]
                a["business_name"] = c.get("business_name", "")
            all_appts.extend(appts)
        return all_appts

    # ── Stats & Health ──────────────────────────

    def get_all_stats(self):
        clients = self._load_index()
        total_appointments = 0
        running_count = 0

        for c in clients:
            appts = self.get_appointments(c["client_id"])
            c["appointment_count"] = len(appts)
            total_appointments += len(appts)
            is_running = self._is_port_alive(c["port"])
            c["running"] = is_running
            if is_running:
                running_count += 1
                health = self.check_health(c["client_id"])
                c["response_time_ms"] = health.get("response_time_ms")
            else:
                c["response_time_ms"] = None

        toolkit_cfg = self.load_toolkit_config()
        domain_configured = bool(toolkit_cfg.get("domain", ""))

        return {
            "total_clients": len(clients),
            "running": running_count,
            "stopped": len(clients) - running_count,
            "total_appointments": total_appointments,
            "clients": clients,
            "domain_configured": domain_configured,
        }

    def check_health(self, client_id):
        config = self.get_client(client_id)
        if not config:
            return {"status": "not_found", "error": f"Client '{client_id}' not found"}

        port = config["port"]
        pid = self._read_pid(client_id)

        result = {
            "client_id": client_id,
            "port": port,
            "pid": pid,
            "pid_alive": self._is_pid_alive(pid),
        }

        try:
            start = time.time()
            req = urllib.request.Request(f"http://localhost:{port}/status", method="GET")
            resp = urllib.request.urlopen(req, timeout=5)
            elapsed = (time.time() - start) * 1000

            result["status"] = "healthy"
            result["http_status"] = resp.status
            result["response_time_ms"] = round(elapsed, 1)

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

    # ── Logs ────────────────────────────────────

    def get_logs(self, client_id, lines=100):
        log_path = self.logs_dir / f"{client_id}.log"
        if not log_path.exists():
            return []
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
            return [line.rstrip("\n") for line in all_lines[-lines:]]
        except Exception:
            return []

    def clear_logs(self, client_id):
        log_path = self.logs_dir / f"{client_id}.log"
        if log_path.exists():
            try:
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().isoformat()}] Logs cleared.\n")
                return True
            except Exception:
                pass
        return False

    # ── Twilio Webhook ──────────────────────────

    def _update_twilio_webhook(self, phone_number, webhook_url, toolkit_cfg=None):
        if toolkit_cfg is None:
            toolkit_cfg = self.load_toolkit_config()

        account_sid = toolkit_cfg.get("twilio_account_sid", "")
        auth_token = toolkit_cfg.get("twilio_auth_token", "")

        if not account_sid or not auth_token:
            return False, "Twilio credentials not configured"

        try:
            import base64
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

    def update_all_webhooks(self, domain=None):
        toolkit_cfg = self.load_toolkit_config()
        if domain:
            toolkit_cfg["domain"] = domain
        else:
            domain = toolkit_cfg.get("domain", "")

        if not domain:
            return {"error": "No domain configured"}

        clients = self._load_index()
        results = []
        for c in clients:
            if self._is_port_alive(c["port"]):
                config = self.get_client(c["client_id"])
                if config and config.get("twilio_phone_number"):
                    webhook_url = f"https://{domain}/incoming"
                    ok, msg = self._update_twilio_webhook(config["twilio_phone_number"], webhook_url, toolkit_cfg)
                    results.append({"client_id": c["client_id"], "success": ok, "message": msg})

        return {"updated": len(results), "results": results}
