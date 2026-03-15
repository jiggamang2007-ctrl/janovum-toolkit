"""
Janovum Platform — Configuration Manager
Stores API key, active modules, and client settings.
"""

import json
import os

CONFIG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "api_key": "",
    "model": "claude-sonnet-4-20250514",
    "max_monthly_spend_per_client": 300,
    "server_port": 5050,
    "modules_enabled": {}
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
        # merge with defaults for any missing keys
        for k, v in DEFAULT_CONFIG.items():
            if k not in cfg:
                cfg[k] = v
        return cfg
    return dict(DEFAULT_CONFIG)


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def get_api_key():
    return load_config().get("api_key", "")


def set_api_key(key):
    cfg = load_config()
    cfg["api_key"] = key
    save_config(cfg)


def get_model():
    return load_config().get("model", "claude-sonnet-4-20250514")


def set_model(model):
    cfg = load_config()
    cfg["model"] = model
    save_config(cfg)
