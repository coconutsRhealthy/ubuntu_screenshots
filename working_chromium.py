import boto3
import io
import os
import time
from datetime import datetime
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


URLS = {
    "about-you": "https://en.aboutyou.nl/your-shop",
    "adidas": "https://www.adidas.nl/",
    "aimnsportswear": "https://www.aimnsportswear.nl/",
    "airup": "https://shop.air-up.com/nl/en",
    "albelli": "https://www.albelli.nl/",
    "aliexpress": "http://nl.aliexpress.com/",
    "amazon": "https://www.amazon.nl/",
    "arket": "https://www.arket.com/en-nl/",
    "asos": "https://www.asos.com/nl/dames/",
    "aybl": "https://nl.aybl.com",
    "bershka": "https://www.bershka.com/nl/h-woman.html",
    "bijenkorf": "https://www.debijenkorf.nl/",
    "bjornborg": "https://www.bjornborg.com/nl/",
    "bodyandfit.com": "https://www.bodyandfit.com",
    "bol.com": "https://www.bol.com/nl/nl/",
    "boohoo": "https://nl.boohoo.com/",
    "boozyshop": "https://www.boozyshop.nl/",
    "burga": "https://burga.nl/",
    "bylashbabe": "https://bylashbabe.nl/",
    "cabaulifestyle": "https://cabaulifestyle.com/",
    "charlottetilbury": "https://www.charlottetilbury.com/nl",
    "cider": "https://www.shopcider.com/",
    "colourfulrebel": "https://colourfulrebel.com/",
    "coolblue": "https://www.coolblue.nl/",
    "costes": "https://www.costesfashion.com/nl-nl",
    "cottonclub": "https://www.cottonclub.nl/nl-nl",
    "creamyfabrics": "https://creamyfabrics.com/nl",
    "decathlon": "https://www.decathlon.nl/",
    "deloox": "https://www.deloox.nl/",
    "desenio": "https://desenio.nl/",
    "dilling": "https://www.dilling.nl/",
    "douglas": "https://www.douglas.nl/nl",
    "dyson": "https://www.dyson.nl/nl",
    "emmasleepnl": "https://www.emma-sleep.nl/",
    "emyjewels": "https://emyjewels.com/",
    "esn": "https://nl.esn.com/",
    "estrid": "https://estrid.com/en-nl/pages/home",
    "esuals": "https://www.esuals.nl/",
    "etos": "https://www.etos.nl/",
    "famousstore": "https://www.famous-store.nl/",
    "fashiontiger.nl": "https://fashiontiger.nl/",
    "footlocker": "https://www.footlocker.nl/",
    "geurwolkje": "https://geurwolkje.nl/",
    "ginatricot": "https://www.ginatricot.com/nl",
    "gisou": "https://gisou.com/",
    "greetz.nl": "https://www.greetz.nl/nl/",
    "gutsgusto": "https://www.gutsgusto.com/en",
    "gymshark": "https://nl.gymshark.com/",
    "haarshop.nl": "https://www.haarshop.nl/",
    "hellofresh.nl": "https://www.hellofresh.nl/",
    "hema": "https://www.hema.nl/",
    "hm": "https://www2.hm.com/nl_nl/index.html",
    "hollandandbarrett": "https://www.hollandandbarrett.nl/",
    "hunkemoller": "https://www.hunkemoller.nl/",
    "iciparisxl": "https://www.iciparisxl.nl/",
    "idealofsweden": "https://idealofsweden.nl/",
    "jdsports": "https://www.jdsports.nl/",
    "kaartje2go": "https://www.kaartje2go.nl/",
    "kaptenandson": "https://kapten-son.com/nl",
    "koreanskincare": "https://koreanskincare.nl/",
    "kruidvat": "https://www.kruidvat.nl/",
    "leolive": "https://le-olive.com/",
    "loavies": "https://www.loavies.com/nl/",
    "lookfantastic": "https://www.lookfantastic.nl",
    "loopearplugs": "https://www.loopearplugs.com/?country=NL",
    "lounge by zalando": "https://www.zalando-lounge.nl/",
    "loungeunderwear": "https://nl.lounge.com/",
    "lucardi": "https://www.lucardi.nl/",
    "lyko": "https://lyko.com/nl",
    "mango": "https://shop.mango.com/nl/nl",
    "mediamarkt": "https://www.mediamarkt.nl/",
    "meetmethere": "https://meet-me-there.com/?country=NL",
    "merodacosmetics": "https://merodacosmetics.nl/",
    "mimamsterdam": "https://www.mimamsterdam.com/nl/",
    "minre": "https://www.minre.nl/",
    "mostwanted": "https://most-wanted.com/",
    "myjewellery": "https://www.my-jewellery.com/nl-nl",
    "myproteinnl": "https://nl.myprotein.com/",
    "nakdfashion": "https://www.na-kd.com/nl",
    "nike": "https://www.nike.com/nl/en/",
    "ninjakitchen": "https://ninjakitchen.nl/",
    "notino": "https://www.notino.nl/",
    "oliviakate": "https://oliviakate.nl/",
    "omoda": "https://www.omoda.nl/",
    "only": "https://www.only.com/en-nl",
    "otrium": "https://www.otrium.nl/dames",
    "pandora": "https://nl.pandora.net/",
    "parfumado": "https://parfumado.com/",
    "parfumdreams.nl": "https://www.parfumdreams.nl/",
    "paulaschoice.nl": "https://www.paulaschoice.nl/nl",
    "pinkgellac": "https://pinkgellac.com/nl",
    "plutosport": "https://www.plutosport.nl/",
    "pullandbear": "https://www.pullandbear.com/nl/",
    "rituals": "https://www.rituals.com/nl-nl/home",
    "scuffers": "https://scuffers.com/",
    "sellpy": "https://www.sellpy.nl/",
    "shein": "https://nl.shein.com/",
    "shoeby": "https://www.shoeby.nl/",
    "sissy-boy": "https://www.sissy-boy.com/",
    "sizzthebrand": "https://sizzthebrand.com/",
    "smartphonehoesjes.nl": "https://www.smartphonehoesjes.nl/",
    "snipes": "https://www.snipes.com/nl-nl/",
    "snuggs": "https://snuggs.nl/",
    "sophiamae": "https://sophia-mae.com/",
    "spacenk.com": "https://www.spacenk.com/nl/home",
    "stradivarius": "https://www.stradivarius.com/nl/",
    "stronger": "https://www.strongerlabel.com/nl",
    "temu": "https://www.temu.com/nl-en",
    "tessv": "https://www.tessv.nl/",
    "thesting": "https://www.thesting.com/nl-nl/dames",
    "thingsilikethingsilove": "https://www.thingsilikethingsilove.com/",
    "thuisbezorgd": "https://www.thuisbezorgd.nl/",
    "uniqlo": "https://www.uniqlo.com/nl/nl/",
    "upfront": "https://upfront.nl/",
    "urbanoutfitters": "https://www.urbanoutfitters.com/",
    "veromoda": "https://www.veromoda.com/nl-nl",
    "weekday": "https://www.weekday.com/nl-nl/women/",
    "wehkamp": "https://www.wehkamp.nl/",
    "westwing": "https://www.westwing.nl/",
    "xenos": "https://www.xenos.nl/",
    "xoxowildhearts": "https://www.xoxowildhearts.com/",
    "xxlnutrition": "https://xxlnutrition.com/nl",
    "yoursurprise": "https://www.yoursurprise.nl/",
    "zalando": "https://www.zalando.nl/dames-home/",
    "zara": "https://www.zara.com/nl/",
    "zelesta.nl": "https://zelesta.nl/"
}


# ========================================
# R2 CONFIG
# ========================================

R2_ACCOUNT_ID = "secret"
R2_ACCESS_KEY_ID = "secret"
R2_SECRET_ACCESS_KEY = "secret"
R2_BUCKET_NAME = "screenshots"

r2 = boto3.client(
    "s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    region_name="auto",
)


# ========================================
# CHROME CONFIG (Stealth)
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

    print(f"\nOpening {key} -> {url}")

    try:
        driver.get(url)

        wait_for_full_load(driver)
        time.sleep(2)

        driver.execute_script("window.scrollTo(0, 0);")

        nuclear_cookie_cleanup(driver)
        click_cookie_buttons(driver)

        time.sleep(0.5)

        safe_key = key.replace(" ", "_").replace(".", "")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

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