import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

URLS = [
    "https://nl.lounge.com/",
    "https://www.douglas.nl/nl",
    "https://www.arket.com/en-nl/",
    "https://www.asos.com/nl/dames/"
]

OUTPUT_DIR = "screenshots"
os.makedirs(OUTPUT_DIR, exist_ok=True)

chrome_options = Options()
chrome_options.binary_location = os.environ.get("CHROME_BIN", "/usr/bin/chromium")

chrome_options.add_argument("--headless")
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

# ================================
# COOKIE / OVERLAY CLEANER
# ================================

COOKIE_KILLER_JS = """
(function() {

    function killOverlays() {

        if (!document || !document.body) return;

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
                if (el && (el.offsetHeight > 100 || el.offsetWidth > 100)) {
                    try { el.remove(); } catch(e){}
                }
            });
        });

        // Veilig scroll unlock
        if (document.body) {
            document.body.style.overflow = "auto";
            document.body.style.position = "static";
        }

        if (document.documentElement) {
            document.documentElement.style.overflow = "auto";
            document.documentElement.style.position = "static";
        }

        document.querySelectorAll("*").forEach(el => {
            try {
                const style = window.getComputedStyle(el);
                if (
                    style &&
                    style.position === "fixed" &&
                    parseInt(style.zIndex || 0) > 1000 &&
                    el.offsetHeight > window.innerHeight * 0.3
                ) {
                    el.remove();
                }
            } catch(e){}
        });
    }

    killOverlays();
    setTimeout(killOverlays, 1000);

})();
"""


def clean_page():
    driver.execute_script(COOKIE_KILLER_JS)

for i, url in enumerate(URLS):
    print(f"Opening {url}")
    driver.get(url)

    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    WebDriverWait(driver, 15).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )

    # Kleine extra delay voor lazy JS content
    time.sleep(2)

    clean_page()

    # Nog kleine delay zodat eventuele animaties verdwijnen
    time.sleep(1)

    screenshot_path = os.path.join(OUTPUT_DIR, f"screenshot_{i+1}.png")
    driver.save_screenshot(screenshot_path)
    print(f"Saved: {screenshot_path}")

driver.quit()
print("Done.")
