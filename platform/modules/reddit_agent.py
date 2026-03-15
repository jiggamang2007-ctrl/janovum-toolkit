"""
Janovum Module — Reddit Agent
Browse, post, comment, and interact on Reddit using Selenium.
Includes live screenshot feed for real-time monitoring.

How it works:
  1. Agent launches headless Chrome, navigates to Reddit
  2. Can browse subreddits, read posts, post content, upvote, comment
  3. Takes screenshots at each step for the live viewer dashboard
  4. Claude decides what to post/comment based on client goals
  5. Screenshots saved to a shared folder for the Agent Viewer page

Requirements:
  pip install selenium webdriver-manager
"""

import json
import os
import sys
import time
import threading
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MODULE_NAME = "reddit_agent"
MODULE_DESC = "Reddit Agent — browse, post, comment on Reddit with live screenshot feed"

# Screenshot directory for live viewer
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "agent_screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# Active agents
active_agents = {}


def get_driver(headless=True):
    """Create Chrome WebDriver for Reddit."""
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.options import Options

    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)


def take_screenshot(driver, agent_id, step_name=""):
    """Take a screenshot and save for the live viewer."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{agent_id}_{timestamp}.png"
    filepath = os.path.join(SCREENSHOT_DIR, filename)
    driver.save_screenshot(filepath)

    # Also save a "latest" screenshot for the live viewer
    latest_path = os.path.join(SCREENSHOT_DIR, f"{agent_id}_latest.png")
    driver.save_screenshot(latest_path)

    # Save metadata
    meta = {
        "agent_id": agent_id,
        "timestamp": datetime.now().isoformat(),
        "step": step_name,
        "url": driver.current_url,
        "title": driver.title,
        "screenshot": filename
    }
    meta_path = os.path.join(SCREENSHOT_DIR, f"{agent_id}_meta.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f)

    return filepath


def login_reddit(driver, agent_id, username, password):
    """Log into Reddit."""
    driver.get("https://www.reddit.com/login/")
    time.sleep(3)
    take_screenshot(driver, agent_id, "login_page")

    from selenium.webdriver.common.by import By
    try:
        user_input = driver.find_element(By.ID, "login-username")
        pass_input = driver.find_element(By.ID, "login-password")
        user_input.send_keys(username)
        pass_input.send_keys(password)
        time.sleep(0.5)

        login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_btn.click()
        time.sleep(5)
        take_screenshot(driver, agent_id, "after_login")

        return {"status": "logged_in", "url": driver.current_url}
    except Exception as e:
        take_screenshot(driver, agent_id, "login_error")
        return {"error": str(e)}


def browse_subreddit(driver, agent_id, subreddit, sort="hot"):
    """Browse a subreddit and get post titles."""
    url = f"https://www.reddit.com/r/{subreddit}/{sort}/"
    driver.get(url)
    time.sleep(3)
    take_screenshot(driver, agent_id, f"browsing_r_{subreddit}")

    from selenium.webdriver.common.by import By
    posts = []
    try:
        # Get post titles
        elements = driver.find_elements(By.CSS_SELECTOR, "a[data-click-id='body']")
        for el in elements[:20]:
            text = el.text.strip()
            href = el.get_attribute("href")
            if text and href:
                posts.append({"title": text, "url": href})
    except Exception:
        pass

    # Fallback: get body text
    if not posts:
        body = driver.find_element(By.TAG_NAME, "body").text[:5000]
        posts = [{"title": "Page content", "text": body}]

    return {"subreddit": subreddit, "sort": sort, "posts": posts[:15], "url": driver.current_url}


def post_to_reddit(driver, agent_id, subreddit, title, body_text):
    """Create a new text post on a subreddit."""
    url = f"https://www.reddit.com/r/{subreddit}/submit"
    driver.get(url)
    time.sleep(3)
    take_screenshot(driver, agent_id, f"submit_page_r_{subreddit}")

    from selenium.webdriver.common.by import By
    try:
        # Fill title
        title_input = driver.find_element(By.CSS_SELECTOR, "textarea[placeholder*='Title'], input[name='title']")
        title_input.send_keys(title)
        time.sleep(0.5)

        # Fill body
        body_input = driver.find_element(By.CSS_SELECTOR, "div[role='textbox'], textarea[name='text']")
        body_input.send_keys(body_text)
        time.sleep(0.5)
        take_screenshot(driver, agent_id, "filled_post_form")

        # Submit
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_btn.click()
        time.sleep(5)
        take_screenshot(driver, agent_id, "after_post_submit")

        return {"status": "posted", "subreddit": subreddit, "title": title, "url": driver.current_url}
    except Exception as e:
        take_screenshot(driver, agent_id, "post_error")
        return {"error": str(e)}


def comment_on_post(driver, agent_id, post_url, comment_text):
    """Comment on a Reddit post."""
    driver.get(post_url)
    time.sleep(3)
    take_screenshot(driver, agent_id, "viewing_post")

    from selenium.webdriver.common.by import By
    try:
        comment_box = driver.find_element(By.CSS_SELECTOR, "div[role='textbox']")
        comment_box.click()
        time.sleep(0.5)
        comment_box.send_keys(comment_text)
        time.sleep(0.5)
        take_screenshot(driver, agent_id, "typed_comment")

        submit = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit.click()
        time.sleep(3)
        take_screenshot(driver, agent_id, "after_comment")

        return {"status": "commented", "url": post_url}
    except Exception as e:
        take_screenshot(driver, agent_id, "comment_error")
        return {"error": str(e)}


def get_agent_screenshots(agent_id=None):
    """Get screenshot info for the live viewer."""
    screenshots = []
    for f in os.listdir(SCREENSHOT_DIR):
        if f.endswith("_meta.json"):
            if agent_id and not f.startswith(agent_id):
                continue
            with open(os.path.join(SCREENSHOT_DIR, f)) as fh:
                meta = json.load(fh)
                screenshots.append(meta)

    screenshots.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return screenshots


def get_all_active_agents():
    """Get status of all active Reddit agents."""
    agents = []
    for agent_id, info in active_agents.items():
        meta_path = os.path.join(SCREENSHOT_DIR, f"{agent_id}_meta.json")
        meta = {}
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                meta = json.load(f)
        agents.append({
            "agent_id": agent_id,
            "status": info.get("status", "unknown"),
            "started": info.get("started", ""),
            "last_step": meta.get("step", ""),
            "current_url": meta.get("url", ""),
            "last_screenshot": meta.get("screenshot", "")
        })
    return agents


# ── TOOL DEFINITIONS ──
TOOLS = [
    {
        "name": "reddit_browse",
        "description": "Browse a subreddit and see top posts",
        "input_schema": {
            "type": "object",
            "properties": {
                "subreddit": {"type": "string", "description": "Subreddit name (without r/)"},
                "sort": {"type": "string", "description": "Sort by: hot, new, top, rising", "default": "hot"}
            },
            "required": ["subreddit"]
        }
    },
    {
        "name": "reddit_post",
        "description": "Create a new text post on a subreddit",
        "input_schema": {
            "type": "object",
            "properties": {
                "subreddit": {"type": "string", "description": "Subreddit to post in"},
                "title": {"type": "string", "description": "Post title"},
                "body": {"type": "string", "description": "Post body text"}
            },
            "required": ["subreddit", "title", "body"]
        }
    },
    {
        "name": "reddit_comment",
        "description": "Comment on a Reddit post",
        "input_schema": {
            "type": "object",
            "properties": {
                "post_url": {"type": "string", "description": "URL of the post to comment on"},
                "comment": {"type": "string", "description": "Comment text"}
            },
            "required": ["post_url", "comment"]
        }
    },
    {
        "name": "reddit_screenshot",
        "description": "Get latest screenshot from a Reddit agent",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID to get screenshot for"}
            }
        }
    }
]


def execute_tool(tool_name, tool_input):
    agent_id = tool_input.get("agent_id", f"reddit_{int(time.time())}")

    if tool_name == "reddit_browse":
        driver = get_driver()
        try:
            result = browse_subreddit(driver, agent_id, tool_input["subreddit"], tool_input.get("sort", "hot"))
            return json.dumps(result)
        finally:
            driver.quit()

    elif tool_name == "reddit_post":
        return json.dumps({"error": "Must be logged in to post. Use reddit_browse first."})

    elif tool_name == "reddit_comment":
        return json.dumps({"error": "Must be logged in to comment. Use reddit_browse first."})

    elif tool_name == "reddit_screenshot":
        screenshots = get_agent_screenshots(tool_input.get("agent_id"))
        return json.dumps(screenshots[:5])

    return json.dumps({"error": f"Unknown tool: {tool_name}"})
