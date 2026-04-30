"""
Appends the proactive agent backend to server_v2.py on the VPS.
Run once. Safe — only adds new routes and a background thread.
"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('104.238.133.244', username='root', password='Ek2+X-HhF5-g{EJ7')

sftp = ssh.open_sftp()

# Read current server
with sftp.open('/root/janovum-toolkit/platform/server_v2.py', 'r') as f:
    server = f.read().decode('utf-8')

# Don't double-add
if '# ── PROACTIVE AGENT' in server:
    print('Proactive agent already exists in server. Skipping.')
    sftp.close()
    ssh.close()
    exit()

PROACTIVE_CODE = '''

# ─────────────────────────────────────────────────────────────────────────────
# PROACTIVE AGENT — background task runner
# ─────────────────────────────────────────────────────────────────────────────
import threading as _threading
import subprocess as _subprocess

_PROACTIVE_FILE  = os.path.join(PLATFORM_DIR, "data", "proactive_tasks.json")
_PROACTIVE_LOG   = os.path.join(PLATFORM_DIR, "data", "proactive_log.json")
_agent_running   = False
_agent_thread    = None

def _pa_load_tasks():
    if os.path.exists(_PROACTIVE_FILE):
        with open(_PROACTIVE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []

def _pa_save_tasks(tasks):
    os.makedirs(os.path.dirname(_PROACTIVE_FILE), exist_ok=True)
    with open(_PROACTIVE_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2)

def _pa_log(entry):
    log = []
    if os.path.exists(_PROACTIVE_LOG):
        with open(_PROACTIVE_LOG, encoding="utf-8") as f:
            try: log = json.load(f)
            except: log = []
    entry["ts"] = datetime.utcnow().isoformat() + "Z"
    log.insert(0, entry)
    log = log[:500]
    os.makedirs(os.path.dirname(_PROACTIVE_LOG), exist_ok=True)
    with open(_PROACTIVE_LOG, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)

def _pa_run_task(task):
    t = task.get("type", "custom")
    name = task.get("name", t)
    try:
        if t == "crm_health_check":
            contacts = _crm_load()
            no_phone = sum(1 for c in contacts if not c.get("phone"))
            no_email = sum(1 for c in contacts if not c.get("email"))
            ai_gen   = sum(1 for c in contacts if c.get("source") == "AI-Generated")
            result   = f"{len(contacts)} total contacts | {ai_gen} AI-generated | {no_phone} missing phone | {no_email} missing email"

        elif t == "receptionist_check":
            r = _subprocess.run(["systemctl", "is-active", "janovum-receptionist"],
                                capture_output=True, text=True, timeout=5)
            status = r.stdout.strip() or "unknown"
            result = f"Receptionist service: {status}"

        elif t == "daily_crm_summary":
            contacts = _crm_load()
            new_leads  = [c for c in contacts if c.get("status") == "new"]
            contacted  = [c for c in contacts if c.get("status") == "contacted"]
            closed     = [c for c in contacts if c.get("status") == "closed"]
            result = f"Pipeline — New: {len(new_leads)} | Contacted: {len(contacted)} | Closed: {len(closed)} | Total: {len(contacts)}"

        elif t == "ping_server":
            import time as _time
            start = _time.time()
            import urllib.request as _ur
            _ur.urlopen("https://janovum.com/api/status", timeout=5)
            ms = int((_time.time() - start) * 1000)
            result = f"Server ping: {ms}ms — online"

        elif t == "custom":
            result = task.get("description", "Task ran successfully.")

        else:
            result = f"Unknown task type: {t}"

        _pa_log({"task": name, "type": t, "result": result, "status": "success"})

    except Exception as e:
        _pa_log({"task": name, "type": t, "result": str(e), "status": "error"})

def _proactive_loop():
    global _agent_running
    import time as _time
    while _agent_running:
        try:
            tasks = _pa_load_tasks()
            now   = datetime.utcnow()
            changed = False
            for task in tasks:
                if not task.get("enabled", True):
                    continue
                interval = int(task.get("interval_minutes", 60))
                last_run = task.get("last_run")
                if last_run:
                    try:
                        last_dt  = datetime.fromisoformat(last_run.rstrip("Z"))
                        elapsed  = (now - last_dt).total_seconds() / 60
                        if elapsed < interval:
                            continue
                    except:
                        pass
                _pa_run_task(task)
                task["last_run"]  = now.isoformat() + "Z"
                task["run_count"] = task.get("run_count", 0) + 1
                changed = True
            if changed:
                _pa_save_tasks(tasks)
        except Exception as e:
            print(f"[ProactiveAgent] loop error: {e}")
        _time.sleep(60)

def _start_proactive_agent():
    global _agent_running, _agent_thread
    if _agent_running:
        return
    _agent_running = True
    _agent_thread  = _threading.Thread(target=_proactive_loop, daemon=True)
    _agent_thread.start()
    # Seed default tasks if none exist
    if not _pa_load_tasks():
        default_tasks = [
            {"id": str(uuid.uuid4()), "name": "CRM Health Check",    "type": "crm_health_check",  "interval_minutes": 60,  "enabled": True, "run_count": 0, "description": "Check CRM contact counts and data quality"},
            {"id": str(uuid.uuid4()), "name": "Daily Pipeline Summary","type": "daily_crm_summary","interval_minutes": 1440,"enabled": True, "run_count": 0, "description": "Daily summary of leads by status"},
            {"id": str(uuid.uuid4()), "name": "Receptionist Health", "type": "receptionist_check","interval_minutes": 30,  "enabled": True, "run_count": 0, "description": "Verify receptionist service is running"},
            {"id": str(uuid.uuid4()), "name": "Server Ping",         "type": "ping_server",       "interval_minutes": 15,  "enabled": True, "run_count": 0, "description": "Ping janovum.com and log response time"},
        ]
        _pa_save_tasks(default_tasks)
    print("[ProactiveAgent] started with", len(_pa_load_tasks()), "tasks")

# Auto-start on server boot
_start_proactive_agent()

# ── PROACTIVE AGENT ROUTES ──────────────────────────────────────────────────

@app.route("/api/proactive/status", methods=["GET"])
def proactive_status():
    log = []
    if os.path.exists(_PROACTIVE_LOG):
        with open(_PROACTIVE_LOG, encoding="utf-8") as f:
            try: log = json.load(f)
            except: log = []
    return jsonify({"running": _agent_running, "task_count": len(_pa_load_tasks()), "log": log[:50]})

@app.route("/api/proactive/start", methods=["POST"])
def proactive_start():
    _start_proactive_agent()
    return jsonify({"ok": True, "running": _agent_running})

@app.route("/api/proactive/stop", methods=["POST"])
def proactive_stop():
    global _agent_running
    _agent_running = False
    return jsonify({"ok": True, "running": False})

@app.route("/api/proactive/tasks", methods=["GET"])
def proactive_get_tasks():
    return jsonify(_pa_load_tasks())

@app.route("/api/proactive/tasks", methods=["POST"])
def proactive_add_task():
    task = request.json or {}
    task["id"]        = str(uuid.uuid4())
    task["created"]   = datetime.utcnow().isoformat() + "Z"
    task["run_count"] = 0
    task["enabled"]   = task.get("enabled", True)
    tasks = _pa_load_tasks()
    tasks.append(task)
    _pa_save_tasks(tasks)
    return jsonify({"ok": True, "task": task})

@app.route("/api/proactive/tasks/<task_id>", methods=["POST"])
def proactive_update_task(task_id):
    data  = request.json or {}
    tasks = _pa_load_tasks()
    for t in tasks:
        if t.get("id") == task_id:
            t.update(data)
            break
    _pa_save_tasks(tasks)
    return jsonify({"ok": True})

@app.route("/api/proactive/tasks/<task_id>", methods=["DELETE"])
def proactive_delete_task(task_id):
    tasks = [t for t in _pa_load_tasks() if t.get("id") != task_id]
    _pa_save_tasks(tasks)
    return jsonify({"ok": True})

@app.route("/api/proactive/tasks/<task_id>/run", methods=["POST"])
def proactive_run_now(task_id):
    tasks = _pa_load_tasks()
    task  = next((t for t in tasks if t.get("id") == task_id), None)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    _pa_run_task(task)
    task["last_run"]  = datetime.utcnow().isoformat() + "Z"
    task["run_count"] = task.get("run_count", 0) + 1
    _pa_save_tasks(tasks)
    return jsonify({"ok": True})

@app.route("/api/proactive/log", methods=["GET"])
def proactive_get_log():
    log = []
    if os.path.exists(_PROACTIVE_LOG):
        with open(_PROACTIVE_LOG, encoding="utf-8") as f:
            try: log = json.load(f)
            except: log = []
    return jsonify(log[:200])

@app.route("/api/proactive/log", methods=["DELETE"])
def proactive_clear_log():
    if os.path.exists(_PROACTIVE_LOG):
        os.remove(_PROACTIVE_LOG)
    return jsonify({"ok": True})
'''

# Find a safe insertion point — just before the final app.run / if __name__ block
insert_markers = ['if __name__ == "__main__"', "if __name__ == '__main__'", 'app.run(']
insert_pos = -1
for marker in insert_markers:
    idx = server.rfind(marker)
    if idx != -1:
        insert_pos = idx
        break

if insert_pos == -1:
    # Just append at end
    new_server = server + PROACTIVE_CODE
else:
    new_server = server[:insert_pos] + PROACTIVE_CODE + '\n' + server[insert_pos:]

with sftp.open('/root/janovum-toolkit/platform/server_v2.py', 'w') as f:
    f.write(new_server.encode('utf-8'))

sftp.close()

# Syntax check
stdin, stdout, stderr = ssh.exec_command('cd /root/janovum-toolkit && python3 -m py_compile platform/server_v2.py && echo SYNTAX_OK')
out = stdout.read().decode()
err = stderr.read().decode()
print(out)
if err: print('ERRORS:', err)

if 'SYNTAX_OK' in out:
    # Restart service
    stdin, stdout, stderr = ssh.exec_command('systemctl restart janovum-toolkit && sleep 3 && systemctl is-active janovum-toolkit')
    print('Service:', stdout.read().decode().strip())
else:
    print('Syntax check failed — NOT restarting. Fix errors above.')

ssh.close()
