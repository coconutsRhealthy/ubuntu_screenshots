import subprocess
import time
import os

SITES = [
    "https://www.nos.nl",
    "https://www.telegraaf.nl",
    "https://www.nu.nl",
    "https://www.buienradar.nl",
    "https://www.google.nl"
]

SCREENSHOT_DIR = "/home/lennart/screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# 1\ufe0f\u20e3 Firefox starten voor de hele sessie
firefox_process = subprocess.Popen(["firefox", "--new-window"])
time.sleep(5)  # even tijd geven om te starten

try:
    for idx, site in enumerate(SITES, start=1):
        # 2\ufe0f\u20e3 Nieuwe tab openen met URL
        subprocess.run(["firefox", "--new-tab", site])
        print(f"Opening {site}")

        time.sleep(8)  # wachten tot pagina geladen

        # 3\ufe0f\u20e3 Screenshot van actief venster
        screenshot_path = os.path.join(SCREENSHOT_DIR, f"site_{idx}.png")
        subprocess.run(["gnome-screenshot", "-w", "-f", screenshot_path])
        print(f"Screenshot opgeslagen: {screenshot_path}")

        time.sleep(2)  # kleine pauze tussen sites

finally:
    # 4\ufe0f\u20e3 Firefox netjes afsluiten
    print("Sluit Firefox netjes af...")
    firefox_process.terminate()  # stuur netjes een afsluit-signaal
    try:
        firefox_process.wait(timeout=10)  # wacht tot Firefox klaar is
    except subprocess.TimeoutExpired:
        print("Firefox reageerde niet, geforceerd afsluiten")
        firefox_process.kill()

print("Klaar met alle screenshots!")
