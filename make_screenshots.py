import subprocess
import time
import os
from datetime import datetime
import re

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

SCREENSHOT_DIR = "/home/lennart/screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def sanitize_site_name(url):
    # Haal domein uit URL en vervang ongewenste tekens voor bestandsnaam
    site = re.sub(r'https?://(www\.)?', '', url)
    site = re.sub(r'[^A-Za-z0-9_-]', '_', site)
    return site

# 1️⃣ Start 1 Firefox-instance voor alle sites
firefox_process = subprocess.Popen(["firefox", "--new-window"])
time.sleep(5)  # even tijd geven om te starten

try:
    for site in SITES:
        # 2️⃣ Nieuwe tab openen
        subprocess.run(["firefox", "--new-tab", site])
        print(f"Opening {site}")

        # 3️⃣ Wacht tot pagina geladen is
        time.sleep(8)

        # 4️⃣ Screenshot maken
        site_name = sanitize_site_name(site)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(SCREENSHOT_DIR, f"{site_name}_{timestamp}.png")

        subprocess.run(["gnome-screenshot", "-w", "-f", screenshot_path])
        print(f"Screenshot opgeslagen: {screenshot_path}")

        time.sleep(2)  # kleine pauze tussen sites

finally:
    # 5️⃣ Firefox afsluiten na alle sites
    print("Sluit Firefox netjes af...")
    firefox_process.terminate()
    try:
        firefox_process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        print("Geforceerd afsluiten")
        firefox_process.kill()

print("Klaar met alle screenshots!")
