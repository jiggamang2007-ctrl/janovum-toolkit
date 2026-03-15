"""
Janovum Core — Fast Browser Controller
Uses Chrome DevTools Protocol (CDP) for near-instant browser interaction.
No more screenshot-scan-act loops for basic navigation.

Instead of:
  screenshot → save file → read image → think → act (5-10s per step)

We do:
  read DOM instantly → act → listen for result (milliseconds)

Screenshots only taken when we actually NEED to see something visual
(CAPTCHAs, layout checks, visual verification for the Agent Viewer).

CDP gives us:
  - Instant DOM reading (no screenshot needed)
  - Event listeners (know INSTANTLY when page loads, element appears, etc.)
  - Network interception (see every request/response)
  - Console log capture
  - JavaScript execution
  - Performance monitoring
"""

import json
import os
import sys
import time
import threading
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.browser import create_driver, take_screenshot, release_driver, PERSONAL_VIEWER_DIR


class FastBrowser:
    """
    High-speed browser controller using CDP + Selenium.
    Reads DOM directly instead of screenshotting.
    Only takes screenshots for visual tasks or the Agent Viewer feed.
    """

    def __init__(self, agent_id=None, headless=True):
        self.agent_id = agent_id or f"fast_{int(time.time())}"
        self.driver, self.debug_port = create_driver(self.agent_id, headless=headless, debug=True)
        self.step_count = 0
        self.last_url = ""
        self._screenshot_interval = 3  # seconds between auto-screenshots for viewer
        self._last_screenshot_time = 0
        self._event_log = []

    # ══════════════════════════════════════════
    # INSTANT DOM READING (no screenshot needed)
    # ══════════════════════════════════════════

    def read_page(self):
        """
        Instantly read the current page state.
        Returns text, title, URL — no screenshot needed.
        """
        return {
            "url": self.driver.current_url,
            "title": self.driver.title,
            "text": self._get_body_text(),
            "ready_state": self._js("return document.readyState"),
        }

    def read_text(self, selector=None):
        """Read text content from the page or a specific element. Instant."""
        if selector:
            try:
                el = self.driver.find_element("css selector", selector)
                return el.text
            except Exception:
                return None
        return self._get_body_text()

    def read_all_text(self, selector):
        """Read text from ALL matching elements. Instant."""
        try:
            elements = self.driver.find_elements("css selector", selector)
            return [el.text for el in elements if el.text.strip()]
        except Exception:
            return []

    def read_attribute(self, selector, attribute):
        """Read an attribute from an element. Instant."""
        try:
            el = self.driver.find_element("css selector", selector)
            return el.get_attribute(attribute)
        except Exception:
            return None

    def read_all_links(self):
        """Get all links on the page. Instant."""
        return self._js("""
            return Array.from(document.querySelectorAll('a[href]')).map(a => ({
                text: a.textContent.trim().substring(0, 100),
                href: a.href
            })).filter(l => l.text && l.href);
        """) or []

    def read_form_fields(self):
        """Get all input fields on the page. Instant."""
        return self._js("""
            return Array.from(document.querySelectorAll('input, textarea, select')).map(el => ({
                tag: el.tagName.toLowerCase(),
                type: el.type || '',
                name: el.name || '',
                id: el.id || '',
                placeholder: el.placeholder || '',
                value: el.value || '',
                visible: el.offsetParent !== null
            }));
        """) or []

    def element_exists(self, selector):
        """Check if an element exists. Instant."""
        try:
            self.driver.find_element("css selector", selector)
            return True
        except Exception:
            return False

    def element_visible(self, selector):
        """Check if an element is visible. Instant."""
        return self._js(f"""
            const el = document.querySelector('{selector}');
            if (!el) return false;
            return el.offsetParent !== null && getComputedStyle(el).visibility !== 'hidden';
        """) or False

    def count_elements(self, selector):
        """Count matching elements. Instant."""
        return len(self.driver.find_elements("css selector", selector))

    def get_page_source(self):
        """Get raw HTML source. Instant."""
        return self.driver.page_source

    # ══════════════════════════════════════════
    # FAST ACTIONS (with event-driven waiting)
    # ══════════════════════════════════════════

    def go(self, url, wait_for=None, timeout=15):
        """
        Navigate to URL. Waits for page load automatically.
        Optionally wait for a specific element to appear.
        """
        self.driver.get(url)
        self._wait_ready(timeout)

        if wait_for:
            self._wait_for(wait_for, timeout)

        self._auto_screenshot("navigate")
        self.step_count += 1
        self.last_url = self.driver.current_url

        return self.read_page()

    def click(self, selector, wait_after=None, timeout=10):
        """Click an element. Optionally wait for something after."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        el = WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )
        el.click()
        self.step_count += 1

        if wait_after:
            self._wait_for(wait_after, timeout)

        self._auto_screenshot(f"click_{selector[:30]}")
        return True

    def type_text(self, selector, text, clear=True, timeout=10):
        """Type text into an input field."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        el = WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        if clear:
            el.clear()
        el.send_keys(text)
        self.step_count += 1
        self._auto_screenshot(f"type_{selector[:30]}")
        return True

    def submit_form(self, selector=None):
        """Submit a form."""
        if selector:
            self.click(selector)
        else:
            self._js("document.querySelector('form').submit()")
        time.sleep(1)
        self._wait_ready()
        self._auto_screenshot("submit_form")
        self.step_count += 1

    def scroll_to(self, selector=None, y=None):
        """Scroll to an element or Y position."""
        if selector:
            self._js(f"document.querySelector('{selector}').scrollIntoView({{behavior:'smooth',block:'center'}})")
        elif y is not None:
            self._js(f"window.scrollTo(0, {y})")
        else:
            self._js("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(0.3)
        self._auto_screenshot("scroll")

    def hover(self, selector):
        """Hover over an element."""
        from selenium.webdriver.common.action_chains import ActionChains
        el = self.driver.find_element("css selector", selector)
        ActionChains(self.driver).move_to_element(el).perform()
        self._auto_screenshot(f"hover_{selector[:30]}")

    def select_dropdown(self, selector, value=None, text=None):
        """Select a dropdown option by value or visible text."""
        from selenium.webdriver.support.ui import Select
        el = self.driver.find_element("css selector", selector)
        select = Select(el)
        if value:
            select.select_by_value(value)
        elif text:
            select.select_by_visible_text(text)
        self._auto_screenshot(f"select_{selector[:30]}")

    def run_js(self, script):
        """Execute JavaScript and return result. Instant."""
        return self._js(script)

    # ══════════════════════════════════════════
    # CDP — Chrome DevTools Protocol (advanced)
    # ══════════════════════════════════════════

    def cdp(self, method, params=None):
        """Execute a raw CDP command."""
        return self.driver.execute_cdp_cmd(method, params or {})

    def enable_network_logging(self):
        """Start capturing network requests."""
        self.cdp("Network.enable")

    def get_cookies(self):
        """Get all cookies via CDP."""
        result = self.cdp("Network.getAllCookies")
        return result.get("cookies", [])

    def capture_screenshot_cdp(self):
        """Take screenshot via CDP (faster than Selenium method)."""
        result = self.cdp("Page.captureScreenshot", {"format": "png"})
        return result.get("data", "")  # base64 encoded

    def get_page_metrics(self):
        """Get performance metrics."""
        result = self.cdp("Performance.getMetrics")
        return {m["name"]: m["value"] for m in result.get("metrics", [])}

    def emulate_device(self, width=375, height=812, mobile=True, scale=3):
        """Emulate a mobile device."""
        self.cdp("Emulation.setDeviceMetricsOverride", {
            "width": width, "height": height,
            "deviceScaleFactor": scale, "mobile": mobile
        })

    # ══════════════════════════════════════════
    # SMART WAITING (event-driven, not sleep)
    # ══════════════════════════════════════════

    def wait_for_element(self, selector, timeout=15):
        """Wait for an element to appear. Returns True/False."""
        return self._wait_for(selector, timeout)

    def wait_for_text(self, text, timeout=15):
        """Wait for specific text to appear on the page."""
        end = time.time() + timeout
        while time.time() < end:
            if text.lower() in self._get_body_text().lower():
                return True
            time.sleep(0.2)
        return False

    def wait_for_url_change(self, timeout=15):
        """Wait for the URL to change from current."""
        current = self.driver.current_url
        end = time.time() + timeout
        while time.time() < end:
            if self.driver.current_url != current:
                return self.driver.current_url
            time.sleep(0.2)
        return None

    def wait_for_network_idle(self, timeout=10, idle_time=0.5):
        """Wait for network activity to stop."""
        # Simple approach: wait for document ready + small buffer
        self._wait_ready(timeout)
        time.sleep(idle_time)

    # ══════════════════════════════════════════
    # VISUAL — Only when you actually need to SEE
    # ══════════════════════════════════════════

    def screenshot(self, step="manual"):
        """Take a screenshot manually (for visual inspection or CAPTCHA solving)."""
        return take_screenshot(self.driver, self.agent_id, step)

    def see(self):
        """
        Take a screenshot and return it for visual analysis.
        Use this when you need to actually LOOK at the page
        (CAPTCHAs, visual layouts, image content).
        """
        meta = take_screenshot(self.driver, self.agent_id, f"visual_check_{self.step_count}")
        return meta

    # ══════════════════════════════════════════
    # LIFECYCLE
    # ══════════════════════════════════════════

    def close(self):
        """Close the browser and clean up."""
        release_driver(self.driver, self.agent_id)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ══════════════════════════════════════════
    # INTERNAL HELPERS
    # ══════════════════════════════════════════

    def _js(self, script):
        """Execute JavaScript."""
        try:
            return self.driver.execute_script(script)
        except Exception:
            return None

    def _get_body_text(self):
        """Get page body text efficiently."""
        text = self._js("return document.body ? document.body.innerText : ''") or ""
        return text[:10000]

    def _wait_ready(self, timeout=15):
        """Wait for document.readyState === 'complete'."""
        end = time.time() + timeout
        while time.time() < end:
            state = self._js("return document.readyState")
            if state == "complete":
                return True
            time.sleep(0.1)
        return False

    def _wait_for(self, selector, timeout=15):
        """Wait for a CSS selector to appear."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return True
        except Exception:
            return False

    def _auto_screenshot(self, step):
        """Auto-screenshot for the Agent Viewer (rate-limited)."""
        now = time.time()
        if now - self._last_screenshot_time >= self._screenshot_interval:
            take_screenshot(self.driver, self.agent_id, step)
            self._last_screenshot_time = now


# ── Quick-use function ──
def quick_browse(url, agent_id=None):
    """One-liner: open a URL and return page content."""
    fb = FastBrowser(agent_id=agent_id)
    try:
        result = fb.go(url)
        return result
    finally:
        fb.close()
