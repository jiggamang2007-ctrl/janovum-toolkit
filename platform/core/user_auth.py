"""
Janovum User Authentication
Simple email/password accounts for multi-tenant toolkit access.
Users get isolated data directories — no access to admin data.
"""

import json
import os
import hashlib
import secrets
from pathlib import Path
from datetime import datetime

PLATFORM_DIR = Path(__file__).parent.parent
USERS_DIR = PLATFORM_DIR / "data" / "users"
USERS_FILE = USERS_DIR / "users.json"


def _ensure_dirs():
    USERS_DIR.mkdir(parents=True, exist_ok=True)


def _load_users():
    _ensure_dirs()
    if USERS_FILE.exists():
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_users(users):
    _ensure_dirs()
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)


def _hash_password(password, salt=None):
    """PBKDF2 with random salt."""
    if salt is None:
        salt = secrets.token_hex(32)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return salt, dk.hex()


def _verify_password(password, salt, stored_hash):
    _, computed = _hash_password(password, salt)
    return computed == stored_hash


def _generate_user_id(name, email):
    """Generate a clean user ID from name or email."""
    base = name if name else email.split("@")[0]
    clean = "".join(c if c.isalnum() else "_" for c in base.lower()).strip("_")
    while "__" in clean:
        clean = clean.replace("__", "_")
    uid = clean[:20]
    # Ensure uniqueness
    users = _load_users()
    existing_ids = {u["user_id"] for u in users.values()}
    if uid not in existing_ids:
        return uid
    counter = 2
    while f"{uid}_{counter}" in existing_ids:
        counter += 1
    return f"{uid}_{counter}"


def _create_user_directory(user_id):
    """Create isolated data directory with default templates for a new user."""
    user_dir = USERS_DIR / user_id
    subdirs = ["clients", "clients/logs", "clients/pids", "auth", "costs", "conversations"]
    for sub in subdirs:
        (user_dir / sub).mkdir(parents=True, exist_ok=True)

    # Default empty clients index
    idx_path = user_dir / "clients" / "clients_index.json"
    if not idx_path.exists():
        with open(idx_path, "w", encoding="utf-8") as f:
            json.dump([], f)

    # Default toolkit config (empty — user fills in their own Twilio creds)
    tk_path = user_dir / "toolkit_config.json"
    if not tk_path.exists():
        with open(tk_path, "w", encoding="utf-8") as f:
            json.dump({
                "domain": "",
                "twilio_account_sid": "",
                "twilio_auth_token": "",
                "auto_update_webhooks": True,
                "setup_complete": False,
            }, f, indent=2)

    # Default global config
    cfg_path = user_dir / "config.json"
    if not cfg_path.exists():
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump({
                "api_key": "",
                "model": "claude-sonnet-4-20250514",
                "max_monthly_spend_per_client": 300,
                "server_port": 5050,
                "modules_enabled": {},
            }, f, indent=2)

    # User profile
    profile_path = user_dir / "profile.json"
    if not profile_path.exists():
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump({"user_id": user_id, "created_at": datetime.now().isoformat()}, f, indent=2)


def signup_user(email, password, name=""):
    """Create a new user account. Returns {user_id, email, name} or {error}."""
    email = email.strip().lower()
    name = name.strip()

    if not email or "@" not in email:
        return {"error": "Valid email is required"}
    if not password or len(password) < 6:
        return {"error": "Password must be at least 6 characters"}

    users = _load_users()
    if email in users:
        return {"error": "An account with this email already exists"}

    user_id = _generate_user_id(name, email)
    salt, pw_hash = _hash_password(password)

    users[email] = {
        "user_id": user_id,
        "name": name or email.split("@")[0],
        "salt": salt,
        "password_hash": pw_hash,
        "created_at": datetime.now().isoformat(),
    }
    _save_users(users)
    _create_user_directory(user_id)

    return {"user_id": user_id, "email": email, "name": users[email]["name"]}


def login_user(email, password):
    """Validate credentials. Returns {user_id, email, name} or {error}."""
    email = email.strip().lower()
    users = _load_users()

    if email not in users:
        return {"error": "Invalid email or password"}

    user = users[email]
    if not _verify_password(password, user["salt"], user["password_hash"]):
        return {"error": "Invalid email or password"}

    return {"user_id": user["user_id"], "email": email, "name": user["name"]}


def get_user_profile(user_id):
    """Get user profile info."""
    profile_path = USERS_DIR / user_id / "profile.json"
    if profile_path.exists():
        with open(profile_path, "r", encoding="utf-8") as f:
            profile = json.load(f)
    else:
        profile = {"user_id": user_id}

    # Also get email/name from users index
    users = _load_users()
    for email, u in users.items():
        if u["user_id"] == user_id:
            profile["email"] = email
            profile["name"] = u.get("name", "")
            break

    return profile


def get_user_data_dir(user_id):
    """Get the base data directory for a user."""
    return USERS_DIR / user_id
