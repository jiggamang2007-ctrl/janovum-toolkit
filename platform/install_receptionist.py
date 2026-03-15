"""
Janovum Platform — AI Receptionist Installer
Installs all required packages for the receptionist pipeline.

Usage:
  python install_receptionist.py
"""

import subprocess
import sys


def install():
    packages = [
        # Pipecat with required extras
        "pipecat-ai[cartesia,whisper,silero,telnyx]",
        # FastAPI server
        "fastapi",
        "uvicorn[standard]",
        # Logging
        "loguru",
        # WebSocket support
        "websockets",
        # Audio processing
        "numpy",
        # Telnyx REST API (for call control)
        "telnyx",
    ]

    print("=" * 60)
    print("  Janovum AI Receptionist — Installing Dependencies")
    print("=" * 60)
    print()

    for pkg in packages:
        print(f"  Installing: {pkg}")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"    WARNING: Failed to install {pkg}")
            print(f"    {result.stderr.strip()[:200]}")
        else:
            print(f"    OK")

    print()
    print("=" * 60)
    print("  Installation complete!")
    print()
    print("  To start the receptionist server:")
    print("    python receptionist_server.py")
    print()
    print("  The server runs on port 5051.")
    print("  Configure your Telnyx TeXML app webhook to:")
    print("    POST https://your-domain.com/incoming")
    print()
    print("  For local testing with ngrok:")
    print("    ngrok http 5051")
    print("    Then set Telnyx webhook to the ngrok URL + /incoming")
    print("=" * 60)


if __name__ == "__main__":
    install()
