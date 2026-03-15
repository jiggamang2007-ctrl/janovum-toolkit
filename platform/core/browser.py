"""
Janovum Core — Shared Browser Launcher
All modules use this to create Selenium drivers.
Built-in remote debugging so you can watch agents LIVE via Chrome DevTools.

How to watch live:
  1. Agent launches Chrome with --remote-debugging-port
  2. Open a SEPARATE Chrome window (not the headless one)
  3. Go to: chrome://inspect/#devices
  4. Click "inspect" on the page you want to watch
  5. You see the agent's browser LIVE — every click, every scroll, everything

Port assignment:
  - Each agent gets its own port (9222, 9223, 9224, etc.)
  - Ports are tracked so multiple agents can run simultaneously
"""

import os
import sys
import json
import time
import socket
import threading
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Screenshot + metadata directories
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agent_screenshots")
PERSONAL_VIEWER_DIR = os.path.expanduser("~/OneDrive/Desktop/agent_viewer_data")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs(PERSONAL_VIEWER_DIR, exist_ok=True)

# Track active debug ports
_active_ports = {}
_port_lock = threading.Lock()
BASE_DEBUG_PORT = 9222


def _find_free_port(start=9222):
    """Find next available debug port."""
    port = start
    while port < start + 50:
        with _port_lock:
            if port in _active_ports.values():
                port += 1
                continue
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex(("127.0.0.1", port))
            sock.close()
            if result != 0:  # Port is free
                return port
        except Exception:
            pass
        port += 1
    return start  # fallback


def create_driver(agent_id=None, headless=True, debug=True):
    """
    Create a Chrome WebDriver with remote debugging enabled.

    Args:
        agent_id: Unique identifier for this agent (for tracking)
        headless: Run headless (True) or visible window (False)
        debug: Enable remote debugging port (True = you can watch live)

    Returns:
        (driver, debug_port) — the driver and the port number for live viewing
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.options import Options

    opts = Options()

    if headless:
        opts.add_argument("--headless=new")

    # Standard anti-detection
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

    # Remote debugging — THIS is what lets you watch live
    debug_port = None
    if debug:
        debug_port = _find_free_port()
        opts.add_argument(f"--remote-debugging-port={debug_port}")
        opts.add_argument(f"--remote-debugging-address=127.0.0.1")
        opts.add_argument("--remote-allow-origins=*")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)

    # Track this agent
    if agent_id and debug_port:
        with _port_lock:
            _active_ports[agent_id] = debug_port

        # Save debug info for the viewer
        _save_agent_info(agent_id, {
            "agent_id": agent_id,
            "debug_port": debug_port,
            "debug_url": f"http://127.0.0.1:{debug_port}",
            "devtools_url": f"devtools://devtools/bundled/inspector.html?ws=127.0.0.1:{debug_port}",
            "status": "running",
            "started": datetime.now().isoformat(),
            "headless": headless
        })

    return driver, debug_port


def take_screenshot(driver, agent_id, step=""):
    """
    Take a screenshot and save to BOTH:
    - Janovum platform folder (for client viewer)
    - Personal desktop folder (for your Agent_Viewer.html)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save latest screenshot
    for folder in [SCREENSHOT_DIR, PERSONAL_VIEWER_DIR]:
        latest = os.path.join(folder, f"{agent_id}_latest.png")
        driver.save_screenshot(latest)

        # Save timestamped copy
        ts_file = os.path.join(folder, f"{agent_id}_{timestamp}.png")
        driver.save_screenshot(ts_file)

    # Save metadata to both locations
    meta = {
        "agent_id": agent_id,
        "timestamp": datetime.now().isoformat(),
        "step": step,
        "url": driver.current_url,
        "title": driver.title,
        "screenshot": f"{agent_id}_latest.png",
        "screenshot_path": os.path.join(PERSONAL_VIEWER_DIR, f"{agent_id}_latest.png").replace("\\", "/"),
        "debug_port": _active_ports.get(agent_id),
        "status": "running"
    }

    for folder in [SCREENSHOT_DIR, PERSONAL_VIEWER_DIR]:
        meta_path = os.path.join(folder, f"{agent_id}_meta.json")
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

    return meta


def release_driver(driver, agent_id=None):
    """Quit driver and clean up port tracking."""
    try:
        driver.quit()
    except Exception:
        pass

    if agent_id:
        with _port_lock:
            _active_ports.pop(agent_id, None)

        # Update status
        for folder in [SCREENSHOT_DIR, PERSONAL_VIEWER_DIR]:
            meta_path = os.path.join(folder, f"{agent_id}_meta.json")
            if os.path.exists(meta_path):
                try:
                    with open(meta_path) as f:
                        meta = json.load(f)
                    meta["status"] = "stopped"
                    meta["stopped_at"] = datetime.now().isoformat()
                    with open(meta_path, "w") as f:
                        json.dump(meta, f, indent=2)
                except Exception:
                    pass


def get_active_agents():
    """Get all active agents with their debug ports."""
    agents = []
    with _port_lock:
        for agent_id, port in _active_ports.items():
            meta_path = os.path.join(PERSONAL_VIEWER_DIR, f"{agent_id}_meta.json")
            meta = {"agent_id": agent_id, "debug_port": port}
            if os.path.exists(meta_path):
                try:
                    with open(meta_path) as f:
                        meta = json.load(f)
                except Exception:
                    pass
            agents.append(meta)
    return agents


def get_all_debug_ports():
    """Get mapping of agent_id -> debug_port for all active agents."""
    with _port_lock:
        return dict(_active_ports)


def _save_agent_info(agent_id, info):
    """Save agent info to the personal viewer data folder."""
    for folder in [SCREENSHOT_DIR, PERSONAL_VIEWER_DIR]:
        path = os.path.join(folder, f"{agent_id}_meta.json")
        with open(path, "w") as f:
            json.dump(info, f, indent=2)
