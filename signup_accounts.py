"""Sign up for VoIP.ms and Cartesia accounts."""
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import json

EMAIL = "myfriendlyagent12@gmail.com"
PASSWORD = "67Claude67!"

SS_DIR = os.path.join(os.path.dirname(__file__), "platform", "agent_screenshots")
os.makedirs(SS_DIR, exist_ok=True)

def screenshot(driver, name):
    path = os.path.join(SS_DIR, f"signup_{name}.png")
    driver.save_screenshot(path)
    print(f"  [screenshot] {name}")

def signup_cartesia(driver):
    """Sign up for Cartesia (TTS)."""
    print("\n=== CARTESIA SIGNUP ===")
    driver.get("https://play.cartesia.ai/")
    time.sleep(4)
    screenshot(driver, "cartesia_01_landing")
    print(f"  URL: {driver.current_url}")
    print(f"  Title: {driver.title}")

    # Look for sign up / get started links
    all_links = driver.find_elements(By.TAG_NAME, "a")
    for link in all_links:
        txt = link.text.strip().lower()
        href = link.get_attribute("href") or ""
        if any(w in txt for w in ["sign", "start", "create", "register", "free"]):
            print(f"  Link: '{link.text}' -> {href}")

    # Look for buttons
    all_buttons = driver.find_elements(By.TAG_NAME, "button")
    for btn in all_buttons:
        txt = btn.text.strip().lower()
        if any(w in txt for w in ["sign", "start", "create", "register", "free", "get"]):
            print(f"  Button: '{btn.text}'")

    # Try clicking sign up
    for link in all_links:
        txt = link.text.strip().lower()
        if "sign up" in txt or "get started" in txt or "start free" in txt:
            print(f"  Clicking: '{link.text}'")
            link.click()
            time.sleep(3)
            break

    screenshot(driver, "cartesia_02_signup_page")
    print(f"  URL: {driver.current_url}")

    # Look for email/password fields
    inputs = driver.find_elements(By.TAG_NAME, "input")
    print(f"  Found {len(inputs)} inputs:")
    for inp in inputs:
        itype = inp.get_attribute("type") or ""
        iname = inp.get_attribute("name") or ""
        iplace = inp.get_attribute("placeholder") or ""
        iid = inp.get_attribute("id") or ""
        print(f"    type={itype} name={iname} placeholder={iplace} id={iid}")

        # Fill fields
        lower_all = f"{iname} {iplace} {iid}".lower()
        if "email" in lower_all or itype == "email":
            inp.clear()
            inp.send_keys(EMAIL)
            print(f"    -> filled email")
        elif itype == "password" or "password" in lower_all:
            inp.clear()
            inp.send_keys(PASSWORD)
            print(f"    -> filled password")
        elif "name" in lower_all and "first" in lower_all:
            inp.clear()
            inp.send_keys("Jaden")
        elif "name" in lower_all and "last" in lower_all:
            inp.clear()
            inp.send_keys("Novum")
        elif "name" in lower_all and "company" not in lower_all:
            inp.clear()
            inp.send_keys("Jaden Novum")

    time.sleep(1)
    screenshot(driver, "cartesia_03_filled")

    # Check checkboxes
    for cb in driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']"):
        if not cb.is_selected():
            driver.execute_script("arguments[0].click();", cb)

    # Submit
    for btn in driver.find_elements(By.TAG_NAME, "button"):
        txt = btn.text.strip().lower()
        if any(w in txt for w in ["sign up", "create", "register", "submit", "continue", "get started"]):
            print(f"  Clicking submit: '{btn.text}'")
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(5)
            break

    screenshot(driver, "cartesia_04_after_submit")
    print(f"  URL after submit: {driver.current_url}")
    print(f"  Title: {driver.title}")

    # Check page text for success/error
    body_text = driver.find_element(By.TAG_NAME, "body").text[:500]
    print(f"  Page text: {body_text[:200]}")

    time.sleep(3)
    screenshot(driver, "cartesia_05_final")


def signup_voipms(driver):
    """Sign up for VoIP.ms."""
    print("\n=== VOIP.MS SIGNUP ===")
    driver.get("https://voip.ms/register")
    time.sleep(4)
    screenshot(driver, "voipms_01_landing")
    print(f"  URL: {driver.current_url}")
    print(f"  Title: {driver.title}")

    inputs = driver.find_elements(By.TAG_NAME, "input")
    selects = driver.find_elements(By.TAG_NAME, "select")
    print(f"  Found {len(inputs)} inputs, {len(selects)} selects")

    for inp in inputs:
        itype = inp.get_attribute("type") or ""
        iname = inp.get_attribute("name") or ""
        iplace = inp.get_attribute("placeholder") or ""
        iid = inp.get_attribute("id") or ""
        print(f"    type={itype} name={iname} placeholder={iplace} id={iid}")

        lower_all = f"{iname} {iplace} {iid}".lower()
        if "email" in lower_all or itype == "email":
            inp.clear()
            inp.send_keys(EMAIL)
            print(f"    -> filled email")
        elif itype == "password" or "password" in lower_all:
            inp.clear()
            inp.send_keys(PASSWORD)
            print(f"    -> filled password")
        elif "first" in lower_all:
            inp.clear()
            inp.send_keys("Jaden")
        elif "last" in lower_all:
            inp.clear()
            inp.send_keys("Novum")
        elif "company" in lower_all:
            inp.clear()
            inp.send_keys("Janovum")
        elif "phone" in lower_all:
            inp.clear()
            inp.send_keys("5551234567")

    time.sleep(1)
    screenshot(driver, "voipms_02_filled")

    # Check checkboxes
    for cb in driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']"):
        if not cb.is_selected():
            try:
                driver.execute_script("arguments[0].click();", cb)
            except:
                pass

    # Submit
    for btn in driver.find_elements(By.TAG_NAME, "button"):
        txt = btn.text.strip().lower()
        if any(w in txt for w in ["sign up", "create", "register", "submit", "continue"]):
            print(f"  Clicking submit: '{btn.text}'")
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(5)
            break

    # Also check input[type=submit]
    for sub in driver.find_elements(By.CSS_SELECTOR, "input[type='submit']"):
        print(f"  Found submit input: '{sub.get_attribute('value')}'")
        sub.click()
        time.sleep(5)
        break

    screenshot(driver, "voipms_03_after_submit")
    print(f"  URL after submit: {driver.current_url}")

    body_text = driver.find_element(By.TAG_NAME, "body").text[:500]
    print(f"  Page text: {body_text[:200]}")

    time.sleep(3)
    screenshot(driver, "voipms_04_final")


def main():
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--force-device-scale-factor=1")

    print("Starting Chrome...")
    driver = uc.Chrome(options=options, version_main=145)
    wait = WebDriverWait(driver, 15)

    try:
        # Sign up for Cartesia first
        signup_cartesia(driver)

        # Then VoIP.ms
        signup_voipms(driver)

        print("\n=== ALL DONE ===")
        print("Check screenshots in platform/agent_screenshots/")
        input("Press Enter to close browser...")

    except Exception as e:
        screenshot(driver, "error")
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to close browser...")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
