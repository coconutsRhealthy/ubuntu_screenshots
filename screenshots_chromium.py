import os
import time
import requests
from datetime import datetime
from PIL import Image

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


# 📌 URL naar sites.json op GitHub (RAW)
SITES_JSON_URL = (
    "https://raw.githubusercontent.com/wgknl/diski-assets/main/json/sites.json"
)

# 📌 Basis map voor screenshots (oude structuur behouden)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCREENSHOT_DIR = os.path.join(BASE_DIR, "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


# --------------------------------------------------
# 📌 Sites ophalen van GitHub (oude logica)
# --------------------------------------------------
def load_sites_from_github():
    try:
        response = requests.get(SITES_JSON_URL, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print("⚠️ Kon sites.json niet laden van GitHub:", e)
        exit(1)


# --------------------------------------------------
# 📌 Screenshot pad bouwen (oude structuur)
# webshop/jaar/maand/dag/webshop_timestamp.jpg
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
# 🔹 Chromium Selenium setup
# --------------------------------------------------
chrome_options = Options()
chrome_options.binary_location = os.environ.get("CHROME_BIN", "/usr/bin/chromium")

chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")

# Performance tweaks
chrome_options.add_argument("--disable-notifications")
chrome_options.add_argument("--disable-infobars")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")

service = Service(os.environ.get("CHROMEDRIVER_PATH", "/usr/bin/chromedriver"))
driver = webdriver.Chrome(service=service, options=chrome_options)


# --------------------------------------------------
# 🍪 Cookie killer JS (uit nieuw script)
# --------------------------------------------------
COOKIE_KILLER_JS = """
(function() {
    function killOverlays() {
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
                if (el.offsetHeight > 100 || el.offsetWidth > 100) {
                    el.remove();
                }
            });
        });

        document.body.style.overflow = "auto";
        document.documentElement.style.overflow = "auto";
        document.body.style.position = "static";
        document.documentElement.style.position = "static";

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

    killOverlays();
    setTimeout(killOverlays, 1000);
})();
"""


def clean_page():
    driver.execute_script(COOKIE_KILLER_JS)


# --------------------------------------------------
# 🚀 Main
# --------------------------------------------------
SITES = load_sites_from_github()

try:
    for site in SITES:
        webshop_name = site["webshop_name"]
        webshop_url = site["webshop_url"]

        print(f"Opening {webshop_name} → {webshop_url}")

        driver.get(webshop_url)

        time.sleep(3)
        clean_page()
        time.sleep(2)

        # 📸 Screenshot maken (PNG → JPEG zoals oude script)
        jpg_path = build_screenshot_path(SCREENSHOT_DIR, webshop_name)
        png_path = jpg_path.replace(".jpg", ".png")

        driver.save_screenshot(png_path)

        with Image.open(png_path) as img:
            rgb_img = img.convert("RGB")
            rgb_img.save(jpg_path, "JPEG", quality=85, optimize=True)

        os.remove(png_path)

        print(f"Screenshot opgeslagen: {jpg_path}")

        time.sleep(1)

finally:
    driver.quit()
    print("✅ Klaar met alle screenshots!")
