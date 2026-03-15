"""
Janovum Platform — Authentication System
Supports two ways to connect:
  1. API Key — paste your Claude API key (developer mode)
  2. OAuth — "Sign in with Claude" using your existing subscription (consumer mode)

OAuth Flow:
  1. User clicks "Sign in with Claude" on the toolkit dashboard
  2. Redirected to Anthropic's OAuth consent page
  3. User approves access
  4. Anthropic redirects back with an auth code
  5. We exchange the code for access + refresh tokens
  6. Tokens stored securely per-client
  7. API calls use the OAuth token instead of API key

This means anyone with a Claude Pro/Max/Team subscription can use the toolkit
without paying extra for API access!
"""

import json
import os
import time
import secrets
import hashlib
import requests
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs

PLATFORM_DIR = Path(__file__).parent.parent
AUTH_DIR = PLATFORM_DIR / "data" / "auth"
OAUTH_CONFIG_FILE = PLATFORM_DIR / "oauth_config.json"

# Anthropic OAuth endpoints
ANTHROPIC_AUTH_URL = "https://console.anthropic.com/oauth/authorize"
ANTHROPIC_TOKEN_URL = "https://console.anthropic.com/oauth/token"
ANTHROPIC_USERINFO_URL = "https://api.anthropic.com/v1/oauth/userinfo"

# Default OAuth config — these get set when the developer registers their app with Anthropic
DEFAULT_OAUTH_CONFIG = {
    "client_id": "",       # Set this after registering with Anthropic
    "client_secret": "",   # Set this after registering with Anthropic
    "redirect_uri": "http://localhost:5050/auth/callback",
    "scopes": ["user:read", "messages:write"],
}


class AuthMethod:
    API_KEY = "api_key"
    OAUTH = "oauth"


class AuthToken:
    """Stores OAuth tokens for a user/client."""

    def __init__(self, client_id, access_token, refresh_token=None, expires_at=None, user_info=None):
        self.client_id = client_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = expires_at  # Unix timestamp
        self.user_info = user_info or {}
        self.created_at = datetime.now().isoformat()
        self.last_used = None
        self.total_calls = 0

    def is_expired(self):
        if not self.expires_at:
            return False
        return time.time() >= self.expires_at

    def to_dict(self):
        return {
            "client_id": self.client_id,
            "access_token": self.access_token[:8] + "..." if self.access_token else None,
            "has_refresh": bool(self.refresh_token),
            "expires_at": self.expires_at,
            "is_expired": self.is_expired(),
            "user_info": self.user_info,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "total_calls": self.total_calls,
            "auth_method": AuthMethod.OAUTH
        }


