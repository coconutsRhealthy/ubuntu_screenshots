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
import signal
import time
from datetime import datetime, timezone, timedelta

import boto3
import psutil
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
    "https://pub-a3be569620e4415b916e737210363aee.r2.dev/webshops_info/shop_registry.external.json",
)

R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "screenshots")
R2_PREFIX = os.environ.get("R2_PREFIX", "")

# A shop is skipped if it already has a screenshot newer than this many hours.
DEDUPE_HOURS = int(os.environ.get("DEDUPE_HOURS", "24"))

# Hard wall-clock cap on a single shop (open -> screenshot -> upload). This is
# the backstop the old code lacked: some pages (e.g. meet-me-there.com) finish
# loading but then spin Chromium in a CPU busy-loop that no Selenium timeout
# covers, freezing the whole cycle indefinitely. When this fires we force-kill
# the Chromium process tree and move on. See DEPLOY.txt INCIDENT 2026-06-11.
SHOP_TIMEOUT_SECONDS = int(os.environ.get("SHOP_TIMEOUT_SECONDS", "90"))

# Abort a single page load after this long (Selenium default is ~300s, far too
# long on a 1-core box with ~280 shops). Independent of the wall-clock cap above.
PAGE_LOAD_TIMEOUT_SECONDS = int(os.environ.get("PAGE_LOAD_TIMEOUT_SECONDS", "45"))

# Hard cap on the graceful driver.quit() during cleanup, so a wedged Chromium
# can't hang teardown; the force-kill below is the backstop if quit() times out.
CLEANUP_TIMEOUT_SECONDS = int(os.environ.get("CLEANUP_TIMEOUT_SECONDS", "15"))

# Chronic offenders. meet-me-there.com hangs Chromium and produces tiny/blank
# screenshots even when it doesn't hang — bad input for the downstream promo
# detector. These are NOT skipped forever: they get a "probation" retry every
# BLOCKLIST_RETRY_HOURS (see below), so a shop that gets fixed recovers on its
# own. SKIP_SHOPS (comma-separated keys) adds to this set.
DEFAULT_SKIP_SHOPS = {"meetmethere"}
SKIP_SHOPS = DEFAULT_SKIP_SHOPS | {
    s.strip() for s in os.environ.get("SKIP_SHOPS", "").split(",") if s.strip()
}

# How often a blocklisted shop gets a real attempt again. The 90s wall-clock cap
# makes such a probe safe (a still-broken shop just times out, uploads nothing,
# and waits another interval). We persist the last *attempt* time in R2 (see
# read/write_probation_times) — written BEFORE the attempt, so even a hang can't
# cause hourly re-tries. A probe that succeeds lands in R2 like any screenshot.
BLOCKLIST_RETRY_HOURS = int(os.environ.get("BLOCKLIST_RETRY_HOURS", "24"))
# Marker objects live under this prefix inside the screenshots bucket.
PROBATION_PREFIX = "_probation/"


# ========================================
# PER-SHOP WALL-CLOCK TIMEOUT + PROCESS REAPING
# ========================================

class ShopTimeout(Exception):
    """Raised by the SIGALRM handler when a shop exceeds its wall-clock budget."""


def _alarm_handler(signum, frame):
    raise ShopTimeout()


def kill_proc_tree(pid):
    """Force-kill a process and all its descendants, then reap them.

    Selenium's driver.quit() does not reliably tear down a misbehaving Chromium:
    the browser tree (chromedriver -> chromium -> renderers) can survive and keep
    burning CPU. The whole tree descends from the chromedriver pid, so killing
    that subtree recursively reaps every leaked chromium process."""
    try:
        parent = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return
    procs = parent.children(recursive=True)
    procs.append(parent)
    for p in procs:
        try:
            p.kill()
        except psutil.NoSuchProcess:
            pass
        except Exception:
            pass
    # Reap them so they don't linger as zombies (tini also reaps, belt-and-braces).
    psutil.wait_procs(procs, timeout=5)


