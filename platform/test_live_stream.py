"""
Simple test: Flask server + headless browser that saves screenshots.
Auto-opens the Agent Viewer in your browser.
"""
import json
import os
import sys
import time
import threading
import webbrowser

PLATFORM_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PLATFORM_DIR)
SCREENSHOT_DIR = os.path.join(PLATFORM_DIR, "agent_screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ── 1. Start Flask server ──
def run_server():
    from server_v2 import app
    import logging
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    app.run(host="0.0.0.0", port=5050, debug=False, use_reloader=False)

print("Starting server...")
threading.Thread(target=run_server, daemon=True).start()
time.sleep(2)
print("Server running!")

# ── 2. Auto-open Agent Viewer ──
webbrowser.open("http://localhost:5050/agent-viewer")
print("Agent Viewer opened in your browser!")

# ── 3. Launch browser ──
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1920,1080")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=opts)

AGENT_ID = "test_browser"

def save(step):
    ss_path = os.path.join(SCREENSHOT_DIR, f"{AGENT_ID}_latest.png")
    driver.save_screenshot(ss_path)
    meta = {
        "agent_id": AGENT_ID,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "step": step,
        "url": driver.current_url,
        "title": driver.title,
        "screenshot": f"{AGENT_ID}_latest.png",
        "status": "running"
    }
    with open(os.path.join(SCREENSHOT_DIR, f"{AGENT_ID}_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

print("Browser launched! Browsing sites...")
print()

try:
    sites = [
        ("https://www.google.com", "google", 6),
        ("https://en.wikipedia.org/wiki/Artificial_intelligence", "wikipedia_ai", 6),
        ("https://news.ycombinator.com/", "hackernews", 6),
        ("https://example.com", "example", 4),
        ("https://en.wikipedia.org/wiki/Florida", "wikipedia_florida", 6),
        ("https://news.ycombinator.com/newest", "hn_newest", 6),
    ]

    for url, step, wait in sites:
        print(f"  -> {step}")
        driver.get(url)
        time.sleep(2)
        save(step)

        for y in [300, 700, 1200]:
            driver.execute_script(f"window.scrollTo(0, {y})")
            time.sleep(1)
            save(f"{step}_scroll")

        time.sleep(max(0, wait - 4))

    print()
    print("Done browsing. Staying alive 3 min with random Wikipedia pages...")
    for i in range(180, 0, -30):
        driver.get("https://en.wikipedia.org/wiki/Special:Random")
        time.sleep(3)
        save(f"random_{i}")
        print(f"  {i}s left | {driver.title}")
        time.sleep(27)

finally:
    meta_path = os.path.join(SCREENSHOT_DIR, f"{AGENT_ID}_meta.json")
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
        meta["status"] = "stopped"
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)
    driver.quit()
    print("Done!")
