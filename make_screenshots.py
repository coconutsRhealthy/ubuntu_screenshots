import time
import os
import requests
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from datetime import datetime
from PIL import Image

# 📌 URL naar je sites.json op GitHub (RAW)
SITES_JSON_URL = (
    "https://raw.githubusercontent.com/wgknl/diski-assets/main/json/sites.json"
)

# 📌 Basis map voor screenshots
SCREENSHOT_DIR = r"/run/user/1000/gvfs/dav+sd:host=Spice%2520client%2520folder._webdav._tcp.local/screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# 📌 Functie: haal sites.json op van GitHub
def load_sites_from_github():
    try:
        response = requests.get(SITES_JSON_URL, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print("⚠️ Kon sites.json niet laden van GitHub:", e)
        exit(1)

# 📌 Functie: build screenshot path
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

# 📌 Load sites from GitHub
SITES = load_sites_from_github()

# 🔹 Selenium setup
options = Options()
options.headless = False  # GUI zichtbaar

PROFILE_PATH = "/home/lennart/snap/firefox/common/.mozilla/firefox/gkmgf18h.default"
options.profile = PROFILE_PATH

service = Service(executable_path="/snap/bin/geckodriver")

driver = webdriver.Firefox(service=service, options=options)
driver.get("about:blank")  # zorg voor minstens 1 tab

try:
    for site in SITES:
        webshop_name = site["webshop_name"]
        webshop_url = site["webshop_url"]

        print(f"Opening {webshop_name} → {webshop_url}")

        # 1️⃣ Nieuwe tab openen
        driver.execute_script("window.open('');")
        driver.switch_to.window(driver.window_handles[-1])
        driver.get(webshop_url)

        # 2️⃣ Wacht tot pagina geladen is
        time.sleep(8)

        # 3️⃣ Screenshot maken (PNG → JPEG)
        jpg_path = build_screenshot_path(SCREENSHOT_DIR, webshop_name)
        png_path = jpg_path.replace(".jpg", ".png")

        driver.save_screenshot(png_path)

        with Image.open(png_path) as img:
            rgb_img = img.convert("RGB")  # JPEG ondersteunt geen alpha
            rgb_img.save(jpg_path, "JPEG", quality=85, optimize=True)

        os.remove(png_path)

        print(f"Screenshot opgeslagen: {jpg_path}")

        # 4️⃣ Tab sluiten
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        time.sleep(1)

finally:
    driver.quit()
    print("✅ Klaar met alle screenshots!")
