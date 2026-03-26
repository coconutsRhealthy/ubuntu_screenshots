import io
import os
import time
import json
from datetime import datetime
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains


# ========================================
# CONFIG
# ========================================

URL = "https://www.bybit.com/copyTrade/"
OUTPUT_DIR = "screenshots"

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ========================================
# CHROME CONFIG
# ========================================

chrome_options = Options()
chrome_options.binary_location = os.environ.get("CHROME_BIN", "/usr/bin/chromium")

chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")

chrome_options.add_argument(
    "--user-agent=Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option("useAutomationExtension", False)

service = Service(os.environ.get("CHROMEDRIVER_PATH", "/usr/bin/chromedriver"))

driver = webdriver.Chrome(service=service, options=chrome_options)

driver.execute_script(
    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
)


# ========================================
# OPTIONAL: COOKIE CLICK
# ========================================

def accept_cookies(driver):
    try:
        buttons = driver.find_elements("xpath", "//button")
        for btn in buttons:
            text = (btn.text or "").lower()
            if any(k in text for k in ["accept", "agree", "akkoord", "alles"]):
                btn.click()
                time.sleep(1)
                return
    except:
        pass


# ========================================
# FETCH VIA BROWSER (CORE)
# ========================================

def fetch_page(driver, page_no):
    api_url = (
        "https://www.bybit.com/x-api/fapi/beehive/public/v1/common/dynamic-leader-list"
        f"?pageNo={page_no}&pageSize=16&userTag=&dataDuration=DATA_DURATION_SEVEN_DAY"
        "&leaderTag=&code=&leaderLevel="
    )

    print(f"Fetching page {page_no} via browser fetch...")

    result = driver.execute_script("""
        const url = arguments[0];

        return fetch(url, {
            method: 'GET',
            credentials: 'include'
        })
        .then(r => r.json())
        .then(data => data)
        .catch(e => ({error: e.toString()}));
    """, api_url)

    return result


# ========================================
# MAIN
# ========================================

try:
    print(f"Opening {URL}")
    driver.get(URL)

    wait = WebDriverWait(driver, 15)

    time.sleep(3)

    accept_cookies(driver)

    time.sleep(1)

    # ========================================
    # Klik "All Traders" tab
    # ========================================

    print("Waiting for 'All Traders' tab...")

    all_traders_tab = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//div[@role='tab' and contains(., 'All Traders')]")
        )
    )

    # Scroll naar element
    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'center'});",
        all_traders_tab
    )

    time.sleep(1)

    # Klik (echte user-like click)
    try:
        all_traders_tab.click()
    except:
        ActionChains(driver).move_to_element(all_traders_tab).click().perform()

    print("Clicked 'All Traders'")

    time.sleep(3)

    # ========================================
    # PAGINA'S OPHALEN
    # ========================================

    all_data = []

    for page in range(1, 6):
        data = fetch_page(driver, page)

        if not data or "error" in data:
            print(f"Error on page {page}: {data}")
            break

        all_data.append(data)
        time.sleep(1)

    # Opslaan
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(OUTPUT_DIR, f"leaderboard_{timestamp}.json")

    with open(json_path, "w") as f:
        json.dump(all_data, f, indent=2)

    print(f"Saved API data: {json_path}")

    # ========================================
    # SCREENSHOT
    # ========================================

    png_bytes = driver.get_screenshot_as_png()
    image = Image.open(io.BytesIO(png_bytes))

    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    screenshot_path = os.path.join(OUTPUT_DIR, f"screenshot_{timestamp}.jpg")

    image.save(screenshot_path, "JPEG", quality=80, optimize=True)

    print(f"Saved screenshot: {screenshot_path}")


except Exception as e:
    print(f"Error: {e}")

finally:
    driver.quit()
