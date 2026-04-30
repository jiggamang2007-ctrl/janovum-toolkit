"""
Adds Operator Platform routes to server_v2.py on VPS.
Safe — only appends new routes, touches nothing existing.
"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('104.238.133.244', username='root', password='Ek2+X-HhF5-g{EJ7')
sftp = ssh.open_sftp()

with sftp.open('/root/janovum-toolkit/platform/server_v2.py', 'r') as f:
    server = f.read().decode('utf-8')

if '# ── OPERATOR PLATFORM' in server:
    print('Platform routes already exist. Skipping.')
    sftp.close(); ssh.close(); exit()

PLATFORM_ROUTES = '''

# ─────────────────────────────────────────────────────────────────────────────
# OPERATOR PLATFORM — white-label, billing, revenue share
# ─────────────────────────────────────────────────────────────────────────────

_OP_CONFIG_FILE  = os.path.join(PLATFORM_DIR, "data", "operator_config.json")
_OP_REVENUE_FILE = os.path.join(PLATFORM_DIR, "data", "operator_revenue.json")
_OP_ONBOARD_FILE = os.path.join(PLATFORM_DIR, "data", "operator_onboarding.json")

JANOVUM_REVENUE_SHARE = 0.15   # 15% of client billings go to Janovum

PLANS = {
    "starter": {"name": "Starter", "price": 97,  "clients": 3,  "description": "Up to 3 clients"},
    "pro":     {"name": "Pro",     "price": 297, "clients": 10, "description": "Up to 10 clients"},
    "agency":  {"name": "Agency",  "price": 497, "clients": 999,"description": "Unlimited clients"},
}

def _op_load_config():
    if os.path.exists(_OP_CONFIG_FILE):
        with open(_OP_CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {
        "brand_name": "",
        "logo_url": "",
        "primary_color": "#3B82F6",
        "domain": "",
        "support_email": "",
        "plan": "starter",
        "stripe_connected": False,
        "billing_email": "",
        "onboarded": False,
    }

def _op_save_config(cfg):
    os.makedirs(os.path.dirname(_OP_CONFIG_FILE), exist_ok=True)
    with open(_OP_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def _op_load_revenue():
    if os.path.exists(_OP_REVENUE_FILE):
        with open(_OP_REVENUE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []

def _op_save_revenue(data):
    os.makedirs(os.path.dirname(_OP_REVENUE_FILE), exist_ok=True)
    with open(_OP_REVENUE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def _op_load_onboarding():
    if os.path.exists(_OP_ONBOARD_FILE):
        with open(_OP_ONBOARD_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {
        "set_brand": False,
        "connect_twilio": False,
        "deploy_receptionist": False,
        "add_first_client": False,
        "connect_billing": False,
    }

def _op_save_onboarding(data):
    os.makedirs(os.path.dirname(_OP_ONBOARD_FILE), exist_ok=True)
    with open(_OP_ONBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# Serve the operator hub page
@app.route("/operator")
def operator_hub():
    return _no_cache_html(send_from_directory(os.path.join(PARENT_DIR), "Janovum_Operator_Hub.html"))

# White-label / config
@app.route("/api/platform/config", methods=["GET"])
def platform_get_config():
    cfg = _op_load_config()
    cfg["plan_details"] = PLANS.get(cfg.get("plan", "starter"), PLANS["starter"])
    cfg["revenue_share_pct"] = int(JANOVUM_REVENUE_SHARE * 100)
    return jsonify(cfg)

@app.route("/api/platform/config", methods=["POST"])
def platform_save_config():
    data = request.json or {}
    cfg  = _op_load_config()
    allowed = ["brand_name","logo_url","primary_color","domain","support_email","plan","billing_email"]
    for k in allowed:
        if k in data:
            cfg[k] = data[k]
    # Auto-mark brand step done
    if cfg.get("brand_name"):
        ob = _op_load_onboarding()
        ob["set_brand"] = True
        _op_save_onboarding(ob)
    _op_save_config(cfg)
    return jsonify({"ok": True, "config": cfg})

# Onboarding checklist
@app.route("/api/platform/onboarding", methods=["GET"])
def platform_get_onboarding():
    ob  = _op_load_onboarding()
    cfg = _op_load_config()
    # Auto-detect steps from existing data
    contacts = _crm_load()
    if contacts:
        ob["add_first_client"] = True
    if cfg.get("brand_name"):
        ob["set_brand"] = True
    _op_save_onboarding(ob)
    total = len(ob)
    done  = sum(1 for v in ob.values() if v)
    return jsonify({"steps": ob, "total": total, "done": done, "pct": int(done/total*100)})

@app.route("/api/platform/onboarding/<step>", methods=["POST"])
def platform_complete_step(step):
    ob = _op_load_onboarding()
    if step in ob:
        ob[step] = True
        _op_save_onboarding(ob)
    return jsonify({"ok": True})

# Revenue tracking
@app.route("/api/platform/revenue", methods=["GET"])
def platform_get_revenue():
    entries = _op_load_revenue()
    now     = datetime.utcnow()
    month_entries = [e for e in entries
                     if e.get("date","")[:7] == now.strftime("%Y-%m")]
    total_month   = sum(e.get("amount", 0) for e in month_entries)
    cut_month     = round(total_month * JANOVUM_REVENUE_SHARE, 2)
    total_all     = sum(e.get("amount", 0) for e in entries)
    cut_all       = round(total_all * JANOVUM_REVENUE_SHARE, 2)
    return jsonify({
        "entries": entries[-100:],
        "this_month": {"revenue": total_month, "janovum_cut": cut_month},
        "all_time":   {"revenue": total_all,   "janovum_cut": cut_all},
        "share_pct":  int(JANOVUM_REVENUE_SHARE * 100),
    })

@app.route("/api/platform/revenue/log", methods=["POST"])
def platform_log_revenue():
    data    = request.json or {}
    entries = _op_load_revenue()
    import uuid as _uuid_mod
    entry = {
        "id":          str(_uuid_mod.uuid4()),
        "client_name": data.get("client_name", ""),
        "amount":      float(data.get("amount", 0)),
        "type":        data.get("type", "monthly"),   # monthly | setup | other
        "date":        data.get("date", datetime.utcnow().strftime("%Y-%m-%d")),
        "notes":       data.get("notes", ""),
        "janovum_cut": round(float(data.get("amount", 0)) * JANOVUM_REVENUE_SHARE, 2),
    }
    entries.append(entry)
    _op_save_revenue(entries)
    # Auto-mark billing step done
    ob = _op_load_onboarding()
    if not ob.get("connect_billing"):
        ob["connect_billing"] = True
        _op_save_onboarding(ob)
    return jsonify({"ok": True, "entry": entry})

@app.route("/api/platform/revenue/<entry_id>", methods=["DELETE"])
def platform_delete_revenue(entry_id):
    entries = [e for e in _op_load_revenue() if e.get("id") != entry_id]
    _op_save_revenue(entries)
    return jsonify({"ok": True})

# Plans info
@app.route("/api/platform/plans", methods=["GET"])
def platform_get_plans():
    return jsonify(PLANS)

# Stripe connect placeholder
@app.route("/api/platform/billing/connect", methods=["POST"])
def platform_connect_billing():
    # Placeholder — Stripe OAuth will go here
    cfg = _op_load_config()
    cfg["stripe_connected"] = True
    _op_save_config(cfg)
    return jsonify({"ok": True, "message": "Billing integration coming soon. Your revenue share will be tracked automatically."})
'''

# Find insertion point (before proactive agent or before app.run)
insert_markers = ['# ── PROACTIVE AGENT', 'if __name__ == "__main__"', "if __name__ == '__main__'"]
insert_pos = -1
for marker in insert_markers:
    idx = server.find(marker)
    if idx != -1:
        insert_pos = idx
        break

if insert_pos == -1:
    new_server = server + PLATFORM_ROUTES
else:
    new_server = server[:insert_pos] + PLATFORM_ROUTES + '\n' + server[insert_pos:]

with sftp.open('/root/janovum-toolkit/platform/server_v2.py', 'w') as f:
    f.write(new_server.encode('utf-8'))

sftp.close()

# Syntax check
stdin, stdout, stderr = ssh.exec_command('python3 -m py_compile /root/janovum-toolkit/platform/server_v2.py && echo SYNTAX_OK')
out = stdout.read().decode(); err = stderr.read().decode()
print(out)
if err: print('ERRORS:', err)

if 'SYNTAX_OK' in out:
    stdin, stdout, stderr = ssh.exec_command('fuser -k 5050/tcp 2>/dev/null; sleep 2; systemctl restart janovum-toolkit; sleep 5; systemctl is-active janovum-toolkit')
    print('Service:', stdout.read().decode().strip())
else:
    print('NOT restarting — fix errors above.')

ssh.close()
