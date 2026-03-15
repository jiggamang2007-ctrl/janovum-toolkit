"""Log into Cartesia and get API key."""
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import os

SS_DIR = os.path.join(os.path.dirname(__file__), "platform", "agent_screenshots")
EMAIL = "myfriendlyagent12@gmail.com"
PASSWORD = "67Claude67!"
CODE = "714332"

def screenshot(driver, name):
    path = os.path.join(SS_DIR, f"cartesia_{name}.png")
    driver.save_screenshot(path)
    print(f"  [ss] {name}")

def main():
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    driver = uc.Chrome(options=options, version_main=145)

    try:
        # Go to sign-in page
        print("[1] Signing in to Cartesia...")
        driver.get("https://play.cartesia.ai/sign-in")
        time.sleep(4)
        screenshot(driver, "login_01")
        print(f"  URL: {driver.current_url}")

        # Fill email
        inputs = driver.find_elements(By.TAG_NAME, "input")
        for inp in inputs:
            itype = (inp.get_attribute("type") or "").lower()
            iname = (inp.get_attribute("name") or "").lower()
            iplace = (inp.get_attribute("placeholder") or "").lower()
            if "email" in iname or "email" in iplace or itype == "email":
                inp.clear()
                inp.send_keys(EMAIL)
                print("  Filled email")
            elif itype == "password" or "password" in iname:
                inp.clear()
                inp.send_keys(PASSWORD)
                print("  Filled password")

        time.sleep(1)
        screenshot(driver, "login_02_filled")

        # Click continue/sign in
        for btn in driver.find_elements(By.TAG_NAME, "button"):
            txt = btn.text.strip().lower()
            if any(w in txt for w in ["continue", "sign in", "log in", "submit"]):
                print(f"  Clicking: '{btn.text}'")
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(3)
                break

        screenshot(driver, "login_03_after_continue")
        print(f"  URL: {driver.current_url}")

        # Check if we need to enter password on next screen
        inputs = driver.find_elements(By.TAG_NAME, "input")
        for inp in inputs:
            itype = (inp.get_attribute("type") or "").lower()
            if itype == "password":
                inp.clear()
                inp.send_keys(PASSWORD)
                print("  Filled password on second screen")
                time.sleep(1)
                # Click continue again
                for btn in driver.find_elements(By.TAG_NAME, "button"):
                    txt = btn.text.strip().lower()
                    if any(w in txt for w in ["continue", "sign in", "log in", "submit"]):
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(5)
                        break
                break

        screenshot(driver, "login_04")
        print(f"  URL: {driver.current_url}")

        # Check if we need verification code
        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        if "verify" in page_text or "code" in page_text:
            print("  Need verification code - checking email for new code...")

            # Read fresh code from email
            import imaplib
            import email as emaillib
            from email.header import decode_header
            import re

            time.sleep(5)  # Wait for email
            mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            mail.login(EMAIL, "pdcvjroclstugncx")
            mail.select("inbox")
            status, messages = mail.search(None, '(FROM "cartesia")')
            email_ids = messages[0].split()

            latest_code = None
            for eid in reversed(email_ids[-5:]):
                status, msg_data = mail.fetch(eid, "(RFC822)")
                msg = emaillib.message_from_bytes(msg_data[0][1])
                subject = str(decode_header(msg["Subject"])[0][0])
                if isinstance(subject, bytes):
                    subject = subject.decode()
                codes = re.findall(r'\b(\d{6})\b', subject)
                if codes:
                    latest_code = codes[-1]
            mail.logout()

            if latest_code:
                print(f"  Got code: {latest_code}")
            else:
                latest_code = CODE
                print(f"  Using original code: {latest_code}")

            # Try entering code - Clerk uses special OTP component
            # Method 1: Try clicking on the page and typing
            time.sleep(1)

            # Find OTP inputs (Clerk sometimes renders them in shadow DOM)
            # Try JavaScript approach
            driver.execute_script(f"""
                // Try to find OTP inputs in shadow DOM
                const inputs = document.querySelectorAll('input[data-otp-input], input[autocomplete="one-time-code"]');
                if (inputs.length > 0) {{
                    inputs[0].focus();
                }}
            """)
            time.sleep(0.5)

            # Type the code
            active = driver.switch_to.active_element
            active.send_keys(latest_code)
            print("  Typed code via active element")
            time.sleep(3)

            screenshot(driver, "login_05_code")

            # Click continue if needed
            for btn in driver.find_elements(By.TAG_NAME, "button"):
                txt = btn.text.strip().lower()
                if "continue" in txt or "verify" in txt:
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(5)
                    break

        screenshot(driver, "login_06_dashboard")
        print(f"  URL: {driver.current_url}")
        print(f"  Title: {driver.title}")

        # Navigate to API keys / settings
        time.sleep(2)

        # Try different API key URLs
        for url in [
            "https://play.cartesia.ai/console/api-keys",
            "https://play.cartesia.ai/console",
            "https://play.cartesia.ai/dashboard",
            "https://play.cartesia.ai/settings",
        ]:
            driver.get(url)
            time.sleep(3)
            page_text = driver.find_element(By.TAG_NAME, "body").text
            print(f"  {url}: {page_text[:150]}")
            if "api" in page_text.lower() or "key" in page_text.lower() or "sk_" in page_text:
                screenshot(driver, "login_07_apikeys")
                # Look for API key text
                import re
                keys = re.findall(r'sk_[a-zA-Z0-9_-]+', page_text)
                if keys:
                    print(f"\n  API KEY FOUND: {keys[0]}")
                break

        screenshot(driver, "login_08_final")
        page_text = driver.find_element(By.TAG_NAME, "body").text
        print(f"\n  Final page text:\n{page_text[:800]}")

    except Exception as e:
        screenshot(driver, "error")
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
