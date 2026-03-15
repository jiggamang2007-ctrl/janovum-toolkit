"""Test browser agent with live streaming on Agent Viewer."""
import sys
import os
import json
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

AGENT_ID = "browser_live"
DEBUG_PORT = 9222
VIEWER_DIR = os.path.expanduser("~/OneDrive/Desktop/agent_viewer_data")
os.makedirs(VIEWER_DIR, exist_ok=True)


def save_meta(driver, step):
    meta = {
        "agent_id": AGENT_ID,
        "debug_port": DEBUG_PORT,
        "name": "Live Browser Agent",
        "type": "browser",
        "task": "Browse websites with live streaming to Agent Viewer",
        "status": "running",
        "step": step,
        "url": driver.current_url,
        "title": driver.title,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    # Screenshot
    ss_path = os.path.join(VIEWER_DIR, f"{AGENT_ID}_latest.png")
    driver.save_screenshot(ss_path)
    meta["screenshot_path"] = ss_path.replace("\\", "/")

    meta_path = os.path.join(VIEWER_DIR, f"{AGENT_ID}_meta.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)


def main():
    print(f"[agent] Launching browser on debug port {DEBUG_PORT}...")

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument(f"--remote-debugging-port={DEBUG_PORT}")
    opts.add_argument("--remote-debugging-address=127.0.0.1")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    print(f"[agent] Browser launched! Debug port: {DEBUG_PORT}")

    try:
        # ── SITE 1: Wikipedia (won't block us) ──
        print("[agent] Step 1: Navigating to Wikipedia...")
        driver.get("https://en.wikipedia.org/wiki/Artificial_intelligence")
        time.sleep(3)
        save_meta(driver, "wikipedia_loaded")
        print(f"[agent] Title: {driver.title}")
        print(f"[agent] URL: {driver.current_url}")

        # Scroll around
        print("[agent] Scrolling down...")
        driver.execute_script("window.scrollTo(0, 500)")
        time.sleep(1)
        save_meta(driver, "scrolled_wikipedia")

        driver.execute_script("window.scrollTo(0, 1200)")
        time.sleep(1)
        save_meta(driver, "scrolled_more")

        # ── SITE 2: Hacker News ──
        print("\n[agent] Step 2: Navigating to Hacker News...")
        driver.get("https://news.ycombinator.com/")
        time.sleep(3)
        save_meta(driver, "hackernews_loaded")
        print(f"[agent] Title: {driver.title}")

        posts = driver.find_elements(By.CSS_SELECTOR, "span.titleline a")
        if posts:
            print(f"[agent] Top HN posts:")
            for i, p in enumerate(posts[:8]):
                print(f"  {i+1}. {p.text.strip()[:80]}")

        save_meta(driver, "reading_hn_posts")

        # Click first post
        if posts and posts[0].get_attribute("href"):
            first_url = posts[0].get_attribute("href")
            first_title = posts[0].text.strip()[:60]
            print(f"\n[agent] Clicking: {first_title}")
            driver.get(first_url)
            time.sleep(4)
            save_meta(driver, "viewing_article")
            print(f"[agent] Now on: {driver.title}")

        # ── SITE 3: Try Reddit ──
        print("\n[agent] Step 3: Trying Reddit...")
        driver.get("https://old.reddit.com/r/technology/")
        time.sleep(5)
        save_meta(driver, "reddit_loaded")
        body = driver.find_element(By.TAG_NAME, "body").text[:500]
        print(f"[agent] Reddit title: {driver.title}")
        if "humanity" in body.lower():
            print("[agent] Reddit blocked us (CAPTCHA). That's fine — other sites work!")
        else:
            print(f"[agent] Reddit loaded! Preview: {body[:200]}")
            reddit_posts = driver.find_elements(By.CSS_SELECTOR, "a.title")
            for i, p in enumerate(reddit_posts[:5]):
                print(f"  {i+1}. {p.text.strip()[:80]}")

        save_meta(driver, "reddit_check")

        # ── Keep alive for viewer ──
        print(f"\n[agent] === LIVE ON PORT {DEBUG_PORT} ===")
        print("[agent] Open Agent_Viewer.html -> Click 'Scan Ports' or 'Connect to Port 9222'")
        print("[agent] You should see the live stream right on the page!")
        print("[agent] Keeping alive 25 seconds...\n")

        # Browse around while alive
        sites = [
            ("https://example.com", "example_com"),
            ("https://en.wikipedia.org/wiki/Florida", "wiki_florida"),
            ("https://news.ycombinator.com/newest", "hn_newest"),
        ]

        for url, step in sites:
            print(f"[agent] Browsing to {url}...")
            driver.get(url)
            time.sleep(3)
            save_meta(driver, step)
            print(f"[agent] Title: {driver.title}")

        # Final countdown
        for i in range(10):
            time.sleep(1)
            save_meta(driver, f"alive_{i}")
            if i % 3 == 0:
                print(f"  ...{10-i}s remaining")

    finally:
        print("\n[agent] Closing browser")
        driver.quit()
        # Mark as stopped
        meta_path = os.path.join(VIEWER_DIR, f"{AGENT_ID}_meta.json")
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                meta = json.load(f)
            meta["status"] = "stopped"
            with open(meta_path, "w") as f:
                json.dump(meta, f, indent=2)


if __name__ == "__main__":
    main()
