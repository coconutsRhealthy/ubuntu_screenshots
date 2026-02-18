import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait


URLS = [
    "https://www.asos.com/nl/dames/",
    "https://www.douglas.nl/nl",
    "https://www.arket.com/en-nl/",
    "https://nl.lounge.com/",
    "https://www.zalando.nl/dames-home/",
    "https://www2.hm.com/nl_nl/index.html",
    "https://en.aboutyou.nl/your-shop"
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
# SAFE NUCLEAR COOKIE CLEANUP
# ========================================

NUCLEAR_COOKIE_JS = """
(function() {

    if (!document || !document.body) return;

    // Bekende cookie providers (veilig)
    const knownRoots = [
        "#usercentrics-root",
        "#onetrust-consent-sdk",
        "#CybotCookiebotDialog",
        "[id*='cookiebanner']",
        "[id*='cookie-consent']"
    ];

    knownRoots.forEach(sel => {
        document.querySelectorAll(sel).forEach(el => {
            try { el.remove(); } catch(e){}
        });
    });

    // Verwijder dialogs met cookie/consent tekst
    document.querySelectorAll('[role="dialog"]').forEach(el => {
        const text = (el.innerText || "").toLowerCase();
        if (text.includes("cookie") || text.includes("consent")) {
            try { el.remove(); } catch(e){}
        }
    });

    // Scroll unlock
    document.body.style.overflow = "auto";
    document.documentElement.style.overflow = "auto";

})();
"""


def nuclear_cookie_cleanup(driver):
    try:
        driver.execute_script(NUCLEAR_COOKIE_JS)
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

        driver.execute_script("window.scrollTo(0, 0);")

        # 🔥 Hard cleanup
        nuclear_cookie_cleanup(driver)

        time.sleep(0.5)

        screenshot_path = os.path.join(OUTPUT_DIR, f"screenshot_{i+1}.png")
        driver.save_screenshot(screenshot_path)
        print(f"Saved: {screenshot_path}")

    except Exception as e:
        print(f"Error on {url}: {e}")
        continue


driver.quit()
print("\nDone.")
