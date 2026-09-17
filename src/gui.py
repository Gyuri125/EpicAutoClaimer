import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from src.database import get_accounts, add_account, PROFILES_DIR
from src.claimer import open_manual_login

class AccountManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("EpicAutoClaimer - Fiókkezelő")
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
            messagebox.showinfo("Siker", f"'{name}' létrehozva. Kattints a 'Belépés / 2FA' gombra a belépéshez.")

    def login_account(self):
        selected = self.listbox.curselection()
        if not selected:
            messagebox.showwarning("Figyelem", "Válassz ki egy fiókot a listából!")
            return
        name = self.listbox.get(selected[0])
        p_dir = os.path.join(PROFILES_DIR, name)

        threading.Thread(target=open_manual_login, args=(p_dir,), daemon=True).start()
        messagebox.showinfo("Böngésző indítása", "A böngésző megnyílik. Lépj be kézzel és hagyd jóvá a 2FA-t, majd zárd be a böngészőt.")