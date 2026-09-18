import os
import time
import random
import logging
import subprocess
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from src.database import is_game_claimed, mark_game_claimed

logger = logging.getLogger("EpicClaimer")


def human_delay(min_sec=2.0, max_sec=5.0):
    """Emberi reakcióidőt szimuláló lebegőpontos véletlenszerű várakozás."""
    time.sleep(random.uniform(min_sec, max_sec))


def _get_system_chrome_path():
    """Megkeresi a valódi Google Chrome elérési útját a Windowson."""
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
    """Natív böngésző indítása manuális belépéshez és 2FA kezeléshez."""
    chrome_path = _get_system_chrome_path()

    if chrome_path:
        print(f"[Login] Natív Google Chrome indítása: {chrome_path}")
        cmd = [
            chrome_path,
            f"--user-data-dir={os.path.abspath(profile_dir)}",
            "--no-first-run",
            "--no-default-browser-check",
            "https://store.epicgames.com/login"
        ]
        proc = subprocess.Popen(cmd)
        proc.wait()
        print("[Login] Böngésző bezárva, a munkamenet elmentve.")
    else:
        print("[Login] Chrome nem található a szokásos helyen, Playwright indítása...")
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                headless=False,
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = context.new_page()
            page.goto("https://store.epicgames.com/login")
            for _ in range(180):
                if context.pages and not page.is_closed():
                    time.sleep(1)
                else:
                    break
            context.close()


def _launch_browser(playwright_instance, profile_dir, headless=False):
    """Automatizált böngésző futtatása felkészítve a botvédelem ellen."""
    launch_args = [
        "--disable-blink-features=AutomationControlled",
        "--start-maximized"
    ]
    ignore_args = ["--enable-automation"]

    try:
        context = playwright_instance.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=headless,
            channel="chrome",
            args=launch_args,
            ignore_default_args=ignore_args,
            no_viewport=True
        )
    except Exception:
        context = playwright_instance.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=headless,
            args=launch_args,
            ignore_default_args=ignore_args,
            no_viewport=True
        )

    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    """)
    return context


def claim_for_account(acc_name, profile_dir, games, notify_fn):
    """Végrehajtja a beszerzéseket emberi reakcióidőkkel."""
    with sync_playwright() as p:
        context = _launch_browser(p, profile_dir, headless=False)
        try:
            page = context.pages[0] if context.pages else context.new_page()

            for game in games:
                slug = game["slug"]
                title = game["title"]

                if is_game_claimed(acc_name, slug):
                    continue

                try:
                    print(f"[{acc_name}] Beszerzés kísérlete: {title}")
                    page.goto(game["url"], wait_until="domcontentloaded", timeout=45000)
                    human_delay(3.2, 6.5)

                    # Korhatár modal kezelése
                    age_gate = page.locator("button:has-text('Folytatás'), button:has-text('Continue')")
                    if age_gate.is_visible(timeout=3000):
                        age_gate.click()
                        human_delay(1.5, 3.0)

                    # 'Get' vagy 'Beszerzés' gomb leütése
                    get_btn = page.locator("button[data-testid='purchase-cta-button']")
                    if not get_btn.is_visible(timeout=5000):
                        print(f"[{acc_name}] A Get gomb nem található: {title}")
                        continue

                    btn_text = get_btn.inner_text().strip().lower()
                    if not any(k in btn_text for k in ["get", "beszerzés"]):
                        print(f"[{acc_name}] Már megvan a könyvtárban: {title}")
                        mark_game_claimed(acc_name, slug, title)
                        continue

                    get_btn.click()
                    human_delay(2.5, 4.8)

                    # Rendelés gomb kezelése (főoldalon vagy iframe-ben)
                    order_success = False
                    order_btn = page.locator("button:has-text('Megrendelés elküldése'), button:has-text('Place Order')")

                    if order_btn.is_visible(timeout=4000):
                        order_btn.click()
                        order_success = True
                    else:
                        for frame in page.frames:
                            f_btn = frame.locator("button:has-text('Megrendelés elküldése'), button:has-text('Place Order')")
                            if f_btn.is_visible(timeout=2000):
                                f_btn.click()
                                order_success = True
                                break

                    if order_success:
                        human_delay(5.0, 8.0)
                        mark_game_claimed(acc_name, slug, title)
                        notify_fn("EpicAutoClaimer", f"Sikeresen beszerezve: {title} ({acc_name})")
                        print(f"[{acc_name}] Sikeres rendelés: {title}")
                    else:
                        print(f"[{acc_name}] Nem sikerült a rendelés gombra kattintani: {title}")

                except PlaywrightTimeoutError:
                    logger.warning(f"[{acc_name}] Időtúllépés: {title}")
                except Exception as inner_err:
                    logger.error(f"[{acc_name}] Hiba történt ({title}): {inner_err}")

        except Exception as outer_err:
            logger.critical(f"[{acc_name}] Hiba a folyamatban: {outer_err}")
        finally:
            try:
                context.close()
            except Exception:
                pass