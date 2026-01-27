from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from datetime import datetime
import os
import re
import time

# 📌 Jouw lijst met sites
SITES = [
    "https://www.nos.nl",
    "https://www.telegraaf.nl",
    "https://www.nu.nl",
    "https://www.buienradar.nl",
    "https://www.google.nl",
    "https://www.wikipedia.org",
    "https://www.bbc.com",
    "https://www.cnn.com",
    "https://www.reddit.com",
    "https://www.twitter.com"
]

# 📌 Basis map voor screenshots
SCREENSHOT_DIR = "/home/lennart/screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# 📌 Functie om URL om te zetten naar sitenaam (bijv. nos, nu, bbc)
def sanitize_site_name(url):
    site = re.sub(r'https?://(www\.)?', '', url)
    site = site.split('/')[0]   # alleen domein
    site = site.split('.')[0]   # alleen sitenaam
    return site

# 📌 Functie om mappenstructuur + screenshotpad te maken
def build_screenshot_path(base_dir, site_name):
    now = datetime.now()

    year = now.strftime("%Y")
    month = now.strftime("%m")
    day = now.strftime("%d")
    timestamp = now.strftime("%Y%m%d_%H%M%S")

    dir_path = os.path.join(
        base_dir,
        site_name,
        year,
        month,
        day
    )

    # Mappen aanmaken indien ze niet bestaan
    os.makedirs(dir_path, exist_ok=True)

    filename = f"{site_name}_{timestamp}.png"
    return os.path.join(dir_path, filename)

# 🔹 Selenium setup
options = Options()
options.headless = False  # GUI zichtbaar

# 🔹 Gebruik jouw bestaande Snap Firefox-profiel
PROFILE_PATH = "/home/lennart/snap/firefox/common/.mozilla/firefox/gkmgf18h.default"
options.profile = PROFILE_PATH

# 🔹 Service verwijzing naar geckodriver
service = Service(executable_path="/snap/bin/geckodriver")

# 🔹 Start browser
driver = webdriver.Firefox(service=service, options=options)

# Zorg dat er altijd minimaal één tab open is
driver.get("about:blank")

try:
    for site in SITES:
        # 1️⃣ Nieuwe tab openen
        driver.execute_script("window.open('');")
        driver.switch_to.window(driver.window_handles[-1])
        driver.get(site)
        print(f"Opening {site}")

        # 2️⃣ Wacht tot pagina geladen is
        time.sleep(8)

        # 3️⃣ Screenshot maken
        site_name = sanitize_site_name(site)
        screenshot_path = build_screenshot_path(SCREENSHOT_DIR, site_name)
        driver.save_screenshot(screenshot_path)
        print(f"Screenshot opgeslagen: {screenshot_path}")

        # 4️⃣ Tab sluiten
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        time.sleep(1)

finally:
    # 🔹 Hele browser netjes afsluiten
    driver.quit()
    print("Klaar met alle screenshots!")
