"""Sign up for Telnyx account using Selenium."""
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os

EMAIL = "myfriendlyagent12@gmail.com"
PASSWORD = "67Claude67!"

# Screenshot dir
SS_DIR = os.path.join(os.path.dirname(__file__), "platform", "agent_screenshots")
os.makedirs(SS_DIR, exist_ok=True)

def screenshot(driver, name):
    path = os.path.join(SS_DIR, f"telnyx_{name}.png")
    driver.save_screenshot(path)
    print(f"[screenshot] {name}")

def main():
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = uc.Chrome(options=options)
    wait = WebDriverWait(driver, 15)

    try:
        print("[1] Going to Telnyx signup...")
        driver.get("https://telnyx.com/sign-up")
        time.sleep(3)
        screenshot(driver, "01_signup_page")

        # Print page title and URL
        print(f"    Title: {driver.title}")
        print(f"    URL: {driver.current_url}")

        # Print all input fields found
        inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"    Found {len(inputs)} input fields:")
        for inp in inputs:
            print(f"      - type={inp.get_attribute('type')} name={inp.get_attribute('name')} placeholder={inp.get_attribute('placeholder')} id={inp.get_attribute('id')}")

        # Print all buttons
        buttons = driver.find_elements(By.TAG_NAME, "button")
        print(f"    Found {len(buttons)} buttons:")
        for btn in buttons:
            print(f"      - text='{btn.text}' type={btn.get_attribute('type')}")

        # Also check for links that might be sign-up related
        links = driver.find_elements(By.TAG_NAME, "a")
        for link in links:
            txt = link.text.strip().lower()
            if any(w in txt for w in ['sign', 'create', 'register', 'start']):
                print(f"    Link: '{link.text}' -> {link.get_attribute('href')}")

        screenshot(driver, "02_fields_found")

        # Try to fill email
        email_field = None
        for inp in inputs:
            t = (inp.get_attribute('type') or '').lower()
            n = (inp.get_attribute('name') or '').lower()
            p = (inp.get_attribute('placeholder') or '').lower()
            if 'email' in t or 'email' in n or 'email' in p:
                email_field = inp
                break

        if email_field:
            print("[2] Filling email...")
            email_field.clear()
            email_field.send_keys(EMAIL)
            time.sleep(1)
        else:
            print("[!] No email field found, trying first text input...")
            for inp in inputs:
                if inp.get_attribute('type') in ['text', 'email', '']:
                    inp.clear()
                    inp.send_keys(EMAIL)
                    break

        # Try to fill password
        pass_fields = [inp for inp in inputs if (inp.get_attribute('type') or '').lower() == 'password']
        if pass_fields:
            print("[3] Filling password...")
            pass_fields[0].clear()
            pass_fields[0].send_keys(PASSWORD)
            time.sleep(1)

        screenshot(driver, "03_filled_form")

        # Look for name fields
        for inp in inputs:
            n = (inp.get_attribute('name') or '').lower()
            p = (inp.get_attribute('placeholder') or '').lower()
            if 'first' in n or 'first' in p:
                inp.clear()
                inp.send_keys("Jaden")
            elif 'last' in n or 'last' in p:
                inp.clear()
                inp.send_keys("Novum")
            elif 'company' in n or 'company' in p or 'organization' in n:
                inp.clear()
                inp.send_keys("Janovum")

        time.sleep(1)
        screenshot(driver, "04_all_fields")

        # Check TOS checkbox
        checkboxes = driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
        for cb in checkboxes:
            if not cb.is_selected():
                try:
                    driver.execute_script("arguments[0].click();", cb)
                    print("[4] Checked checkbox")
                except:
                    pass

        time.sleep(1)
        screenshot(driver, "05_before_submit")

        # Find and click submit button
        submit_btn = None
        for btn in driver.find_elements(By.TAG_NAME, "button"):
            txt = btn.text.strip().lower()
            if any(w in txt for w in ['sign up', 'create', 'register', 'get started', 'submit', 'start']):
                submit_btn = btn
                break

        if submit_btn:
            print(f"[5] Clicking '{submit_btn.text}'...")
            driver.execute_script("arguments[0].click();", submit_btn)
            time.sleep(5)
            screenshot(driver, "06_after_submit")
            print(f"    URL after submit: {driver.current_url}")
            print(f"    Title: {driver.title}")
        else:
            print("[!] No submit button found")
            # Try input[type=submit]
            submits = driver.find_elements(By.CSS_SELECTOR, "input[type='submit']")
            if submits:
                submits[0].click()
                time.sleep(5)
                screenshot(driver, "06_after_submit")

        # Wait and take final screenshot
        time.sleep(5)
        screenshot(driver, "07_final")
        print(f"[DONE] Final URL: {driver.current_url}")
        print(f"       Title: {driver.title}")

        # Keep browser open for manual intervention if needed
        input("Press Enter to close browser...")

    except Exception as e:
        screenshot(driver, "error")
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to close browser...")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
