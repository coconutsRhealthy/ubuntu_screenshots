import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse


URLS = [
    "https://burga.nl/",
    "http://nl.aliexpress.com/",
    "https://bylashbabe.nl/",
    "https://cabaulifestyle.com/",
    "https://colourfulrebel.com/",
    "https://creamyfabrics.com/nl",
    "https://desenio.nl/",
    "https://emyjewels.com/",
    "https://en.aboutyou.nl/your-shop",
    "https://estrid.com/en-nl/pages/home",
    "https://fashiontiger.nl/",
    "https://geurwolkje.nl/",
    "https://gisou.com/",
    "https://idealofsweden.nl/",
    "https://kapten-son.com/nl",
    "https://koreanskincare.nl/",
    "https://le-olive.com/",
    "https://lyko.com/nl",
    "https://meet-me-there.com/?country=NL",
    "https://merodacosmetics.nl/",
    "https://most-wanted.com/",
    "https://ninjakitchen.nl/",
    "https://nl.aybl.com",
    "https://nl.boohoo.com/",
    "https://nl.esn.com/",
    "https://nl.gymshark.com/",
    "https://nl.lounge.com/",
    "https://nl.myprotein.com/",
    "https://nl.pandora.net/",
    "https://nl.shein.com/",
    "https://oliviakate.nl/",
    "https://parfumado.com/",
    "https://pinkgellac.com/nl",
    "https://scuffers.com/",
    "https://shop.air-up.com/nl/en",
    "https://shop.mango.com/nl/nl",
    "https://sizzthebrand.com/",
    "https://snuggs.nl/",
    "https://sophia-mae.com/",
    "https://upfront.nl/",
    "https://www.adidas.nl/",
    "https://www.aimnsportswear.nl/",
    "https://www.albelli.nl/",
    "https://www.amazon.nl/",
    "https://www.arket.com/en-nl/",
    "https://www.asos.com/nl/dames/",
    "https://www.bershka.com/nl/h-woman.html",
    "https://www.bjornborg.com/nl/",
    "https://www.bodyandfit.com",
    "https://www.bol.com/nl/nl/",
    "https://www.boozyshop.nl/",
    "https://www.charlottetilbury.com/nl",
    "https://www.coolblue.nl/",
    "https://www.costesfashion.com/nl-nl",
    "https://www.cottonclub.nl/nl-nl",
    "https://www.debijenkorf.nl/",
    "https://www.decathlon.nl/",
    "https://www.deloox.nl/",
    "https://www.dilling.nl/",
    "https://www.douglas.nl/nl",
    "https://www.dyson.nl/nl",
    "https://www.emma-sleep.nl/",
    "https://www.esuals.nl/",
    "https://www.etos.nl/",
    "https://www.famous-store.nl/",
    "https://www.footlocker.nl/",
    "https://www.ginatricot.com/nl",
    "https://www.greetz.nl/nl/",
    "https://www.gutsgusto.com/en",
    "https://www.haarshop.nl/",
    "https://www.hellofresh.nl/",
    "https://www.hema.nl/",
    "https://www.hollandandbarrett.nl/",
    "https://www.hunkemoller.nl/",
    "https://www.iciparisxl.nl/",
    "https://www.jdsports.nl/",
    "https://www.kaartje2go.nl/",
    "https://www.kruidvat.nl/",
    "https://www.loavies.com/nl/",
    "https://www.lookfantastic.nl",
    "https://www.loopearplugs.com/?country=NL",
    "https://www.lucardi.nl/",
    "https://www.mediamarkt.nl/",
    "https://www.mimamsterdam.com/nl/",
    "https://www.minre.nl/",
    "https://www.my-jewellery.com/nl-nl",
    "https://www.na-kd.com/nl",
    "https://www.nike.com/nl/en/",
    "https://www.notino.nl/",
    "https://www.omoda.nl/",
    "https://www.only.com/en-nl",
    "https://www.otrium.nl/dames",
    "https://www.parfumdreams.nl/",
    "https://www.paulaschoice.nl/nl",
    "https://www.plutosport.nl/",
    "https://www.pullandbear.com/nl/",
    "https://www.rituals.com/nl-nl/home",
    "https://www.sellpy.nl/",
    "https://www.shoeby.nl/",
    "https://www.shopcider.com/",
    "https://www.sissy-boy.com/",
    "https://www.smartphonehoesjes.nl/",
    "https://www.snipes.com/nl-nl/",
    "https://www.spacenk.com/nl/home",
    "https://www.stradivarius.com/nl/",
    "https://www.strongerlabel.com/nl",
    "https://www.temu.com/nl-en",
    "https://www.tessv.nl/",
    "https://www.thesting.com/nl-nl/dames",
    "https://www.thingsilikethingsilove.com/",
    "https://www.thuisbezorgd.nl/",
    "https://www.uniqlo.com/nl/nl/",
    "https://www.urbanoutfitters.com/",
    "https://www.veromoda.com/nl-nl",
    "https://www.weekday.com/nl-nl/women/",
    "https://www.wehkamp.nl/",
    "https://www.westwing.nl/",
    "https://www.xenos.nl/",
    "https://www.xoxowildhearts.com/",
    "https://www.yoursurprise.nl/",
    "https://www.zalando-lounge.nl/",
    "https://www.zalando.nl/dames-home/",
    "https://www.zara.com/nl/",
    "https://www2.hm.com/nl_nl/index.html",
    "https://xxlnutrition.com/nl",
    "https://zelesta.nl/"
]

