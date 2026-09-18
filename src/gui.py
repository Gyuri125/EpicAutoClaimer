import os
import sqlite3
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from src.database import get_accounts, add_account
from src.claimer import open_manual_login, claim_for_account, claim_all_accounts, is_manual_browser_open
from src.epic_api import fetch_free_games
from src.logger import register_gui_callback, LOG_FILE
import src.scheduler as scheduler


class AccountManagerGUI:
    def __init__(self, root, notify_fn=None):
        self.root = root
        self.notify_fn = notify_fn if notify_fn else lambda t, m: None
        self.root.title("EpicAutoClaimer Vezérlőpult")
        self.root.geometry("620x680")
        self.root.minsize(580, 600)

        main_frame = ttk.Frame(root, padding=12)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Rendszer és Ütemező Státusz
        status_box = ttk.LabelFrame(main_frame, text="Rendszer Státusz", padding=8)
        status_box.pack(fill=tk.X, pady=(0, 8))

        last_check_str = scheduler.LAST_CHECK_TIME.strftime("%Y.%m.%d %H:%M:%S") if scheduler.LAST_CHECK_TIME else "Még nem futott vizsgálat"
        self.status_label = ttk.Label(status_box, text=f"Ütemező: AKTÍV (Háttérben fut)\nUtolsó vizsgálat: {last_check_str}", font=("Arial", 9))
        self.status_label.pack(anchor=tk.W)

        # 2. Fiókok listája és műveletek
        acc_box = ttk.LabelFrame(main_frame, text="Regisztrált Fiókok", padding=8)
        acc_box.pack(fill=tk.X, pady=(0, 8))

        self.listbox = tk.Listbox(acc_box, height=4, font=("Arial", 10))
        self.listbox.pack(fill=tk.X, pady=(0, 6))
        self.refresh_accounts()

        btn_row = ttk.Frame(acc_box)
        btn_row.pack(fill=tk.X, pady=2)

        ttk.Button(btn_row, text="🌐 Böngésző (Belépés)", command=self.open_browser_for_selected).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(btn_row, text="⚡ CSAK ennek a fióknak", command=self.claim_selected_only).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(btn_row, text="🚀 ÖSSZES fiók beszerzése", command=self.claim_all_click).pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=2)

        # Új fiók hozzáadása
        add_box = ttk.Frame(acc_box)
        add_box.pack(fill=tk.X, pady=(6, 0))
        self.acc_entry = ttk.Entry(add_box, font=("Arial", 10))
        self.acc_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.acc_entry.insert(0, "Új_fióknév")
        self.acc_entry.bind("<FocusIn>", lambda e: self.acc_entry.delete(0, tk.END) if "Új_" in self.acc_entry.get() else None)
        ttk.Button(add_box, text="Hozzáadás", command=self.add_acc_click).pack(side=tk.RIGHT)

        # 3. Élő Eseménynapló (Konzol nézet magában az ablakban)
        log_box = ttk.LabelFrame(main_frame, text="Élő Eseménynapló (Live Log)", padding=6)
        log_box.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        log_controls = ttk.Frame(log_box)
        log_controls.pack(fill=tk.X, pady=(0, 4))
        ttk.Button(log_controls, text="🧹 Törlés", width=10, command=self.clear_log).pack(side=tk.LEFT, padx=2)
        ttk.Button(log_controls, text="📂 Naplófájl megnyitása", command=self.open_log_file).pack(side=tk.RIGHT, padx=2)

        self.log_text = tk.Text(
            log_box,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#181818",
            fg="#dcdcdc",
            insertbackground="white"
        )
        log_scroll = ttk.Scrollbar(log_box, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Feliratkozás a központi naplóüzenetekre
        register_gui_callback(self.append_log)

        # 4. Legutóbb beszerzett játékok
        history_box = ttk.LabelFrame(main_frame, text="Adatbázisban lévő legutóbbi beszerzések", padding=6)
        history_box.pack(fill=tk.X)

        self.history_list = tk.Listbox(history_box, height=3, font=("Arial", 8))
        self.history_list.pack(fill=tk.X)
        self.refresh_history()

    def append_log(self, text):
        """Szálbiztos kiírás a Tkinter szövegdobozba."""
        def _insert():
            self.log_text.insert(tk.END, text + "\n")
            self.log_text.see(tk.END)
        self.root.after(0, _insert)

    def clear_log(self):
        self.log_text.delete("1.0", tk.END)

    def open_log_file(self):
        if os.path.exists(LOG_FILE):
            os.startfile(LOG_FILE)
        else:
            messagebox.showinfo("Információ", "A naplófájl még üres vagy nem jött létre.")

    def refresh_accounts(self):
        self.listbox.delete(0, tk.END)
        for name, _ in get_accounts():
            self.listbox.insert(tk.END, f"  {name}")
        if self.listbox.size() > 0:
            self.listbox.select_set(0)

    def refresh_history(self):
        self.history_list.delete(0, tk.END)
        try:
            with sqlite3.connect("epic_bot.db") as conn:
                rows = conn.cursor().execute(
                    "SELECT account_name, game_title, claimed_at FROM claimed_games ORDER BY id DESC LIMIT 10"
                ).fetchall()
                if not rows:
                    self.history_list.insert(tk.END, "Még nem történt beszerzés rögzítése.")
                for acc, title, dt in rows:
                    self.history_list.insert(tk.END, f"[{dt[:16]}] {title} -> {acc}")
        except Exception:
            pass

    def get_selected_account_name(self):
        selected = self.listbox.curselection()
        if not selected:
            return None
        return self.listbox.get(selected[0]).strip()

    def add_acc_click(self):
        name = self.acc_entry.get().strip()
        if name and not name.startswith("Új_"):
            add_account(name)
            self.acc_entry.delete(0, tk.END)
            self.refresh_accounts()
            messagebox.showinfo("Siker", f"'{name}' profil létrehozva!")

    def open_browser_for_selected(self):
        name = self.get_selected_account_name()
        if not name:
            messagebox.showwarning("Figyelem", "Válassz ki egy fiókot a listából!")
            return

        if is_manual_browser_open():
            messagebox.showwarning("Figyelem", "Egy böngészőablak már nyitva van. Zárd be!")
            return

        p_dir = os.path.abspath(os.path.join("./profiles", name))
        threading.Thread(target=lambda: open_manual_login(p_dir), daemon=True).start()

    def claim_selected_only(self):
        name = self.get_selected_account_name()
        if not name:
            messagebox.showwarning("Figyelem", "Válassz ki egy fiókot a listából!")
            return

        if is_manual_browser_open():
            messagebox.showwarning("Figyelem", "Zárd be a böngészőablakot a beszerzés előtt!")
            return

        p_dir = os.path.abspath(os.path.join("./profiles", name))
        self.status_label.config(text=f"Vizsgálat folyamatban ({name})...")

        def _run():
            games = fetch_free_games()
            claim_for_account(name, p_dir, games, self.notify_fn)
            self.root.after(0, lambda: self.status_label.config(text=f"Vizsgálat kész ({name})."))
            self.root.after(0, self.refresh_history)

        threading.Thread(target=_run, daemon=True).start()

    def claim_all_click(self):
        if is_manual_browser_open():
            messagebox.showwarning("Figyelem", "Zárd be a böngészőablakot a beszerzés előtt!")
            return
        threading.Thread(target=lambda: claim_all_accounts(self.notify_fn), daemon=True).start()