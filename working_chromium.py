import boto3
import io
import os
import requests
import time
from datetime import datetime, timezone, timedelta
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


JSON_URL = "https://pub-a3be569620e4415b916e737210363aee.r2.dev/webshops_info/webshop_info_export.json"

def load_urls_from_json(json_url):
    response = requests.get(json_url, timeout=10)
    response.raise_for_status()

    data = response.json()

    urls = {}
    for item in data:
        name = item.get("name")
        url = item.get("url")

        if name and url:
            urls[name] = url

    print(f"Loaded {len(urls)} URLs from JSON")  # ✅ fix
    return urls

URLS = load_urls_from_json(JSON_URL)

# ========================================
# R2 CONFIG
# ========================================

R2_ACCOUNT_ID = "secret"
R2_ACCESS_KEY_ID = "secret"
R2_SECRET_ACCESS_KEY = "secret"
R2_BUCKET_NAME = "screenshots"
R2_PREFIX = ""

r2 = boto3.client(
    "s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    region_name="auto",
)


def build_latest_screenshot_map(r2_client, bucket_name, prefix):
    """
    Scant bucket één keer en bouwt dict:
    {
        "about-you": datetime,
        "adidas": datetime,
    }
    Gebaseerd op timestamp in bestandsnaam.
    """
    latest_map = {}
    continuation_token = None

    while True:
        if continuation_token:
            response = r2_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix,
                ContinuationToken=continuation_token,
            )
        else:
            response = r2_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix,
            )

        if "Contents" not in response:
            break

        for obj in response["Contents"]:
            filename = obj["Key"].replace(prefix, "")

            try:
                shop = filename.split("_")[0]
                timestamp_str = filename.split("_", 1)[1].replace(".jpg", "")

                dt = datetime.strptime(
                    timestamp_str, "%Y%m%d_%H%M%S"
                ).replace(tzinfo=timezone.utc)

                if shop not in latest_map or dt > latest_map[shop]:
                    latest_map[shop] = dt

            except Exception:
                continue

        if response.get("IsTruncated"):
            continuation_token = response.get("NextContinuationToken")
        else:
            break

    return latest_map


latest_screenshots = build_latest_screenshot_map(
    r2, R2_BUCKET_NAME, R2_PREFIX
)


def screenshot_recently_uploaded_from_map(latest_map, safe_key, hours=24):
    if safe_key not in latest_map:
        print(f"[CHECK] {safe_key}: no previous screenshot found.")
        return False

    last_modified = latest_map[safe_key]
    now = datetime.now(timezone.utc)
    age = now - last_modified

    if age < timedelta(hours=hours):
        remaining = timedelta(hours=hours) - age
        print(
            f"[SKIP] {safe_key}: "
            f"last screenshot {age} ago. "
            f"Next allowed in {remaining}."
        )
        return True

    print(
        f"[OK] {safe_key}: "
        f"last screenshot {age} ago. Creating new one."
    )

    return False


print("\n--- Fresh run mode ---\n")


# ========================================
# CHROME CONFIG
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
# GENERIC COOKIE CLICKER (CASE INSENSITIVE)
# ========================================

def click_cookie_buttons(driver, timeout=5):
    keywords = [
        "accept", "agree", "allow", "consent",
        "akkoord", "accepteren", "alles accepteren", "alle cookies accepteren", "oké", "alles toestaan", "aanvaarden",
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
                    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(1)
                    return True
            except:
                continue
    except:
        pass

    return False


# ========================================
# SAFE NUCLEAR COOKIE CLEANUP
# ========================================

NUCLEAR_COOKIE_JS = """
(function() {

    if (!document || !document.body) return;

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

    document.querySelectorAll('[role="dialog"]').forEach(el => {
        const text = (el.innerText || "").toLowerCase();
        if (text.includes("cookie") || text.includes("consent")) {
            try { el.remove(); } catch(e){}
        }
    });

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

for key, url in URLS.items():
    safe_key = key.replace(" ", "_")

    # 24-uurs check
    if screenshot_recently_uploaded_from_map(
            latest_screenshots, safe_key, hours=24
    ):
        continue

    print(f"\nOpening {key} -> {url}")

    try:
        driver.get(url)

        wait_for_full_load(driver)
        time.sleep(2)

        driver.execute_script("window.scrollTo(0, 0);")

        nuclear_cookie_cleanup(driver)
        click_cookie_buttons(driver)

        time.sleep(0.5)

        safe_key = key.replace(" ", "_")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        screenshot_filename = f"{safe_key}_{timestamp}.jpg"

        # Screenshot als PNG bytes in memory
        png_bytes = driver.get_screenshot_as_png()

        # Open met Pillow
        image = Image.open(io.BytesIO(png_bytes))

        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        # JPEG in memory
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=75, optimize=True)
        buffer.seek(0)

        # Upload naar R2
        r2.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=screenshot_filename,
            Body=buffer,
            ContentType="image/jpeg",
        )

        print(f"Uploaded to R2: screenshots/{screenshot_filename}")

    except Exception as e:
        print(f"Error on {key}: {e}")
        continue


driver.quit()
print("\nDone.")