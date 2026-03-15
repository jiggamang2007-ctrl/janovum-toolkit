"""
Janovum Platform — Quick Start
Run this to start everything: python run.py

Dashboard opens at http://localhost:5050
"""

import subprocess
import sys
import os

PLATFORM_DIR = os.path.dirname(os.path.abspath(__file__))

def check_requirements():
    """Check if required packages are installed."""
    missing = []
    try:
        import flask
    except ImportError:
        missing.append("flask")
    try:
        import requests
    except ImportError:
        missing.append("requests")

    if missing:
        print(f"Installing missing packages: {', '.join(missing)}")
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
        print("Done!")

def main():
    check_requirements()

    print()
    print("=" * 50)
    print("  JANOVUM PLATFORM")
    print("  Starting server...")
    print("=" * 50)
    print()

    # Start the Flask server
    server_path = os.path.join(PLATFORM_DIR, "server.py")
    os.chdir(PLATFORM_DIR)
    subprocess.call([sys.executable, server_path])

if __name__ == "__main__":
    main()
