import time
from playwright.sync_api import sync_playwright
from src.database import is_game_claimed, mark_game_claimed

def open_manual_login(profile_dir):
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False
        )
        page = context.new_page()
        page.goto("https://store.epicgames.com/login")
        # 2 perc várakozási idő manuális belépésre és 2FA-ra
        page.wait_for_timeout(120000)
        context.close()

def claim_for_account(acc_name, profile_dir, games, notify_fn):
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = context.new_page()

        for game in games:
            slug = game["slug"]
            title = game["title"]

            if is_game_claimed(acc_name, slug):
                continue

            page.goto(game["url"])
            page.wait_for_load_state("domcontentloaded")
            time.sleep(3)

            # Korhatár modal ablak kezelése
            continue_btn = page.locator("button:has-text('Folytatás'), button:has-text('Continue')")
            if continue_btn.is_visible():
                continue_btn.click()
                time.sleep(1.5)

            # 'Get' vagy 'Beszerzés' gomb leütése
            get_btn = page.locator("button[data-testid='purchase-cta-button']")
            if get_btn.is_visible() and any(k in get_btn.inner_text().lower() for k in ["get", "beszerzés"]):
                get_btn.click()
                time.sleep(5)

                # Megrendelés jóváhagyása
                order_btn = page.locator("button:has-text('Megrendelés elküldése'), button:has-text('Place Order')")
                if order_btn.is_visible():
                    order_btn.click()
                    time.sleep(5)
                    mark_game_claimed(acc_name, slug, title)
                    notify_fn("EpicAutoClaimer", f"Sikeresen beszerezve: {title} ({acc_name})")
                else:
                    # Fizetési iframe keresése
                    for frame in page.frames:
                        f_order_btn = frame.locator("button:has-text('Megrendelés elküldése'), button:has-text('Place Order')")
                        if f_order_btn.is_visible():
                            f_order_btn.click()
                            time.sleep(5)
                            mark_game_claimed(acc_name, slug, title)
                            notify_fn("EpicAutoClaimer", f"Sikeresen beszerezve: {title} ({acc_name})")
                            break
            else:
                # Már a könyvtárban van vagy nem kattintható
                mark_game_claimed(acc_name, slug, title)

        context.close()