def cleanup_driver(driver, chromedriver_pid):
    """Tear down a driver: try a graceful, time-capped quit(), then force-kill the
    whole Chromium process tree as the backstop. Safe to call on any state."""
    if driver is not None:
        try:
            signal.alarm(CLEANUP_TIMEOUT_SECONDS)
            driver.quit()
        except Exception:
            pass
        finally:
            signal.alarm(0)
    if chromedriver_pid is not None:
        kill_proc_tree(chromedriver_pid)


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
    """Load the shop registry and return {shop_name: url}.

    Expects shop_registry.external.json: a dict with a "shops" object keyed by
    shop name, each value being {"url": ..., "category": ..., "resolved_on": ...}.
    """
    response = requests.get(json_url, timeout=10)
    response.raise_for_status()

    shops = response.json().get("shops", {})

    urls = {}
    for name, info in shops.items():
        url = info.get("url") if isinstance(info, dict) else None
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
            if filename.startswith(PROBATION_PREFIX):
                continue  # blocklist probation markers, not screenshots
            try:
                # Filename is "{safe_key}_{YYYYmmdd}_{HHMMSS}.jpg". Parse from the
                # END so shop names that themselves contain "_" (e.g. fejo_studio,
                # osock_performance) still match — splitting on the FIRST "_"
                # mangled them, so they never deduped and got re-shot every cycle.
                name = filename[:-4] if filename.endswith(".jpg") else filename
                shop, date_part, time_part = name.rsplit("_", 2)
                dt = datetime.strptime(
                    f"{date_part}_{time_part}", "%Y%m%d_%H%M%S"
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


def screenshot_recently_uploaded_from_map(latest_map, safe_key, hours):
    if safe_key not in latest_map:
        return False

    age = datetime.now(timezone.utc) - latest_map[safe_key]
    if age < timedelta(hours=hours):
        return True
    return False


# ----- blocklist probation state (persisted in R2) -----

def read_probation_times(r2_client, bucket_name, prefix, safe_keys):
    """Return {safe_key: datetime_of_last_probe} for the given blocklisted shops.

    Each marker is a tiny object holding an ISO timestamp. A shop with no marker
    is absent from the dict, which blocklisted_shop_due() reads as 'never probed
    => due now'. Read failures (incl. missing object) are treated the same way."""
    times = {}
    for safe_key in safe_keys:
        key = f"{prefix}{PROBATION_PREFIX}{safe_key}.txt"
        try:
            body = r2_client.get_object(Bucket=bucket_name, Key=key)["Body"].read()
            times[safe_key] = datetime.fromisoformat(body.decode().strip())
        except Exception:
            continue
    return times


def write_probation_time(r2_client, bucket_name, prefix, safe_key, dt):
    """Record dt as the last probe time for a blocklisted shop. Written BEFORE the
    attempt so a hang/timeout still advances the clock (no hourly re-tries)."""
    try:
        r2_client.put_object(
            Bucket=bucket_name,
            Key=f"{prefix}{PROBATION_PREFIX}{safe_key}.txt",
            Body=dt.isoformat().encode(),
            ContentType="text/plain",
        )
    except Exception as e:
        logger.error(f"Could not write probation marker for {safe_key}: {e}")


def blocklisted_shop_due(probation_times, safe_key, hours):
    """True if a blocklisted shop is due for a probation retry (never probed, or
    last probe was at least `hours` ago)."""
    last = probation_times.get(safe_key)
    if last is None:
        return True
    return (datetime.now(timezone.utc) - last) >= timedelta(hours=hours)


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
    # Abort a stuck page load instead of waiting out Selenium's ~300s default.
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT_SECONDS)
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

    # When was each blocklisted shop last given a probation retry?
    probation = read_probation_times(
        r2, R2_BUCKET_NAME, R2_PREFIX,
        {k.replace(" ", "_") for k in SKIP_SHOPS},
    )

    shot = skipped = failed = 0

    # Install the per-shop wall-clock alarm handler once for this cycle.
    signal.signal(signal.SIGALRM, _alarm_handler)

    for key, url in urls.items():
        safe_key = key.replace(" ", "_")

        if key in SKIP_SHOPS or safe_key in SKIP_SHOPS:
            # Blocklisted: skip, EXCEPT for a periodic probation retry (the 90s
            # cap makes a probe safe; a still-broken shop just times out).
            if not blocklisted_shop_due(probation, safe_key, BLOCKLIST_RETRY_HOURS):
                logger.info(
                    f"Skipping {key} — blocklisted (probation retry every "
                    f"{BLOCKLIST_RETRY_HOURS}h)"
                )
                skipped += 1
                continue
            logger.info(
                f"Probation retry for blocklisted {key} — last probe was "
                f">={BLOCKLIST_RETRY_HOURS}h ago"
            )
            # Stamp the attempt BEFORE trying, so a hang can't cause hourly re-tries.
            write_probation_time(
                r2, R2_BUCKET_NAME, R2_PREFIX, safe_key,
                datetime.now(timezone.utc),
            )

        if screenshot_recently_uploaded_from_map(latest, safe_key, DEDUPE_HOURS):
            skipped += 1
            continue

        logger.info(f"Opening {key} -> {url}")
        driver = None
        chromedriver_pid = None
        try:
            signal.alarm(SHOP_TIMEOUT_SECONDS)
            driver = make_chrome_driver()
            chromedriver_pid = driver.service.process.pid
            screenshot_one(driver, r2, key, url)
            shot += 1
        except ShopTimeout:
            failed += 1
            logger.error(
                f"Timeout on {key} after {SHOP_TIMEOUT_SECONDS}s — killing Chromium"
            )
        except Exception as e:
            failed += 1
            logger.error(f"Error on {key}: {e}")
        finally:
            signal.alarm(0)  # cancel the per-shop alarm before teardown
            cleanup_driver(driver, chromedriver_pid)

    return shot, skipped, failed


if __name__ == "__main__":
    # Allow a one-off run for smoke testing: `python screenshot.py`
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
    )
    result = run_cycle()
    logger.info(f"Done. shot:{result[0]} skipped:{result[1]} failed:{result[2]}")
