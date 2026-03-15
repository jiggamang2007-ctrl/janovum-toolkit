#!/usr/bin/env python3
"""
Janovum Platform — One-Command Installer
Run with: python install.py
"""

import os
import sys
import json
import subprocess
import shutil

PLATFORM_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(PLATFORM_DIR, "venv")
REQUIREMENTS = os.path.join(PLATFORM_DIR, "requirements.txt")
CONFIG_FILE = os.path.join(PLATFORM_DIR, "config.json")

# Data directories the platform expects
DATA_DIRS = [
    "data/audio",
    "data/bots",
    "data/conversations",
    "data/costs",
    "data/traces",
    "data/approvals",
    "data/auth",
    "data/sandbox",
    "logs",
    "agent_screenshots",
]

DEFAULT_CONFIG = {
    "api_key": "",
    "model": "claude-sonnet-4-20250514",
    "max_monthly_spend_per_client": 300,
    "server_port": 5050,
    "modules_enabled": {},
}


def check_python_version():
    """Ensure Python 3.10+ is being used."""
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 10):
        print(f"ERROR: Python 3.10+ is required. You have {major}.{minor}.")
        print("Download the latest Python from https://www.python.org/downloads/")
        sys.exit(1)
    print(f"[OK] Python {major}.{minor} detected.")


def create_virtualenv():
    """Create a virtual environment if one doesn't exist."""
    if os.path.isdir(VENV_DIR):
        print(f"[OK] Virtual environment already exists at {VENV_DIR}")
        return

    print("[..] Creating virtual environment...")
    subprocess.check_call([sys.executable, "-m", "venv", VENV_DIR])
    print(f"[OK] Virtual environment created at {VENV_DIR}")


def get_pip_executable():
    """Return the pip executable path inside the venv."""
    if sys.platform == "win32":
        return os.path.join(VENV_DIR, "Scripts", "pip.exe")
    return os.path.join(VENV_DIR, "bin", "pip")


def get_python_executable():
    """Return the python executable path inside the venv."""
    if sys.platform == "win32":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    return os.path.join(VENV_DIR, "bin", "python")


def install_requirements():
    """Install all Python dependencies from requirements.txt."""
    pip = get_pip_executable()
    if not os.path.isfile(pip):
        print("ERROR: pip not found in virtual environment. Try deleting venv/ and re-running.")
        sys.exit(1)

    print("[..] Upgrading pip...")
    subprocess.check_call([pip, "install", "--upgrade", "pip"], stdout=subprocess.DEVNULL)

    print("[..] Installing dependencies from requirements.txt...")
    subprocess.check_call([pip, "install", "-r", REQUIREMENTS])
    print("[OK] All dependencies installed.")


def create_data_directories():
    """Create all required data directories."""
    print("[..] Creating data directories...")
    for d in DATA_DIRS:
        full_path = os.path.join(PLATFORM_DIR, d)
        os.makedirs(full_path, exist_ok=True)
    print(f"[OK] {len(DATA_DIRS)} directories ready.")


def create_default_config():
    """Write config.json if it doesn't already exist."""
    if os.path.isfile(CONFIG_FILE):
        print(f"[OK] config.json already exists — skipping.")
        return

    with open(CONFIG_FILE, "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    print(f"[OK] Default config.json created.")


def print_success():
    """Print final instructions."""
    python = get_python_executable()
    activate_cmd = (
        os.path.join(VENV_DIR, "Scripts", "activate")
        if sys.platform == "win32"
        else f"source {os.path.join(VENV_DIR, 'bin', 'activate')}"
    )

    print()
    print("=" * 56)
    print("  JANOVUM PLATFORM — INSTALLED SUCCESSFULLY")
    print("=" * 56)
    print()
    print("  Next steps:")
    print()
    print(f"  1. Activate the virtual environment:")
    print(f"     {activate_cmd}")
    print()
    print(f"  2. Set your Anthropic API key in config.json")
    print(f"     or set the ANTHROPIC_API_KEY env variable.")
    print()
    print(f"  3. Start the server:")
    print(f"     python server_v5.py")
    print()
    print(f"  4. Open the dashboard:")
    print(f"     http://localhost:5050")
    print()
    print("=" * 56)


def main():
    print()
    print("=== Janovum Platform Installer ===")
    print()

    check_python_version()
    create_virtualenv()
    install_requirements()
    create_data_directories()
    create_default_config()
    print_success()


if __name__ == "__main__":
    main()
