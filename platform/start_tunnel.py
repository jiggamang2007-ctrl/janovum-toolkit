"""
Starts a Cloudflare tunnel and saves the URL to a file.
Other processes read this file to know the public URL.
"""
import subprocess
import re
import sys
import time
from pathlib import Path

PLATFORM_DIR = Path(__file__).parent
URL_FILE = PLATFORM_DIR / "data" / "tunnel_url.txt"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5051

print(f"[tunnel] Starting Cloudflare tunnel for port {PORT}...")

CLOUDFLARED = r"C:\Program Files (x86)\cloudflared\cloudflared.exe"

proc = subprocess.Popen(
    [CLOUDFLARED, "tunnel", "--url", f"http://localhost:{PORT}"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)

# Watch output for the tunnel URL
tunnel_url = None
for line in proc.stdout:
    print(line.strip())
    # Cloudflare prints the URL like: https://xxx-xxx.trycloudflare.com
    match = re.search(r'(https://[a-zA-Z0-9\-]+\.trycloudflare\.com)', line)
    if match and not tunnel_url:
        tunnel_url = match.group(1)
        # Strip https:// for the PUBLIC_URL (websocket needs just the domain)
        domain = tunnel_url.replace("https://", "")
        URL_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(URL_FILE, "w") as f:
            f.write(domain)
        print(f"\n[tunnel] URL saved: {domain}")
        print(f"[tunnel] Set Twilio webhook to: {tunnel_url}/incoming")
        print(f"[tunnel] File: {URL_FILE}\n")
