import os
import requests
from datetime import datetime
from PIL import Image

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException


# --------------------------------------------------
# 📌 Config
# --------------------------------------------------

SITES_JSON_URL = (
    "https://raw.githubusercontent.com/wgknl/diski-assets/main/json/sites.json"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCREENSHOT_DIR = os.path.join(BASE_DIR, "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

PAGE_LOAD_TIMEOUT = 20


# --------------------------------------------------
# 📌 Sites ophalen van GitHub
# --------------------------------------------------

def load_sites_from_github():
    try:
        response = requests.get(SITES_JSON_URL, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print("⚠️ Kon sites.json niet laden:", e)
        exit(1)


# --------------------------------------------------
# 📌 Screenshot pad bouwen
# --------------------------------------------------

def build_screenshot_path(base_dir, webshop_name):
    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    day = now.strftime("%d")
    timestamp = now.strftime("%Y%m%d_%H%M%S")

    dir_path = os.path.join(base_dir, webshop_name, year, month, day)
    os.makedirs(dir_path, exist_ok=True)

    filename = f"{webshop_name}_{timestamp}.jpg"
    return os.path.join(dir_path, filename)


# --------------------------------------------------
# 🔹 Chromium setup
# --------------------------------------------------

chrome_options = Options()
chrome_options.binary_location = os.environ.get("CHROME_BIN", "/usr/bin/chromium")

chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--disable-notifications")
chrome_options.add_argument("--disable-infobars")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")

service = Service(os.environ.get("CHROMEDRIVER_PATH", "/usr/bin/chromedriver"))
driver = webdriver.Chrome(service=service, options=chrome_options)

wait = WebDriverWait(driver, PAGE_LOAD_TIMEOUT)


# --------------------------------------------------
# 🍪 Cookie killer
# --------------------------------------------------

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


# --------------------------------------------------
# ⏳ Slim wachten tot pagina echt geladen is
# --------------------------------------------------

def wait_for_page_ready():
    try:
        # Wacht tot DOM klaar is
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")

        # Wacht tot body aanwezig is
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    except TimeoutException:
        print("⚠️ Pagina load timeout — we gaan toch screenshotten.")


# --------------------------------------------------
# 🚀 Main
# --------------------------------------------------

SITES = load_sites_from_github()

try:
    for site in SITES:
        webshop_name = site["webshop_name"]
        webshop_url = site["webshop_url"]

        print(f"\n🌍 Opening {webshop_name} → {webshop_url}")

        try:
            driver.get(webshop_url)

            wait_for_page_ready()

            # Cookie overlays verwijderen
            clean_page()

            # Kleine extra wait zodat layout stabiliseert
            wait.until(lambda d: d.execute_script("return document.readyState") == "complete")

            # 📸 Screenshot maken
            jpg_path = build_screenshot_path(SCREENSHOT_DIR, webshop_name)
            png_path = jpg_path.replace(".jpg", ".png")

            driver.save_screenshot(png_path)

            with Image.open(png_path) as img:
                rgb_img = img.convert("RGB")
                rgb_img.save(jpg_path, "JPEG", quality=85, optimize=True)

            os.remove(png_path)

            print(f"✅ Screenshot opgeslagen: {jpg_path}")

        except Exception as e:
            print(f"❌ Fout bij {webshop_name}: {e}")

finally:
    driver.quit()
    print("\n🏁 Klaar met alle screenshots!")
