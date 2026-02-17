import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


URLS = [
    "https://www.plutosport.nl/",
    "https://www.wehkamp.nl/",
    "https://most-wanted.com/"
]

OUTPUT_DIR = "screenshots"
os.makedirs(OUTPUT_DIR, exist_ok=True)

chrome_options = Options()
chrome_options.binary_location = os.environ.get("CHROME_BIN", "/usr/bin/chromium")

chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")

# Kleine performance boost
chrome_options.add_argument("--disable-notifications")
chrome_options.add_argument("--disable-infobars")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")

service = Service(os.environ.get("CHROMEDRIVER_PATH", "/usr/bin/chromedriver"))
driver = webdriver.Chrome(service=service, options=chrome_options)


COOKIE_KILLER_JS = """
(function() {

    function killOverlays() {

        // 1. Klik op bekende consent buttons
        const buttons = Array.from(document.querySelectorAll("button, input[type='button'], input[type='submit']"));

        buttons.forEach(btn => {
            const text = (btn.innerText || btn.value || "").toLowerCase().trim();

            if (
                text.includes("accept") ||
                text.includes("agree") ||
                text.includes("allow") ||
                text.includes("reject") ||
                text.includes("decline") ||
                text.includes("consent") ||
                text.includes("akkoord") ||
                text.includes("accepteren") ||
                text.includes("weigeren")
            ) {
                try { btn.click(); } catch(e){}
            }
        });

        // 2. Verwijder cookie/consent overlays
        const selectors = [
            "[id*='cookie']",
            "[class*='cookie']",
            "[id*='consent']",
            "[class*='consent']",
            "[aria-label*='cookie']",
            "[role='dialog']",
            "[class*='modal']",
            "[class*='overlay']"
        ];

        selectors.forEach(sel => {
            document.querySelectorAll(sel).forEach(el => {
                if (el.offsetHeight > 100 || el.offsetWidth > 100) {
                    el.remove();
                }
            });
        });

        // 3. Fix scroll lock
        document.body.style.overflow = "auto";
        document.documentElement.style.overflow = "auto";

        document.body.style.position = "static";
        document.documentElement.style.position = "static";

        // 4. Verwijder vaste backdrops
        document.querySelectorAll("*").forEach(el => {
            const style = window.getComputedStyle(el);
            if (
                style.position === "fixed" &&
                parseInt(style.zIndex || 0) > 1000 &&
                el.offsetHeight > window.innerHeight * 0.3
            ) {
                el.remove();
            }
        });
    }

    // Direct uitvoeren
    killOverlays();

    // Nogmaals na 1 seconde (lazy injected modals)
    setTimeout(killOverlays, 1000);

})();
"""


def clean_page():
    driver.execute_script(COOKIE_KILLER_JS)


for i, url in enumerate(URLS):
    print(f"Opening {url}")
    driver.get(url)

    time.sleep(2)

    clean_page()

    time.sleep(1)

    screenshot_path = os.path.join(OUTPUT_DIR, f"screenshot_{i+1}.png")
    driver.save_screenshot(screenshot_path)
    print(f"Saved: {screenshot_path}")

driver.quit()
print("Done.")
