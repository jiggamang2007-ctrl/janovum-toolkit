"""Verify Cartesia account with the email code."""
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import os

SS_DIR = os.path.join(os.path.dirname(__file__), "platform", "agent_screenshots")
CODE = "714332"

def screenshot(driver, name):
    path = os.path.join(SS_DIR, f"cartesia_verify_{name}.png")
    driver.save_screenshot(path)
    print(f"  [screenshot] {name}")

def main():
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")

    driver = uc.Chrome(options=options, version_main=145)

    try:
        print("[1] Going to Cartesia verify page...")
        driver.get("https://play.cartesia.ai/sign-up/verify-email-address?redirect_url=https%3A%2F%2Fplay.cartesia.ai%2Fdashboard")
        time.sleep(4)
        screenshot(driver, "01_verify_page")
        print(f"  URL: {driver.current_url}")

        # Find code input fields
        inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"  Found {len(inputs)} inputs")

        # Cartesia/Clerk usually has individual digit inputs
        # Try typing the code into each input
        code_inputs = [i for i in inputs if i.get_attribute("type") in ["text", "number", "tel", ""]]
        print(f"  Code inputs: {len(code_inputs)}")

        if len(code_inputs) >= 6:
            # Individual digit inputs
            for i, digit in enumerate(CODE):
                code_inputs[i].send_keys(digit)
                time.sleep(0.2)
            print(f"  Entered code: {CODE}")
        elif len(code_inputs) == 1:
            # Single input for full code
            code_inputs[0].send_keys(CODE)
            print(f"  Entered code: {CODE}")
        else:
            # Try all inputs
            for inp in inputs:
                inp_id = inp.get_attribute("id") or ""
                inp_name = inp.get_attribute("name") or ""
                print(f"    input: id={inp_id} name={inp_name} type={inp.get_attribute('type')}")

            # Try clicking on the page first, then typing
            body = driver.find_element(By.TAG_NAME, "body")
            body.click()
            time.sleep(0.5)

            # Sometimes Clerk uses a special OTP input - try sending keys to active element
            from selenium.webdriver.common.keys import Keys
            driver.switch_to.active_element.send_keys(CODE)
            print(f"  Typed code into active element")

        time.sleep(2)
        screenshot(driver, "02_code_entered")

        # Click continue/verify button
        for btn in driver.find_elements(By.TAG_NAME, "button"):
            txt = btn.text.strip().lower()
            if any(w in txt for w in ["continue", "verify", "submit"]):
                print(f"  Clicking: '{btn.text}'")
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(5)
                break

        screenshot(driver, "03_after_verify")
        print(f"  URL: {driver.current_url}")
        print(f"  Title: {driver.title}")

        # Check if we landed on dashboard
        if "dashboard" in driver.current_url.lower():
            print("  SUCCESS! Logged into Cartesia dashboard!")

            # Try to get API key
            time.sleep(3)
            driver.get("https://play.cartesia.ai/settings/api-keys")
            time.sleep(3)
            screenshot(driver, "04_api_keys")

            # Look for API key on the page
            page_text = driver.find_element(By.TAG_NAME, "body").text
            print(f"  Page text: {page_text[:500]}")

        time.sleep(3)
        screenshot(driver, "05_final")

    except Exception as e:
        screenshot(driver, "error")
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
