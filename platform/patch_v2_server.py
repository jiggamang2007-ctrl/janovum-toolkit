"""Patch server_v2.py on VPS to add memecoin trader routes and user signup system.
Run this ON the VPS: python patch_v2_server.py"""
import os, sys

SERVER = '/root/janovum-toolkit/platform/server_v2.py'

with open(SERVER, 'r') as f:
    code = f.read()

if 'memecoin_trader' in code:
    print('Already patched - skipping')
    sys.exit(0)

# Add import secrets at top
if 'import secrets' not in code:
    code = code.replace('from datetime import datetime', 'from datetime import datetime\nimport secrets', 1)

# The block to insert before if __name__
BLOCK = '''

# ============ MEMECOIN TRADER ROUTES ============
try:
    from modules.memecoin_trader import register_routes as _reg_trader
    _reg_trader(app)
    print("[+] Memecoin Trader routes registered")
except Exception as _e:
    print(f"[!] Trader routes failed: {_e}")

# ============ USER SIGNUP + APPROVAL SYSTEM ============
_USERS_FILE = os.path.join(PLATFORM_DIR, "data", "users", "users.json")
os.makedirs(os.path.dirname(_USERS_FILE), exist_ok=True)

def _load_users():
    if os.path.exists(_USERS_FILE):
        try:
            with open(_USERS_FILE) as f:
                return json.load(f)
        except:
            pass
    return {}

def _save_users(u):
    with open(_USERS_FILE, "w") as f:
        json.dump(u, f, indent=2)

@app.route("/api/users/signup", methods=["POST"])
def user_signup():
    data = request.json or {}
    name = data.get("name","").strip()
    email = data.get("email","").strip()
    pw = data.get("password","")
    if not name or not email or not pw:
        return jsonify({"error": "Name, email, password required"}), 400
    users = _load_users()
    import hashlib
    for uid, u in users.items():
        if u.get("email","").lower() == email.lower():
            return jsonify({"error": f"Account already {u.get('status','exists')}"}), 400
    user_id = hashlib.md5(email.lower().encode()).hexdigest()[:12]
    token = secrets.token_urlsafe(32)
    pw_hash = hashlib.sha256(pw.encode()).hexdigest()
    user = {"id": user_id, "name": name, "email": email.lower(), "password_hash": pw_hash,
            "company": data.get("company",""), "reason": data.get("reason",""),
            "status": "pending", "approval_token": token,
            "created_at": datetime.now().isoformat(), "approved_at": None, "role": "user"}
    users[user_id] = user
    _save_users(users)
    try:
        import smtplib
        from email.mime.text import MIMEText
        approve_url = f"https://janovum.com/api/users/approve/{user_id}?token={token}"
        deny_url = f"https://janovum.com/api/users/deny/{user_id}?token={token}"
        body = f"New Janovum Account Request!\\n\\nName: {name}\\nEmail: {email}\\nCompany: {data.get('company','')}\\n\\nAPPROVE: {approve_url}\\n\\nDENY: {deny_url}"
        msg = MIMEText(body)
        msg["Subject"] = f"[Janovum] Account Request - {name}"
        msg["From"] = "myfriendlyagent12@gmail.com"
        msg["To"] = "myfriendlyagent12@gmail.com"
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.starttls()
            s.login("myfriendlyagent12@gmail.com", "pdcvjroclstugncx")
            s.send_message(msg)
            msg2 = MIMEText(body)
            msg2["Subject"] = msg["Subject"]
            msg2["From"] = "myfriendlyagent12@gmail.com"
            msg2["To"] = "janovumllc@gmail.com"
            s.send_message(msg2)
    except Exception as e:
        print(f"[!] Signup email error: {e}")
    return jsonify({"status": "pending", "message": "Account created! Waiting for admin approval."})

@app.route("/api/users/login", methods=["POST"])
def user_login():
    data = request.json or {}
    email = data.get("email","").strip().lower()
    pw = data.get("password","")
    if not email or not pw:
        return jsonify({"error": "Email and password required"}), 400
    import hashlib
    pw_hash = hashlib.sha256(pw.encode()).hexdigest()
    users = _load_users()
    for uid, u in users.items():
        if u.get("email") == email:
            if u.get("password_hash") != pw_hash:
                return jsonify({"error": "Wrong password"}), 401
            if u.get("status") != "approved":
                return jsonify({"error": f"Account {u.get('status','not approved')}", "status": u.get("status")}), 403
            tok = secrets.token_urlsafe(32)
            u["session_token"] = tok
            u["last_login"] = datetime.now().isoformat()
            _save_users(users)
            return jsonify({"status": "approved", "token": tok, "user": {"id": uid, "name": u["name"], "email": u["email"], "role": u.get("role","user")}})
    return jsonify({"error": "Account not found"}), 404

@app.route("/api/users/approve/<user_id>")
def user_approve(user_id):
    token = request.args.get("token","")
    users = _load_users()
    if user_id not in users or users[user_id].get("approval_token") != token:
        return "<html><body style='background:#0a0a0a;color:#e0e0e0;text-align:center;padding:80px'><h1 style='color:#ff5252'>Invalid Link</h1></body></html>", 400
    users[user_id]["status"] = "approved"
    users[user_id]["approved_at"] = datetime.now().isoformat()
    _save_users(users)
    name = users[user_id]["name"]
    try:
        import smtplib
        from email.mime.text import MIMEText
        msg = MIMEText(f"Hi {name},\\n\\nYour Janovum account is approved! Log in at https://janovum.com\\n\\n- Janovum Team")
        msg["Subject"] = "Janovum Account Approved!"
        msg["From"] = "myfriendlyagent12@gmail.com"
        msg["To"] = users[user_id]["email"]
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.starttls()
            s.login("myfriendlyagent12@gmail.com", "pdcvjroclstugncx")
            s.send_message(msg)
    except:
        pass
    return f"<html><body style='background:#0a0a0a;color:#e0e0e0;font-family:sans-serif;text-align:center;padding:80px'><h1 style='color:#2ecc71'>Approved!</h1><p>{name} now has full access.</p></body></html>"

@app.route("/api/users/deny/<user_id>")
def user_deny(user_id):
    token = request.args.get("token","")
    users = _load_users()
    if user_id not in users or users[user_id].get("approval_token") != token:
        return "<html><body style='background:#0a0a0a;color:#e0e0e0;text-align:center;padding:80px'><h1 style='color:#ff5252'>Invalid Link</h1></body></html>", 400
    users[user_id]["status"] = "denied"
    _save_users(users)
    return f"<html><body style='background:#0a0a0a;color:#e0e0e0;font-family:sans-serif;text-align:center;padding:80px'><h1 style='color:#ff5252'>Denied</h1><p>{users[user_id]['name']} has been denied.</p></body></html>"

@app.route("/api/users/verify", methods=["POST"])
def user_verify():
    data = request.json or {}
    tok = data.get("token","")
    if not tok:
        return jsonify({"valid": False})
    users = _load_users()
    for uid, u in users.items():
        if u.get("session_token") == tok and u.get("status") == "approved":
            return jsonify({"valid": True, "user": {"id": uid, "name": u["name"], "email": u["email"], "role": u.get("role","user")}})
    return jsonify({"valid": False})

@app.route("/api/users/list")
def user_list():
    users = _load_users()
    return jsonify([{"id": uid, "name": u.get("name"), "email": u.get("email"), "status": u.get("status"), "created_at": u.get("created_at"), "role": u.get("role","user")} for uid, u in users.items()])

'''

# Insert before if __name__
marker = 'if __name__ == "__main__":'
if marker in code:
    code = code.replace(marker, BLOCK + '\n' + marker)
    with open(SERVER, 'w') as f:
        f.write(code)
    print('PATCHED server_v2.py successfully')
else:
    print('ERROR: Could not find __main__ marker')
