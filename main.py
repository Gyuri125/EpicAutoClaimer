import os
import sys
import threading
import tkinter as tk
from PIL import Image, ImageDraw
import pystray

from src.database import init_db
from src.gui import AccountManagerGUI
from src.claimer import claim_all_accounts
from src.logger import LOG_FILE
import src.scheduler as scheduler


def create_tray_icon():
    image = Image.new('RGB', (64, 64), color=(25, 25, 25))
    dc = ImageDraw.Draw(image)
    dc.ellipse((14, 14, 50, 50), fill=(0, 150, 255))
    return image


def main():
    init_db()

    root = tk.Tk()
    root.withdraw()
    gui_window = None

    def notify(title, msg):
        if icon:
            icon.notify(msg, title)

    # Háttérben futó ütemező szál
    def background_loop():
        while True:
            if scheduler.is_claim_time_now():
                claim_all_accounts(notify)
            # 30 percenkénti vizsgálat
            threading.Event().wait(1800)

    threading.Thread(target=background_loop, daemon=True).start()

    def open_gui(icon=None, item=None):
        nonlocal gui_window
        def show():
            nonlocal gui_window
            if gui_window is None or not tk.Toplevel.winfo_exists(gui_window):
                gui_window = tk.Toplevel(root)
                AccountManagerGUI(gui_window, notify_fn=notify)
            else:
                gui_window.lift()
                gui_window.focus_force()
        root.after(0, show)

    def manual_claim(icon=None, item=None):
        threading.Thread(target=lambda: claim_all_accounts(notify), daemon=True).start()

    def open_logs(icon=None, item=None):
        if os.path.exists(LOG_FILE):
            os.startfile(LOG_FILE)

    def exit_app(icon, item):
        icon.stop()
        root.quit()
        sys.exit()

    menu = pystray.Menu(
        pystray.MenuItem("Vezérlőpult megnyitása", open_gui, default=True),
        pystray.MenuItem("Azonnali beszerzés most (Összes fiók)", manual_claim),
        pystray.MenuItem("Naplófájl megnyitása (.log)", open_logs),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Kilépés", exit_app)
    )

    icon = pystray.Icon("EpicClaimer", create_tray_icon(), "Epic Games Auto-Claimer", menu)
    threading.Thread(target=icon.run, daemon=True).start()

    root.mainloop()


if __name__ == "__main__":
    main()