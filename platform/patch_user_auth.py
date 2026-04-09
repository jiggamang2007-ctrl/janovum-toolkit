"""Patch user_auth.py to add pending/approval queue.
Run ON VPS: python patch_user_auth.py"""
import sys
from pathlib import Path

AUTH_FILE = Path('/root/janovum-toolkit/platform/core/user_auth.py')
code = AUTH_FILE.read_text()

if '"status": "pending"' in code:
    print('Already patched')
    sys.exit(0)

# 1. Replace signup to set status=pending and email admin
old = '''    users[email] = {
        "user_id": user_id,
        "name": name or email.split("@")[0],
        "salt": salt,
        "password_hash": pw_hash,
        "created_at": datetime.now().isoformat(),
    }
    _save_users(users)
    _create_user_directory(user_id)

    return {"user_id": user_id, "email": email, "name": users[email]["name"]}'''

new = '''    approval_token = secrets.token_hex(24)
    users[email] = {
        "user_id": user_id,
        "name": name or email.split("@")[0],
        "salt": salt,
        "password_hash": pw_hash,
        "created_at": datetime.now().isoformat(),
        "status": "pending",
        "approval_token": approval_token,
    }
    _save_users(users)

    # Send approval email to admin
    _send_approval_email(email, users[email], approval_token)

    return {"user_id": user_id, "email": email, "name": users[email]["name"], "status": "pending", "message": "Account created! Waiting for admin approval. You will receive an email when approved."}'''

if old not in code:
    print('ERROR: Could not find signup code to replace')
    sys.exit(1)
code = code.replace(old, new)

# 2. Add approval check to login
old_login = '    return {"user_id": user["user_id"], "email": email, "name": user["name"]}'
new_login = '''    status = user.get("status", "approved")
    if status == "pending":
        return {"error": "Your account is pending approval. You will receive an email when approved.", "status": "pending"}
    if status == "denied":
        return {"error": "Your account request was denied. Contact janovumllc@gmail.com for help.", "status": "denied"}

    return {"user_id": user["user_id"], "email": email, "name": user["name"], "status": "approved"}'''

code = code.replace(old_login, new_login)

# 3. Add helper functions at the end
code += '''


def _send_approval_email(email, user_data, token):
    """Send approval request to admin."""
    try:
        import smtplib
        from email.mime.text import MIMEText
        user_id = user_data["user_id"]
        name = user_data["name"]
        approve_url = f"https://janovum.com/api/users/approve/{user_id}?token={token}"
        deny_url = f"https://janovum.com/api/users/deny/{user_id}?token={token}"
        body = (
            f"New Janovum Toolkit Account Request!\\n\\n"
            f"Name: {name}\\n"
            f"Email: {email}\\n\\n"
            f"APPROVE this account:\\n{approve_url}\\n\\n"
            f"DENY this account:\\n{deny_url}\\n\\n"
            f"(Click approve to give them full access to the Janovum toolkit)"
        )
        msg = MIMEText(body)
        msg["Subject"] = f"[Janovum] New Account Request - {name}"
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
        print(f"[!] Approval email error: {e}")


def approve_user(user_id, token):
    """Approve a pending user account."""
    users = _load_users()
    for email, u in users.items():
        if u["user_id"] == user_id and u.get("approval_token") == token:
            u["status"] = "approved"
            u["approved_at"] = datetime.now().isoformat()
            _save_users(users)
            _create_user_directory(user_id)
            # Send welcome email
            try:
                import smtplib
                from email.mime.text import MIMEText
                msg = MIMEText(
                    f"Hi {u['name']},\\n\\n"
                    f"Your Janovum toolkit account has been approved!\\n\\n"
                    f"Log in at: https://janovum.com/toolkit/use/login\\n\\n"
                    f"Welcome to the future of AI automation.\\n\\n"
                    f"- Janovum Team"
                )
                msg["Subject"] = "Your Janovum Account is Approved!"
                msg["From"] = "myfriendlyagent12@gmail.com"
                msg["To"] = email
                with smtplib.SMTP("smtp.gmail.com", 587) as s:
                    s.starttls()
                    s.login("myfriendlyagent12@gmail.com", "pdcvjroclstugncx")
                    s.send_message(msg)
            except Exception:
                pass
            return True, u["name"], email
    return False, None, None


def deny_user(user_id, token):
    """Deny a pending user account."""
    users = _load_users()
    for email, u in users.items():
        if u["user_id"] == user_id and u.get("approval_token") == token:
            u["status"] = "denied"
            _save_users(users)
            return True, u["name"]
    return False, None


def list_all_users():
    """Get all users with status."""
    users = _load_users()
    return [
        {"email": email, "name": u["name"], "user_id": u["user_id"],
         "created_at": u.get("created_at"), "status": u.get("status", "approved")}
        for email, u in users.items()
    ]
'''

AUTH_FILE.write_text(code)
print('PATCHED user_auth.py successfully')
