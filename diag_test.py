from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1400,900")
driver = webdriver.Chrome(options=opts)

try:
    driver.get("http://localhost:5050/toolkit/admin")
    time.sleep(3)

    logs = driver.get_log('browser')
    errors = [l for l in logs if l['level'] in ('SEVERE', 'WARNING')]
    print("=== JS ERRORS (initial load) ===")
    for e in errors[:15]:
        print(e['level'], ':', e['message'][:300])

    auth_hidden = 'hidden' in (driver.find_element(By.ID, 'authScreen').get_attribute('class') or '')
    print(f"\nAuth hidden: {auth_hidden}")

    driver.execute_script("switchTab('clients')")
    time.sleep(2)
    grid_html = driver.find_element(By.ID, 'clClientGrid').get_attribute('innerHTML')
    print(f"\nClients grid (first 400): {grid_html[:400]}")

    driver.execute_script("switchTab('employees')")
    time.sleep(1)
    emp_count = len(driver.find_elements(By.CSS_SELECTOR, '#employeeGrid .market-card'))
    print(f"\nEmployee cards: {emp_count}")

    driver.execute_script("switchTab('tools')")
    time.sleep(2)
    tools_stats = driver.find_element(By.ID, 'toolStats').get_attribute('innerHTML')[:200]
    print(f"\nTools stats: {tools_stats}")
    cats_count = len(driver.find_elements(By.CSS_SELECTOR, '#toolCategories .panel'))
    print(f"Tool category panels: {cats_count}")

    driver.execute_script("switchTab('clients')")
    time.sleep(1)
    driver.execute_script("clOpenWizard()")
    time.sleep(0.5)
    modal_vis = driver.find_element(By.ID, 'clWizardModal').value_of_css_property('display')
    print(f"\nAdd Client wizard modal display: {modal_vis}")

    nav_items = driver.find_elements(By.CSS_SELECTOR, '.nav-item')
    locked = [n.get_attribute('data-tab') for n in nav_items if 'nav-locked' in (n.get_attribute('class') or '')]
    print(f"\nLocked nav tabs: {locked}")

    logs2 = driver.get_log('browser')
    errors2 = [l for l in logs2 if l['level'] == 'SEVERE']
    print("\n=== SEVERE ERRORS (post-interact) ===")
    for e in errors2[:15]:
        print(e['message'][:300])

finally:
    driver.quit()
    print("\nDone.")
