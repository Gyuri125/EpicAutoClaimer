import os
import sqlite3

DB_FILE = "epic_bot.db"
PROFILES_DIR = os.path.abspath("./profiles")
os.makedirs(PROFILES_DIR, exist_ok=True)

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
    profile_dir = os.path.join(PROFILES_DIR, name)
    os.makedirs(profile_dir, exist_ok=True)
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