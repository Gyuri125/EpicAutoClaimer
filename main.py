import sys
import time
import random
import threading
import tkinter as tk
from PIL import Image, ImageDraw
import pystray

from src.database import init_db, get_accounts, is_game_claimed
from src.epic_api import fetch_free_games
from src.claimer import claim_for_account
from src.scheduler import should_execute_check
from src.gui import AccountManagerGUI


def create_tray_icon():
    image = Image.new('RGB', (64, 64), color=(30, 30, 30))
    dc = ImageDraw.Draw(image)
    dc.ellipse((12, 12, 52, 52), fill=(0, 122, 255))
    return image


def background_worker(notify_fn):
    """Háttérfolyamat véletlenszerűsített (anti-bot) időzítéssel."""
    while True:
        if should_execute_check():
            games = fetch_free_games()
            accounts = get_accounts()

            # Megnézzük, van-e egyáltalán olyan játék, ami még hiányzik valamelyik fiókból
            any_unclaimed = any(
                not is_game_claimed(name, g["slug"])
                for name, _ in accounts
                for g in games
            )

            if any_unclaimed:
                # Véletlenszerű várakozás 10 és 90 perc között, hogy soha ne azonos percben fusson
                delay_minutes = random.randint(10, 90)
                print(f"[Ütemező] Új játék elérhető. Véletlenszerű várakozás: {delay_minutes} perc...")
                time.sleep(delay_minutes * 60)

                # Véletlenszerűsített fióksorrend
                shuffled_accounts = accounts.copy()
                random.shuffle(shuffled_accounts)

                for index, (name, p_dir) in enumerate(shuffled_accounts):
                    unclaimed = [g for g in games if not is_game_claimed(name, g["slug"])]
                    if unclaimed:
                        claim_for_account(name, p_dir, unclaimed, notify_fn)

                        # Ha még van hátra további fiók, 2-6 perc szünetet tartunk közöttük
                        if index < len(shuffled_accounts) - 1:
                            wait_between = random.uniform(120, 360)
                            print(f"[Ütemező] Fiókok közötti várakozás: {int(wait_between)} mp...")
                            time.sleep(wait_between)

        # 30 perces ellenőrzési ciklus a háttérben
        time.sleep(1800)


def main():
    init_db()

    root = tk.Tk()
    root.withdraw()

    def notify(title, msg):
        if icon:
            icon.notify(msg, title)

    # Időzített háttérszál indítása
    worker_thread = threading.Thread(target=background_worker, args=(notify,), daemon=True)
    worker_thread.start()

    def open_gui(icon, item):
        def show():
            win = tk.Toplevel(root)
            AccountManagerGUI(win)
        root.after(0, show)

    def manual_check(icon, item):
        notify("EpicAutoClaimer", "Azonnali ellenőrzés elindítva...")

        def run():
            games = fetch_free_games()
            accounts = get_accounts()
            for index, (name, p_dir) in enumerate(accounts):
                unclaimed = [g for g in games if not is_game_claimed(name, g["slug"])]
                if unclaimed:
                    claim_for_account(name, p_dir, unclaimed, notify)
                    if index < len(accounts) - 1:
                        time.sleep(random.uniform(5, 10))
            notify("EpicAutoClaimer", "Azonnali beszerzési folyamat befejeződött.")

        threading.Thread(target=run, daemon=True).start()

    def exit_action(icon, item):
        icon.stop()
        root.quit()
        sys.exit()

    menu = pystray.Menu(
        pystray.MenuItem("Fiókok kezelése", open_gui),
        pystray.MenuItem("Azonnali beszerzés most", manual_check),
        pystray.MenuItem("Kilépés", exit_action)
    )

    icon = pystray.Icon("EpicAutoClaimer", create_tray_icon(), "EpicAutoClaimer", menu)
    threading.Thread(target=icon.run, daemon=True).start()

    root.mainloop()


if __name__ == "__main__":
    main()