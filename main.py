import sys
import time
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
    while True:
        if should_execute_check():
            games = fetch_free_games()
            accounts = get_accounts()
            for name, p_dir in accounts:
                unclaimed = [g for g in games if not is_game_claimed(name, g["slug"])]
                if unclaimed:
                    notify_fn("EpicAutoClaimer", f"Új játék elérhető! Beszerzés indítása: {name}...")
                    claim_for_account(name, p_dir, unclaimed, notify_fn)
        # 30 perces ellenőrzési intervallum
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
            for name, p_dir in get_accounts():
                claim_for_account(name, p_dir, games, notify)
            notify("EpicAutoClaimer", "Azonnali beszerzési folyamat lefutott.")
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