class AuthManager:
    """
    Manages authentication for the platform.
    Supports API key and OAuth methods.
    """

    def __init__(self):
        AUTH_DIR.mkdir(parents=True, exist_ok=True)
        self.tokens = {}  # client_id -> AuthToken
        self.pending_states = {}  # state -> {client_id, created_at, code_verifier}
        self._load_tokens()
        self.oauth_config = self._load_oauth_config()

    def _load_oauth_config(self):
        """Load OAuth client config."""
        if OAUTH_CONFIG_FILE.exists():
            try:
                return json.loads(OAUTH_CONFIG_FILE.read_text())
            except Exception:
                pass
        return dict(DEFAULT_OAUTH_CONFIG)

    def save_oauth_config(self, config):
        """Save OAuth client config (client_id, client_secret, etc.)."""
        self.oauth_config.update(config)
        OAUTH_CONFIG_FILE.write_text(json.dumps(self.oauth_config, indent=2))

    def is_oauth_configured(self):
        """Check if OAuth is set up (client_id and secret are set)."""
        return bool(self.oauth_config.get("client_id") and self.oauth_config.get("client_secret"))

    # ── API KEY AUTH ──

    def get_api_key(self, client_id=None):
        """Get the API key for a client (falls back to global key)."""
        from core.config import get_api_key
        # Check client-specific key first
        if client_id:
            client_auth = self._load_client_auth(client_id)
            if client_auth.get("api_key"):
                return client_auth["api_key"]
        # Fall back to global
        return get_api_key()

    def set_client_api_key(self, client_id, api_key):
        """Set a client-specific API key."""
        auth_data = self._load_client_auth(client_id)
        auth_data["api_key"] = api_key
        auth_data["auth_method"] = AuthMethod.API_KEY
        self._save_client_auth(client_id, auth_data)

    # ── OAUTH AUTH ──

    def get_oauth_url(self, client_id):
        """
        Generate the OAuth authorization URL.
        Returns (url, state) — redirect the user to this URL.
        """
        if not self.is_oauth_configured():
            return None, "OAuth not configured. Set client_id and client_secret first."

        # Generate PKCE code verifier and challenge
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = hashlib.sha256(code_verifier.encode()).hexdigest()

        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        self.pending_states[state] = {
            "client_id": client_id,
            "created_at": time.time(),
            "code_verifier": code_verifier
        }

        # Clean up old pending states (>10 min)
        self._cleanup_pending_states()

        params = {
            "client_id": self.oauth_config["client_id"],
            "redirect_uri": self.oauth_config["redirect_uri"],
            "response_type": "code",
            "scope": " ".join(self.oauth_config.get("scopes", ["user:read", "messages:write"])),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }

        url = f"{ANTHROPIC_AUTH_URL}?{urlencode(params)}"
        return url, state

    def handle_oauth_callback(self, code, state):
        """
        Handle the OAuth callback after user approves.
        Exchange the auth code for tokens.
        Returns (AuthToken, error_message)
        """
        if state not in self.pending_states:
            return None, "Invalid or expired state parameter."

        pending = self.pending_states.pop(state)
        client_id = pending["client_id"]
        code_verifier = pending["code_verifier"]

        # Exchange code for tokens
        try:
            token_data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.oauth_config["redirect_uri"],
                "client_id": self.oauth_config["client_id"],
                "client_secret": self.oauth_config["client_secret"],
                "code_verifier": code_verifier
            }

            resp = requests.post(ANTHROPIC_TOKEN_URL, data=token_data, timeout=30)

            if resp.status_code != 200:
                return None, f"Token exchange failed: {resp.status_code} — {resp.text}"

            data = resp.json()
            access_token = data.get("access_token")
            refresh_token = data.get("refresh_token")
            expires_in = data.get("expires_in", 3600)
            expires_at = time.time() + expires_in

            # Get user info
            user_info = self._get_user_info(access_token)

            # Store token
            token = AuthToken(client_id, access_token, refresh_token, expires_at, user_info)
            self.tokens[client_id] = token
            self._save_token(client_id, token)

            # Also save auth method
            auth_data = self._load_client_auth(client_id)
            auth_data["auth_method"] = AuthMethod.OAUTH
            auth_data["oauth_user"] = user_info
            self._save_client_auth(client_id, auth_data)

            return token, None

        except Exception as e:
            return None, f"OAuth error: {str(e)}"

    def refresh_oauth_token(self, client_id):
        """Refresh an expired OAuth token."""
        token = self.tokens.get(client_id)
        if not token or not token.refresh_token:
            return None, "No refresh token available."

        try:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": token.refresh_token,
                "client_id": self.oauth_config["client_id"],
                "client_secret": self.oauth_config["client_secret"]
            }

            resp = requests.post(ANTHROPIC_TOKEN_URL, data=data, timeout=30)

            if resp.status_code != 200:
                return None, f"Refresh failed: {resp.status_code}"

            result = resp.json()
            token.access_token = result["access_token"]
            if result.get("refresh_token"):
                token.refresh_token = result["refresh_token"]
            token.expires_at = time.time() + result.get("expires_in", 3600)

            self._save_token(client_id, token)
            return token, None

        except Exception as e:
            return None, f"Refresh error: {str(e)}"

    def get_auth_header(self, client_id=None):
        """
        Get the appropriate auth header for API calls.
        Checks OAuth first (auto-refreshes if needed), then falls back to API key.
        Returns dict for use as request headers.
        """
        # Check OAuth token first
        if client_id and client_id in self.tokens:
            token = self.tokens[client_id]
            if token.is_expired() and token.refresh_token:
                self.refresh_oauth_token(client_id)
                token = self.tokens.get(client_id)

            if token and not token.is_expired():
                token.last_used = datetime.now().isoformat()
                token.total_calls += 1
                return {
                    "Authorization": f"Bearer {token.access_token}",
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }

        # Fall back to API key
        api_key = self.get_api_key(client_id)
        if api_key:
            return {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }

        return None

    def get_auth_status(self, client_id=None):
        """Get authentication status for a client."""
        result = {
            "oauth_configured": self.is_oauth_configured(),
            "has_api_key": bool(self.get_api_key(client_id)),
        }

        if client_id and client_id in self.tokens:
            token = self.tokens[client_id]
            result["oauth_connected"] = True
            result["oauth_expired"] = token.is_expired()
            result["oauth_user"] = token.user_info
            result["auth_method"] = AuthMethod.OAUTH
        else:
            result["oauth_connected"] = False
            result["auth_method"] = AuthMethod.API_KEY if result["has_api_key"] else None

        return result

    def disconnect_oauth(self, client_id):
        """Disconnect OAuth for a client."""
        if client_id in self.tokens:
            del self.tokens[client_id]
        token_file = AUTH_DIR / f"{client_id}_token.json"
        if token_file.exists():
            token_file.unlink()
        return True

    # ── HELPERS ──

    def _get_user_info(self, access_token):
        """Get user info from Anthropic OAuth."""
        try:
            resp = requests.get(
                ANTHROPIC_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=15
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {}

    def _cleanup_pending_states(self):
        """Remove expired pending OAuth states (>10 min old)."""
        cutoff = time.time() - 600
        expired = [s for s, d in self.pending_states.items() if d["created_at"] < cutoff]
        for s in expired:
            del self.pending_states[s]

    def _load_client_auth(self, client_id):
        auth_file = AUTH_DIR / f"{client_id}.json"
        if auth_file.exists():
            try:
                return json.loads(auth_file.read_text())
            except Exception:
                pass
        return {"client_id": client_id}

    def _save_client_auth(self, client_id, data):
        auth_file = AUTH_DIR / f"{client_id}.json"
        auth_file.write_text(json.dumps(data, indent=2))

    def _save_token(self, client_id, token):
        token_file = AUTH_DIR / f"{client_id}_token.json"
        data = {
            "client_id": token.client_id,
            "access_token": token.access_token,
            "refresh_token": token.refresh_token,
            "expires_at": token.expires_at,
            "user_info": token.user_info,
            "created_at": token.created_at
        }
        token_file.write_text(json.dumps(data, indent=2))

    def _load_tokens(self):
        """Load all saved OAuth tokens."""
        if AUTH_DIR.exists():
            for f in AUTH_DIR.iterdir():
                if f.name.endswith("_token.json"):
                    try:
                        data = json.loads(f.read_text())
                        token = AuthToken(
                            data["client_id"],
                            data["access_token"],
                            data.get("refresh_token"),
                            data.get("expires_at"),
                            data.get("user_info", {})
                        )
                        token.created_at = data.get("created_at", "")
                        self.tokens[data["client_id"]] = token
                    except Exception:
                        pass


# ── SINGLETON ──
_auth = None

def get_auth():
    """Get the global auth manager instance."""
    global _auth
    if _auth is None:
        _auth = AuthManager()
    return _auth
