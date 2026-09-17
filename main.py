import os
import sys
import time
import sqlite3
import requests
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from PIL import Image, ImageDraw
import pystray
from playwright.sync_api import sync_playwright

DB_FILE = "epic_bot.db"
PROFILES_DIR = "./profiles"
os.makedirs(PROFILES_DIR, exist_ok=True)

# ---------------------------------------------------------
# 1. ADATBÁZIS KEZELÉS (SQLite)
# ---------------------------------------------------------
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                profile_dir TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS claimed_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT,
                game_slug TEXT,
                game_title TEXT,
                claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(account_name, game_slug)
            )
        """)
        conn.commit()

def get_accounts():
    with sqlite3.connect(DB_FILE) as conn:
        return conn.cursor().execute("SELECT name, profile_dir FROM accounts").fetchall()

def add_account(name):
    profile_dir = os.path.abspath(os.path.join(PROFILES_DIR, name))
    with sqlite3.connect(DB_FILE) as conn:
        conn.cursor().execute("INSERT OR IGNORE INTO accounts (name, profile_dir) VALUES (?, ?)", (name, profile_dir))
        conn.commit()
    return profile_dir

def is_game_claimed(account_name, game_slug):
    with sqlite3.connect(DB_FILE) as conn:
        res = conn.cursor().execute(
            "SELECT id FROM claimed_games WHERE account_name = ? AND game_slug = ?",
            (account_name, game_slug)
        ).fetchone()
        return res is not None

def mark_game_claimed(account_name, game_slug, title):
    with sqlite3.connect(DB_FILE) as conn:
        conn.cursor().execute(
            "INSERT OR REPLACE INTO claimed_games (account_name, game_slug, game_title) VALUES (?, ?, ?)",
            (account_name, game_slug, title)
        )
        conn.commit()

# ---------------------------------------------------------
# 2. INGYENES JÁTÉKOK LEKÉRDEZÉSE (API)
# ---------------------------------------------------------
def fetch_free_games():
    url = "https://store-site-backend-static.akamaized.net/freeGamesPromotions?locale=hu-HU&country=HU&allowCountries=HU"
    try:
        r = requests.get(url, timeout=15).json()
        elements = r["data"]["Catalog"]["searchStore"]["elements"]
        active_games = []

        for item in elements:
            promotions = item.get("promotions")
            if not promotions or not promotions.get("promotionalOffers"):
                continue

            offers = promotions["promotionalOffers"][0].get("promotionalOffers", [])
            for offer in offers:
                if offer.get("discountSetting", {}).get("discountPercentage") == 0:
                    slug = item.get("productSlug")
                    if not slug:
                        mappings = item.get("offerMappings", [])
                        if mappings:
                            slug = mappings[0].get("pageSlug")
                    if slug:
                        active_games.append({
                            "title": item.get("title", "Ismeretlen játék"),
                            "slug": slug,
                            "url": f"https://store.epicgames.com/hu/p/{slug}"
                        })
        return active_games
    except Exception as e:
        print(f"[API HIBA] Nem sikerült lekérni a játékokat: {e}")
        return []

# ---------------------------------------------------------
# 3. AUTOMATIZÁLT BESZEDŐ (Playwright)
# ---------------------------------------------------------
def claim_for_account(acc_name, profile_dir, games, notify_fn):
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,  # Nem baj, ha felugrik az ablak
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = context.new_page()

        for game in games:
            slug = game["slug"]
            title = game["title"]

            if is_game_claimed(acc_name, slug):
                continue

            print(f"[{acc_name}] Beszerzés kísérlete: {title}")
            page.goto(game["url"])
            page.wait_for_load_state("domcontentloaded")
            time.sleep(3)

            # Korhatár gomb (ha van)
            continue_btn = page.locator("button:has-text('Folytatás'), button:has-text('Continue')")
            if continue_btn.is_visible():
                continue_btn.click()
                time.sleep(1.5)

            # Beszerzés / Get gomb keresése
            get_btn = page.locator("button[data-testid='purchase-cta-button']")
            if get_btn.is_visible() and ("get" in get_btn.inner_text().lower() or "beszerzés" in get_btn.inner_text().lower()):
                get_btn.click()
                time.sleep(4)

                # Fizetési ablak / Megrendelés elküldése gomb
                order_btn = page.locator("button:has-text('Megrendelés elküldése'), button:has-text('Place Order')")
                if order_btn.is_visible():
                    order_btn.click()
                    time.sleep(5)
                    mark_game_claimed(acc_name, slug, title)
                    notify_fn("Epic Games Bot", f"Sikeresen beszerezve: {title} ({acc_name})")
                else:
                    # Ha iframe-ben van a fizetés
                    frames = page.frames
                    for frame in frames:
                        f_order_btn = frame.locator("button:has-text('Megrendelés elküldése'), button:has-text('Place Order')")
                        if f_order_btn.is_visible():
                            f_order_btn.click()
                            time.sleep(5)
                            mark_game_claimed(acc_name, slug, title)
                            notify_fn("Epic Games Bot", f"Sikeresen beszerezve: {title} ({acc_name})")
                            break
            else:
                # Ha már a könyvtárban van, rögzítjük az adatbázisban, hogy legközelebb ne nézze
                mark_game_claimed(acc_name, slug, title)

        context.close()

# ---------------------------------------------------------
# 4. HÁTTÉRBEN FUTÓ FIGYELŐ (Ütemező)
# ---------------------------------------------------------
def background_worker(notify_fn):
    while True:
        now = datetime.now()
        # Karácsonyi időszak: Dec 15 - Jan 5 (minden nap aktív)
        is_xmas = (now.month == 12 and now.day >= 15) or (now.month == 1 and now.day <= 5)

        # Heti időszak: Csütörtök (weekday == 3) 17:00 után, vagy karácsonykor bármely nap
        should_check = is_xmas or (now.weekday() == 3 and now.hour >= 17)

        # Ha éppen aktív az időszak, ellenőrizzük az API-t
        if should_check:
            games = fetch_free_games()
            accounts = get_accounts()
            for name, p_dir in accounts:
                unclaimed = [g for g in games if not is_game_claimed(name, g["slug"])]
                if unclaimed:
                    notify_fn("Epic Games Bot", f"Új játék észlelve! Beszerzés indítása: {name}...")
                    claim_for_account(name, p_dir, unclaimed, notify_fn)

        # 30 percenként fut le a háttérellenőrzés
        time.sleep(1800)

# ---------------------------------------------------------
# 5. FIÓKKEZELŐ GRAFIKUS FELÜLET (Tkinter GUI)
# ---------------------------------------------------------
class AccountManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Epic Games Bot - Fiókok")
        self.root.geometry("450x300")
        self.root.resizable(False, False)

        frame = ttk.Frame(root, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Regisztrált Fiókok:", font=("Arial", 10, "bold")).pack(anchor=tk.W)

        self.listbox = tk.Listbox(frame, height=6)
        self.listbox.pack(fill=tk.X, pady=5)
        self.refresh_accounts()

        btn_box = ttk.Frame(frame)
        btn_box.pack(fill=tk.X, pady=5)

        ttk.Button(btn_box, text="Belépés / 2FA beállítása a kijelölt fiókhoz", command=self.login_account).pack(side=tk.LEFT, fill=tk.X, expand=True)

        new_acc_frame = ttk.LabelFrame(frame, text="Új fiók hozzáadása", padding=5)
        new_acc_frame.pack(fill=tk.X, pady=10)

        self.acc_entry = ttk.Entry(new_acc_frame)
        self.acc_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        ttk.Button(new_acc_frame, text="Hozzáadás", command=self.add_acc_click).pack(side=tk.RIGHT)

    def refresh_accounts(self):
        self.listbox.delete(0, tk.END)
        for name, _ in get_accounts():
            self.listbox.insert(tk.END, name)

    def add_acc_click(self):
        name = self.acc_entry.get().strip()
        if name:
            add_account(name)
            self.acc_entry.delete(0, tk.END)
            self.refresh_accounts()
            messagebox.showinfo("Siker", f"'{name}' profil létrehozva. Kattints a 'Belépés' gombra a bejelentkezéshez!")

    def login_account(self):
        selected = self.listbox.curselection()
        if not selected:
            messagebox.showwarning("Figyelem", "Válassz ki egy fiókot a listából!")
            return
        name = self.listbox.get(selected[0])
        p_dir = os.path.abspath(os.path.join(PROFILES_DIR, name))

        def open_browser():
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=p_dir,
                    headless=False
                )
                page = context.new_page()
                page.goto("https://store.epicgames.com/login")
                # Várakozás, amíg a felhasználó végez és bezárja az ablakot
                page.wait_for_timeout(120000)
                context.close()

        threading.Thread(target=open_browser, daemon=True).start()
        messagebox.showinfo("Böngésző indítása", "A böngésző megnyílt. Jelentkezz be az Epic Games fiókodba, majd zárd be a böngészőt.")

# ---------------------------------------------------------
# 6. TÁLCAIKON ÉS INDÍTÓ RENDSZER (Pystray)
# ---------------------------------------------------------
def create_image():
    # Egyszerű tálcaikon rajzolása (kék kör)
    image = Image.new('RGB', (64, 64), color=(30, 30, 30))
    dc = ImageDraw.Draw(image)
    dc.ellipse((12, 12, 52, 52), fill=(0, 122, 255))
    return image

def main():
    init_db()

    # Fő Tkinter ablak (rejtve tartjuk, csak a menüből nyílik)
    root = tk.Tk()
    root.withdraw()
    app_gui = [None]

    def notify(title, msg):
        if icon:
            icon.notify(msg, title)

    # Háttérszál indítása a figyelőhöz
    t = threading.Thread(target=background_worker, args=(notify,), daemon=True)
    t.start()

    def open_gui(icon, item):
        def show():
            win = tk.Toplevel(root)
            AccountManagerGUI(win)
        root.after(0, show)

    def manual_check(icon, item):
        notify("Epic Games Bot", "Azonnali ellenőrzés elindítva...")
        def run():
            games = fetch_free_games()
            for name, p_dir in get_accounts():
                claim_for_account(name, p_dir, games, notify)
            notify("Epic Games Bot", "Azonnali ellenőrzés befejeződött.")
        threading.Thread(target=run, daemon=True).start()

    def exit_action(icon, item):
        icon.stop()
        root.quit()
        sys.exit()

    menu = pystray.Menu(
        pystray.MenuItem("Fiókok kezelése", open_gui),
        pystray.MenuItem("Azonnali beszedés most", manual_check),
        pystray.MenuItem("Kilépés", exit_action)
    )

    icon = pystray.Icon("EpicClaimer", create_image(), "Epic Games Auto-Claimer", menu)
    threading.Thread(target=icon.run, daemon=True).start()

    # Tkinter fő hurok futtatása
    root.mainloop()

if __name__ == "__main__":
    main()