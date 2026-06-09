"""One screenshot cycle: load the webshop list, and for every shop not already
captured in the last DEDUPE_HOURS, take a headless-Chromium screenshot and
upload it to R2 as JPEG.

This module is the *work*; collect.py is the long-running scheduler that calls
run_cycle() once an hour. Importing this module has no side effects — all config
is read at call time and a fresh Chromium is launched per shop (see
make_chrome_driver) so memory can't accumulate across the shop list on the 1GB
droplet. That per-shop teardown is what replaces the old watchdog's 30-min kill.
"""

import io
import logging
import os
import time
from datetime import datetime, timezone, timedelta

import boto3
import requests
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

# ========================================
# CONFIG (env-driven; see DEPLOY.txt)
# ========================================

JSON_URL = os.environ.get(
    "JSON_URL",
    "https://pub-a3be569620e4415b916e737210363aee.r2.dev/webshops_info/webshop_info_export.json",
)

R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "screenshots")
R2_PREFIX = os.environ.get("R2_PREFIX", "")

# A shop is skipped if it already has a screenshot newer than this many hours.
DEDUPE_HOURS = int(os.environ.get("DEDUPE_HOURS", "24"))


# ========================================
# R2
# ========================================

def make_r2_client():
    missing = [
        name for name, val in (
            ("R2_ACCOUNT_ID", R2_ACCOUNT_ID),
            ("R2_ACCESS_KEY_ID", R2_ACCESS_KEY_ID),
            ("R2_SECRET_ACCESS_KEY", R2_SECRET_ACCESS_KEY),
        ) if not val
    ]
    if missing:
        raise RuntimeError(f"Missing R2 credentials in env: {', '.join(missing)}")

    return boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


def load_urls_from_json(json_url):
    response = requests.get(json_url, timeout=10)
    response.raise_for_status()

    urls = {}
    for item in response.json():
        name = item.get("name")
        url = item.get("url")
        if name and url:
            urls[name] = url

    logger.info(f"Loaded {len(urls)} URLs from JSON")
    return urls


def build_latest_screenshot_map(r2_client, bucket_name, prefix):
    """Scan the bucket once and return {shop_key: latest_screenshot_datetime},
    derived from the timestamp embedded in each filename (shop_YYYYmmdd_HHMMSS.jpg)."""
    latest_map = {}
    continuation_token = None

    while True:
        kwargs = {"Bucket": bucket_name, "Prefix": prefix}
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token
        response = r2_client.list_objects_v2(**kwargs)

        if "Contents" not in response:
            break

        for obj in response["Contents"]:
            filename = obj["Key"].replace(prefix, "")
            try:
                shop = filename.split("_")[0]
                timestamp_str = filename.split("_", 1)[1].replace(".jpg", "")
                dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S").replace(
                    tzinfo=timezone.utc
                )
                if shop not in latest_map or dt > latest_map[shop]:
                    latest_map[shop] = dt
            except Exception:
                continue

        if response.get("IsTruncated"):
            continuation_token = response.get("NextContinuationToken")
        else:
            break

    return latest_map


def screenshot_recently_uploaded_from_map(latest_map, safe_key, hours):
    if safe_key not in latest_map:
        return False

    age = datetime.now(timezone.utc) - latest_map[safe_key]
    if age < timedelta(hours=hours):
        return True
    return False


# ========================================
# CHROME
# ========================================

def make_chrome_driver():
    """A fresh headless Chromium. Created and torn down per shop so memory is
    reclaimed between shops on the memory-constrained droplet."""
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
    return driver


# ----- cookie handling -----

def click_cookie_buttons(driver, timeout=5):
    keywords = [
        "accept", "agree", "allow", "consent",
        "akkoord", "accepteren", "alles accepteren", "alle cookies accepteren",
        "oké", "alles toestaan", "aanvaarden",
        "accept all", "agree all", "allow all",
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
            except Exception:
                continue
    except Exception:
        pass
    return False


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
    except Exception:
        pass


def wait_for_full_load(driver, timeout=15):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


# ========================================
# ONE SHOP
# ========================================

def screenshot_one(driver, r2, key, url):
    """Open one shop, dismiss cookies, screenshot, upload JPEG to R2."""
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

    png_bytes = driver.get_screenshot_as_png()
    image = Image.open(io.BytesIO(png_bytes))
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=75, optimize=True)
    buffer.seek(0)

    r2.put_object(
        Bucket=R2_BUCKET_NAME,
        Key=f"{R2_PREFIX}{screenshot_filename}",
        Body=buffer,
        ContentType="image/jpeg",
    )
    logger.info(f"Uploaded to R2: {R2_BUCKET_NAME}/{R2_PREFIX}{screenshot_filename}")


# ========================================
# ONE CYCLE
# ========================================

def run_cycle():
    """One full pass over the shop list. Returns (shot, skipped, failed)."""
    urls = load_urls_from_json(JSON_URL)
    r2 = make_r2_client()
    latest = build_latest_screenshot_map(r2, R2_BUCKET_NAME, R2_PREFIX)

    shot = skipped = failed = 0

    for key, url in urls.items():
        safe_key = key.replace(" ", "_")

        if screenshot_recently_uploaded_from_map(latest, safe_key, DEDUPE_HOURS):
            skipped += 1
            continue

        logger.info(f"Opening {key} -> {url}")
        driver = None
        try:
            driver = make_chrome_driver()
            screenshot_one(driver, r2, key, url)
            shot += 1
        except Exception as e:
            failed += 1
            logger.error(f"Error on {key}: {e}")
        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass

    return shot, skipped, failed


if __name__ == "__main__":
    # Allow a one-off run for smoke testing: `python screenshot.py`
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
    )
    result = run_cycle()
    logger.info(f"Done. shot:{result[0]} skipped:{result[1]} failed:{result[2]}")
