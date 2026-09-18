import os
import re
import time
import random
import subprocess
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from src.database import get_accounts, is_game_claimed, mark_game_claimed
from src.epic_api import fetch_free_games
from src.logger import log

DEBUG_PORT = 9222
SCREENSHOTS_DIR = os.path.abspath("./debug_screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

active_manual_process = None


def is_manual_browser_open():
    global active_manual_process
    if active_manual_process is not None:
        if active_manual_process.poll() is None:
            return True
        active_manual_process = None
    return False


def human_delay(min_sec=1.5, max_sec=3.0):
    time.sleep(random.uniform(min_sec, max_sec))


def _save_debug_screenshot(page, title, tag="hiba"):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_title = re.sub(r'[\\/*?:"<>| ]', '_', title)
        filepath = os.path.join(SCREENSHOTS_DIR, f"{clean_title}_{tag}_{timestamp}.png")
        page.screenshot(path=filepath)
        log(f"[Screenshot] Hibakép elmentve: {filepath}")
    except Exception:
        pass


def _get_system_chrome_path():
    candidates = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def open_manual_login(profile_dir):
    global active_manual_process
    chrome_path = _get_system_chrome_path()

    cmd = [
        chrome_path or "chrome",
        f"--user-data-dir={os.path.abspath(profile_dir)}",
        "--no-first-run",
        "--no-default-browser-check",
        "https://store.epicgames.com/hu"
    ]
    active_manual_process = subprocess.Popen(cmd)
    active_manual_process.wait()
    active_manual_process = None


def _handle_checkout_modal(page, acc_name, title):
    target_button_texts = [
        "Hozzáadás a könyvtárhoz",
        "Add to Library",
        "Megrendelés elküldése",
        "Place Order"
    ]

    checkout_target = None
    action_btn = None

    for _ in range(15):
        for btn_text in target_button_texts:
            candidate = page.locator(f"button:has-text('{btn_text}')").first
            if candidate.is_visible():
                checkout_target = page
                action_btn = candidate
                break

        if not checkout_target:
            for frame in page.frames:
                try:
                    for btn_text in target_button_texts:
                        candidate = frame.locator(f"button:has-text('{btn_text}')").first
                        if candidate.is_visible():
                            checkout_target = frame
                            action_btn = candidate
                            break
                except Exception:
                    pass
                if checkout_target:
                    break

        if checkout_target:
            break
        time.sleep(1)

    if not checkout_target or not action_btn:
        _save_debug_screenshot(page, title, tag="nincs_checkout")
        return False

    body_text = checkout_target.locator("body").inner_text().lower()
    if not any(term in body_text for term in ["0 ft", "0,00 ft", "0.00", "free", "ingyenes"]):
        log(f"[{acc_name}] [VESZÉLY] Nem 0 Ft az ár! Folyamat megszakítva.")
        _save_debug_screenshot(page, title, tag="nem_ingyenes")
        return False

    action_btn.click(force=True)
    human_delay(2.0, 3.0)

    for context in [page] + page.frames:
        try:
            accept_btn = context.locator("button:has-text('Elfogadom'), button:has-text('I Agree')").first
            if accept_btn.is_visible(timeout=2500):
                accept_btn.click(force=True)
                human_delay(2.0, 3.0)
                break
        except Exception:
            pass

    for context in [page] + page.frames:
        try:
            if context.locator("text=/köszönjük|thank you/i").first.is_visible(timeout=4000):
                return True
        except Exception:
            pass

    for _ in range(8):
        if page.locator("button:has-text('Könyvtárban'), button:has-text('In Library')").first.is_visible():
            return True
        time.sleep(1)

    return False


def claim_for_account(acc_name, profile_dir, games, notify_fn):
    unclaimed_games = []
    for g in games:
        if is_game_claimed(acc_name, g["slug"]):
            log(f"[{acc_name}] ℹ️ Már beszerezve az adatbázis szerint: {g['title']}")
        else:
            unclaimed_games.append(g)

    if not unclaimed_games:
        log(f"[{acc_name}] ✅ MINDEN heti ingyenes játék ({len(games)} db) már megvan! Nincs szükség böngészőre.")
        return

    log(f"[{acc_name}] 🚀 {len(unclaimed_games)} db játék beszerzése indul...")

    if is_manual_browser_open():
        log(f"[{acc_name}] ⚠️ Zárd be a kézi bejelentkező böngészőt a beszerzés előtt!")
        notify_fn("EpicAutoClaimer Hiba", f"Zárd be a böngészőablakot ({acc_name})!")
        return

    chrome_path = _get_system_chrome_path()
    if not chrome_path:
        log(f"[{acc_name}] Nem található Google Chrome.")
        return

    cmd = [
        chrome_path,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={os.path.abspath(profile_dir)}",
        "--no-first-run",
        "--no-default-browser-check",
        "--start-maximized"
    ]
    proc = subprocess.Popen(cmd)

    try:
        with sync_playwright() as p:
            browser = None
            for attempt in range(6):
                try:
                    time.sleep(1.2)
                    browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{DEBUG_PORT}", timeout=10000)
                    break
                except Exception:
                    if attempt == 5:
                        log(f"[{acc_name}] Nem sikerült csatlakozni a böngészőhöz.")
                        return

            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.pages[0] if context.pages else context.new_page()

            for game in unclaimed_games:
                slug = game["slug"]
                title = game["title"]

                try:
                    log(f"[{acc_name}] 🌐 Betöltés: {title}")
                    page.goto(game["url"], wait_until="domcontentloaded", timeout=45000)
                    human_delay(2.5, 3.5)

                    for sel in ["button:has-text('Folytatás')", "button:has-text('Continue')"]:
                        btn = page.locator(sel)
                        if btn.is_visible(timeout=1500):
                            btn.click()
                            human_delay(1.0, 1.5)
                            break

                    page.mouse.wheel(0, 300)
                    human_delay(1.5, 2.0)

                    in_library_loc = page.locator(
                        "button:has-text('Könyvtárban'), button:has-text('In Library'), button:has-text('A könyvtárban')"
                    ).first

                    if in_library_loc.is_visible(timeout=3000):
                        log(f"[{acc_name}] 📦 A játék már korábban a könyvtáradban volt: {title}")
                        mark_game_claimed(acc_name, slug, title)
                        continue

                    get_btn = page.locator(
                        "button[data-testid='purchase-cta-button'], aside button:has-text('Beszerzés'), aside button:has-text('Get')"
                    ).first

                    if not get_btn.is_visible(timeout=3000):
                        log(f"[{acc_name}] ⚠️ Nem található a Beszerzés gomb: {title}")
                        _save_debug_screenshot(page, title, tag="nincs_get_gomb")
                        continue

                    btn_text = get_btn.inner_text().strip().lower()
                    if "könyvtár" in btn_text or "library" in btn_text:
                        log(f"[{acc_name}] 📦 Gomb alapján már a könyvtárban van: {title}")
                        mark_game_claimed(acc_name, slug, title)
                        continue

                    get_btn.click()
                    log(f"[{acc_name}] 🛒 Kosár / Pénztár folyamat indítása...")

                    if _handle_checkout_modal(page, acc_name, title):
                        mark_game_claimed(acc_name, slug, title)
                        notify_fn("EpicAutoClaimer", f"Sikeresen beszerezve: {title} ({acc_name})")
                        log(f"[{acc_name}] 🎉 Tranzakció sikeres: {title}")
                    else:
                        log(f"[{acc_name}] ❌ Nem sikerült beszerezni: {title}")

                except PlaywrightTimeoutError:
                    _save_debug_screenshot(page, title, tag="timeout")
                    log(f"[{acc_name}] Időtúllépés ennél a játéknál: {title}")
                except Exception as err:
                    _save_debug_screenshot(page, title, tag="hiba")
                    log(f"[{acc_name}] Hiba: {err}")

    finally:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            pass


def claim_all_accounts(notify_fn=None):
    """Minden fiókot sorban lekezelő központi függvény."""
    notify = notify_fn if notify_fn else lambda t, m: None
    log("==========================================")
    log("⚡ ÖSSZES FIÓK BESZERZÉSE ELINDULT")
    log("==========================================")

    games = fetch_free_games()
    if not games:
        log("⚠️ Nem sikerült ingyenes játékokat találni az Epic API-ból.")
        return

    accounts = get_accounts()
    if not accounts:
        log("⚠️ Nincsenek mentett fiókok az adatbázisban!")
        return

    log(f"Talált aktív játékok ({len(games)} db): {[g['title'] for g in games]}")

    for idx, (name, p_dir) in enumerate(accounts):
        log(f"\n--- [{idx + 1}/{len(accounts)}] Fiók vizsgálata: {name} ---")
        claim_for_account(name, p_dir, games, notify)
        if idx < len(accounts) - 1:
            log("Rövid szünet a következő fiók előtt (5 mp)...")
            time.sleep(5)

    log("\n==========================================")
    log("✅ Összes fiók ellenőrzése befejeződött!")
    log("==========================================")
    notify("EpicAutoClaimer", "Az összes fiók ellenőrzése lezárult.")