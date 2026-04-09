"""Patch server_v2.py signup route to handle pending status + add approve/deny routes.
Run ON VPS: python patch_signup_route.py"""
import sys

SERVER = '/root/janovum-toolkit/platform/server_v2.py'
with open(SERVER, 'r') as f:
    code = f.read()

if 'from core.user_auth import approve_user' in code:
    print('Already patched')
    sys.exit(0)

# 1. Update signup route to show pending message instead of auto-redirecting
old_signup = '''@user_bp.route("/auth/signup", methods=["POST"])
def u_signup():
    from core.user_auth import signup_user
    data = request.json
    result = signup_user(data.get("email", ""), data.get("password", ""), data.get("name", ""))
    if "error" in result:
        return jsonify(result), 400
    session["user_id"] = result["user_id"]
    session["user_email"] = result["email"]
    session["user_name"] = result["name"]
    return jsonify(result)'''

new_signup = '''@user_bp.route("/auth/signup", methods=["POST"])
def u_signup():
    from core.user_auth import signup_user
    data = request.json
    result = signup_user(data.get("email", ""), data.get("password", ""), data.get("name", ""))
    if "error" in result:
        return jsonify(result), 400
    # If pending approval, don't set session — they can't use the toolkit yet
    if result.get("status") == "pending":
        return jsonify(result)
    # If already approved (legacy), set session
    session["user_id"] = result["user_id"]
    session["user_email"] = result["email"]
    session["user_name"] = result["name"]
    return jsonify(result)'''

if old_signup in code:
    code = code.replace(old_signup, new_signup)
else:
    print('WARNING: Could not find signup route to update')

# 2. Add approve/deny routes (accessible without login, before if __name__)
approve_routes = '''

# ============ ACCOUNT APPROVAL ROUTES (public - clicked from email) ============
@app.route("/api/users/approve/<user_id>")
def public_user_approve(user_id):
    from core.user_auth import approve_user
    token = request.args.get("token", "")
    success, name, email = approve_user(user_id, token)
    if success:
        return f"""<html><body style='background:#0a0a0a;color:#e0e0e0;font-family:-apple-system,sans-serif;text-align:center;padding:80px'>
        <h1 style='color:#2ecc71;font-size:2em'>Account Approved!</h1>
        <p style='margin-top:16px;font-size:1.1em'><strong style='color:#ff6b35'>{name}</strong> ({email}) now has full access to the Janovum toolkit.</p>
        <p style='color:#888;margin-top:12px'>They have been sent a welcome email with login instructions.</p>
        </body></html>"""
    return "<html><body style='background:#0a0a0a;color:#e0e0e0;text-align:center;padding:80px'><h1 style='color:#ff5252'>Invalid or Expired Link</h1><p style='color:#888'>This approval link may have already been used.</p></body></html>", 400

@app.route("/api/users/deny/<user_id>")
def public_user_deny(user_id):
    from core.user_auth import deny_user
    token = request.args.get("token", "")
    success, name = deny_user(user_id, token)
    if success:
        return f"""<html><body style='background:#0a0a0a;color:#e0e0e0;font-family:-apple-system,sans-serif;text-align:center;padding:80px'>
        <h1 style='color:#ff5252;font-size:2em'>Account Denied</h1>
        <p style='margin-top:16px;font-size:1.1em'>{name} has been denied access.</p>
        </body></html>"""
    return "<html><body style='background:#0a0a0a;color:#e0e0e0;text-align:center;padding:80px'><h1 style='color:#ff5252'>Invalid Link</h1></body></html>", 400

@app.route("/api/users/pending")
def public_user_list_pending():
    from core.user_auth import list_all_users
    return jsonify(list_all_users())

'''

marker = 'if __name__ == "__main__":'
if 'public_user_approve' not in code and marker in code:
    code = code.replace(marker, approve_routes + marker)
else:
    print('WARNING: Could not insert approve routes')

with open(SERVER, 'w') as f:
    f.write(code)
print('PATCHED server_v2.py signup + approve routes')