OUTPUT_DIR = "screenshots"
os.makedirs(OUTPUT_DIR, exist_ok=True)


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
# PAGE READY WAITER
# ========================================

def wait_for_full_load(driver, timeout=15):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


# ========================================
# COOKIE CLICKER
# ========================================

def click_cookie_buttons(driver, timeout=5):
    keywords = [
        "accept", "agree", "allow", "consent",
        "akkoord", "accepteren", "alles accepteren",
        "alle cookies accepteren", "oké", "alles toestaan",
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
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(1)
                    return True
            except:
                continue
    except:
        pass

    return False


# ========================================
# NUCLEAR COOKIE CLEANUP (ORIGINEEL)
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
# GENERIC CLOSE BUTTON CLICKER
# ========================================

def click_generic_close_buttons(driver, timeout=3):
    keywords = [
        "close", "sluit", "nee bedankt",
        "no thanks", "later", "misschien later",
        "×"
    ]

    xpath_conditions = " or ".join(
        [f"contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{k}')"
         for k in keywords]
    )

    xpath = f"""
        //button[{xpath_conditions}] |
        //a[{xpath_conditions}] |
        //*[@aria-label='close'] |
        //*[@class[contains(., 'close')]]
    """

    try:
        elements = WebDriverWait(driver, timeout).until(
            EC.presence_of_all_elements_located((By.XPATH, xpath))
        )

        for el in elements:
            try:
                if el.is_displayed() and el.is_enabled():
                    driver.execute_script("arguments[0].click();", el)
                    time.sleep(0.5)
            except:
                continue
    except:
        pass


# ========================================
# REMOVE LARGE OVERLAYS (AGRESSIEF)
# ========================================

def remove_large_overlays(driver):
    js = """
    document.querySelectorAll('div, section').forEach(el => {
        const style = window.getComputedStyle(el);
        if (style.position === 'fixed' && parseInt(style.zIndex) > 1000) {
            el.remove();
        }
    });

    document.body.style.overflow = "auto";
    document.documentElement.style.overflow = "auto";
    """
    driver.execute_script(js)


# ========================================
# IFRAME POPUP HANDLER
# ========================================

def handle_iframe_popups(driver):
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    for iframe in iframes:
        try:
            driver.switch_to.frame(iframe)
            click_generic_close_buttons(driver, timeout=1)
            driver.switch_to.default_content()
        except:
            driver.switch_to.default_content()
            continue


# ========================================
# MAIN LOOP
# ========================================

for i, url in enumerate(URLS):
    print(f"\nOpening {url}")

    try:
        driver.get(url)

        wait_for_full_load(driver)
        time.sleep(3)

        driver.execute_script("window.scrollTo(0, 0);")

        # Eerst netjes proberen
        click_cookie_buttons(driver)
        nuclear_cookie_cleanup(driver)

        # Dan meerdere rondes popup killing
        for _ in range(3):
            click_generic_close_buttons(driver)
            handle_iframe_popups(driver)
            remove_large_overlays(driver)
            time.sleep(1)

        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "").split(".")[0]

        screenshot_path = os.path.join(OUTPUT_DIR, f"{domain}.png")
        driver.save_screenshot(screenshot_path)

        print(f"Saved: {screenshot_path}")

    except Exception as e:
        print(f"Error on {url}: {e}")
        continue


driver.quit()
print("\nDone.")