import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


URLS = [
    "https://www.asos.com/nl/dames/",
    "https://www.douglas.nl/nl",
    "https://www.arket.com/en-nl/"
]

OUTPUT_DIR = "screenshots"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ========================================
# CHROME CONFIG (Stealth)
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
# COOKIE CLICKER (SAFE & GENERIC)
# ========================================

def click_cookie_buttons(driver, timeout=5):
    keywords = [
        "accept", "agree", "allow", "consent",
        "akkoord", "accepteren", "alles accepteren",
        "accept all", "agree all", "allow all"
    ]

    xpath_conditions = " or ".join(
        [f"contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{k}')"
         for k in keywords]
    )

    xpath = f"""
        //button[{xpath_conditions}] |
        //a[{xpath_conditions}] |
        //input[@type='submit' and ({xpath_conditions})]
    """

    try:
        buttons = WebDriverWait(driver, timeout).until(
            EC.presence_of_all_elements_located((By.XPATH, xpath))
        )

        for btn in buttons:
            try:
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    time.sleep(1)
                    return True
            except:
                continue
    except:
        pass

    return False


# ========================================
# MILDE JS CLEANER (NO DOM DESTRUCTION)
# ========================================

COOKIE_CLEANER_JS = """
(function() {

    if (!document || !document.body) return;

    const selectors = [
        "[id*='cookie']",
        "[class*='cookie']",
        "[id*='consent']",
        "[class*='consent']"
    ];

    selectors.forEach(sel => {
        document.querySelectorAll(sel).forEach(el => {
            if (el && el.offsetHeight < window.innerHeight * 0.7) {
                try { el.remove(); } catch(e){}
            }
        });
    });

    if (document.body) {
        document.body.style.overflow = "auto";
    }

    if (document.documentElement) {
        document.documentElement.style.overflow = "auto";
    }

})();
"""


def mild_clean_page(driver):
    try:
        driver.execute_script(COOKIE_CLEANER_JS)
    except:
        pass


# ========================================
# PAGE READY WAITER
# ========================================

def wait_for_full_load(driver, timeout=15):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


# ========================================
# MAIN LOOP
# ========================================

for i, url in enumerate(URLS):
    print(f"\nOpening {url}")

    try:
        driver.get(url)

        wait_for_full_load(driver)
        time.sleep(2)  # laat lazy JS injecteren

        # Scroll naar boven (belangrijk voor banners)
        driver.execute_script("window.scrollTo(0, 0);")

        clicked = click_cookie_buttons(driver)

        if not clicked:
            mild_clean_page(driver)

        time.sleep(1)

        screenshot_path = os.path.join(OUTPUT_DIR, f"screenshot_{i+1}.png")
        driver.save_screenshot(screenshot_path)
        print(f"Saved: {screenshot_path}")

    except Exception as e:
        print(f"Error on {url}: {e}")
        continue


driver.quit()
print("\nDone.")
