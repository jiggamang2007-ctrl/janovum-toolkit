"""
Adds operator signup/login routes to server_v2.py on VPS.
Append-only — safe, touches nothing existing.
"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('104.238.133.244', username='root', password='Ek2+X-HhF5-g{EJ7')
sftp = ssh.open_sftp()

with sftp.open('/root/janovum-toolkit/platform/server_v2.py', 'r') as f:
    server = f.read().decode('utf-8')

if '# ── OPERATOR AUTH' in server:
    print('Operator auth routes already exist. Skipping.')
    sftp.close(); ssh.close(); exit()

OPERATOR_AUTH = '''

# ─────────────────────────────────────────────────────────────────────────────
# OPERATOR AUTH — signup, login, me
# ─────────────────────────────────────────────────────────────────────────────
import hashlib as _hashlib

_OPERATORS_FILE = os.path.join(PLATFORM_DIR, "data", "operators.json")

def _op_auth_load():
    if os.path.exists(_OPERATORS_FILE):
        with open(_OPERATORS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []

def _op_auth_save(ops):
    os.makedirs(os.path.dirname(_OPERATORS_FILE), exist_ok=True)
    with open(_OPERATORS_FILE, "w", encoding="utf-8") as f:
        json.dump(ops, f, indent=2)

def _hash_pw(pw):
    return _hashlib.sha256(pw.encode()).hexdigest()

@app.route("/api/operators/signup", methods=["POST"])
def operator_signup():
    data     = request.json or {}
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name     = data.get("name") or ""
    agency   = data.get("agency_name") or ""
    phone    = data.get("phone") or ""
    plan     = data.get("plan") or "starter"

    if not email or not password or not name:
        return jsonify({"error": "Name, email, and password are required"}), 400

    ops = _op_auth_load()
    if any(o.get("email") == email for o in ops):
        return jsonify({"error": "An account with this email already exists"}), 409

    token = str(uuid.uuid4())
    op = {
        "id":          str(uuid.uuid4()),
        "email":       email,
        "password":    _hash_pw(password),
        "name":        name,
        "agency_name": agency,
        "phone":       phone,
        "plan":        plan,
        "token":       token,
        "created":     datetime.utcnow().isoformat() + "Z",
        "status":      "active",
    }
    ops.append(op)
    _op_auth_save(ops)

    # Send welcome email
    try:
        import smtplib
        from email.mime.text import MIMEText
        body = f"""Hi {name},

Welcome to Janovum! Your operator account is live.

Plan: {plan.title()}
Operator Hub: https://janovum.com/operator

You now have access to the full toolkit. Start signing clients — we built the tech, you sell it.

Questions? Reply to this email.

- The Janovum Team
"""
        msg = MIMEText(body)
        msg['Subject'] = f'Welcome to Janovum, {name.split()[0]}!'
        msg['From']    = 'myfriendlyagent12@gmail.com'
        msg['To']      = email
        with smtplib.SMTP('smtp.gmail.com', 587) as s:
            s.starttls()
            s.login('myfriendlyagent12@gmail.com', 'pdcvjroclstugncx')
            s.send_message(msg)
        print(f"[Signup] Welcome email sent to {email}")
    except Exception as e:
        print(f"[Signup] Email failed: {e}")

    safe_op = {k: v for k, v in op.items() if k != "password"}
    return jsonify({"ok": True, "token": token, "operator": safe_op})


@app.route("/api/operators/login", methods=["POST"])
def operator_login():
    data  = request.json or {}
    email = (data.get("email") or "").strip().lower()
    pw    = data.get("password") or ""
    ops   = _op_auth_load()
    op    = next((o for o in ops if o.get("email") == email), None)
    if not op or op.get("password") != _hash_pw(pw):
        return jsonify({"error": "Invalid email or password"}), 401
    op["token"] = str(uuid.uuid4())
    _op_auth_save(ops)
    safe_op = {k: v for k, v in op.items() if k != "password"}
    return jsonify({"ok": True, "token": op["token"], "operator": safe_op})


@app.route("/api/operators/me", methods=["GET"])
def operator_me():
    token = request.headers.get("X-Op-Token") or request.args.get("token", "")
    if not token:
        return jsonify({"error": "No token"}), 401
    ops = _op_auth_load()
    op  = next((o for o in ops if o.get("token") == token), None)
    if not op:
        return jsonify({"error": "Invalid token"}), 401
    safe_op = {k: v for k, v in op.items() if k != "password"}
    return jsonify(safe_op)


@app.route("/api/operators/list", methods=["GET"])
def operator_list():
    ops = _op_auth_load()
    safe = [{k: v for k, v in o.items() if k != "password"} for o in ops]
    return jsonify({"count": len(safe), "operators": safe})
'''

# Insert before OPERATOR PLATFORM or PROACTIVE AGENT or app.run
markers = ['# ── OPERATOR PLATFORM', '# ── PROACTIVE AGENT', 'if __name__ == "__main__"', "if __name__ == '__main__'"]
insert_pos = -1
for m in markers:
    idx = server.find(m)
    if idx != -1:
        insert_pos = idx
        break

if insert_pos == -1:
    new_server = server + OPERATOR_AUTH
else:
    new_server = server[:insert_pos] + OPERATOR_AUTH + '\n' + server[insert_pos:]

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
    print('NOT restarting — fix errors first.')

ssh.close()
