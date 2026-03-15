"""
Janovum Module — Browser Agent (Selenium)
Uses Selenium to browse the web, fill forms, scrape data, take screenshots,
and interact with websites on behalf of clients.

How it works:
  1. Client or another module requests a browser action
  2. Python launches headless Chrome via Selenium
  3. Executes the action (navigate, click, fill, screenshot, scrape)
  4. Returns results to Claude for reasoning
  5. Claude decides next step or formats the output

Requirements:
  pip install selenium webdriver-manager
  Chrome installed at: C:\Program Files\Google\Chrome\Application\chrome.exe
"""

import os
import sys
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MODULE_NAME = "browser_agent"
MODULE_DESC = "Browser Agent — Selenium-powered web automation, scraping, screenshots"


def get_driver(headless=True):
    """Create and return a configured Chrome WebDriver."""
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


def navigate(url):
    """Navigate to a URL and return the page title and text content."""
    driver = get_driver()
    try:
        driver.get(url)
        time.sleep(2)
        result = {
            "url": driver.current_url,
            "title": driver.title,
            "text": driver.find_element("tag name", "body").text[:5000]
        }
        return result
    finally:
        driver.quit()


def screenshot(url, save_path=None):
    """Take a screenshot of a webpage."""
    driver = get_driver()
    try:
        driver.get(url)
        time.sleep(3)
        if not save_path:
            save_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "clients", f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            )
        driver.save_screenshot(save_path)
        return {"saved_to": save_path, "url": url, "title": driver.title}
    finally:
        driver.quit()


def scrape_page(url, selector=None):
    """Scrape a webpage. Optionally target a specific CSS selector."""
    driver = get_driver()
    try:
        driver.get(url)
        time.sleep(2)

        if selector:
            elements = driver.find_elements("css selector", selector)
            data = [el.text for el in elements if el.text.strip()]
        else:
            data = [driver.find_element("tag name", "body").text[:10000]]

        return {
            "url": url,
            "title": driver.title,
            "elements_found": len(data) if selector else 1,
            "data": data
        }
    finally:
        driver.quit()


def fill_form(url, fields, submit_selector=None):
    """
    Navigate to a URL, fill form fields, optionally submit.

    fields: list of {"selector": "css selector", "value": "text to type"}
    """
    from selenium.webdriver.common.by import By

    driver = get_driver(headless=False)  # visible for form filling
    try:
        driver.get(url)
        time.sleep(2)

        for field in fields:
            el = driver.find_element(By.CSS_SELECTOR, field["selector"])
            el.clear()
            el.send_keys(field["value"])
            time.sleep(0.3)

        if submit_selector:
            btn = driver.find_element(By.CSS_SELECTOR, submit_selector)
            btn.click()
            time.sleep(3)

        return {
            "url": driver.current_url,
            "title": driver.title,
            "fields_filled": len(fields),
            "submitted": bool(submit_selector)
        }
    finally:
        driver.quit()


def extract_links(url, filter_text=None):
    """Extract all links from a page, optionally filtering by text content."""
    driver = get_driver()
    try:
        driver.get(url)
        time.sleep(2)
        links = driver.find_elements("tag name", "a")

        results = []
        for link in links:
            href = link.get_attribute("href")
            text = link.text.strip()
            if href and text:
                if filter_text and filter_text.lower() not in text.lower():
                    continue
                results.append({"text": text, "url": href})

        return {"url": url, "links_found": len(results), "links": results[:50]}
    finally:
        driver.quit()


def extract_table(url, table_index=0):
    """Extract data from an HTML table on a page."""
    driver = get_driver()
    try:
        driver.get(url)
        time.sleep(2)
        tables = driver.find_elements("tag name", "table")

        if table_index >= len(tables):
            return {"error": f"Only {len(tables)} tables found on page"}

        table = tables[table_index]
        rows = table.find_elements("tag name", "tr")

        data = []
        for row in rows:
            cells = row.find_elements("tag name", "td")
            if not cells:
                cells = row.find_elements("tag name", "th")
            data.append([cell.text for cell in cells])

        return {"url": url, "rows": len(data), "data": data}
    finally:
        driver.quit()


# ── TOOL DEFINITIONS (for Claude agent loop) ──
TOOLS = [
    {
        "name": "browser_navigate",
        "description": "Navigate to a URL and get the page content",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to navigate to"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "browser_screenshot",
        "description": "Take a screenshot of a webpage",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to screenshot"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "browser_scrape",
        "description": "Scrape content from a webpage, optionally targeting a CSS selector",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to scrape"},
                "selector": {"type": "string", "description": "Optional CSS selector to target specific elements"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "browser_extract_links",
        "description": "Extract all links from a webpage",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to extract links from"},
                "filter_text": {"type": "string", "description": "Optional text to filter links by"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "browser_extract_table",
        "description": "Extract data from an HTML table on a webpage",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL containing the table"},
                "table_index": {"type": "integer", "description": "Which table on the page (0 = first)", "default": 0}
            },
            "required": ["url"]
        }
    }
]


def execute_tool(tool_name, tool_input):
    """Execute a browser tool and return the result."""
    if tool_name == "browser_navigate":
        return json.dumps(navigate(tool_input["url"]))
    elif tool_name == "browser_screenshot":
        return json.dumps(screenshot(tool_input["url"]))
    elif tool_name == "browser_scrape":
        return json.dumps(scrape_page(tool_input["url"], tool_input.get("selector")))
    elif tool_name == "browser_extract_links":
        return json.dumps(extract_links(tool_input["url"], tool_input.get("filter_text")))
    elif tool_name == "browser_extract_table":
        return json.dumps(extract_table(tool_input["url"], tool_input.get("table_index", 0)))
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})


if __name__ == "__main__":
    # Test
    result = navigate("https://example.com")
    print(json.dumps(result, indent=2))
