import os
import sys
import logging
from datetime import datetime

LOG_DIR = os.path.abspath("./logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app.log")

# Központi logger beállítása UTF-8 támogatással
logger = logging.getLogger("EpicAutoClaimer")
logger.setLevel(logging.INFO)

# Fájlba mentés
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
logger.addHandler(file_handler)

# Konzolra kiírás (ha nem no-console .exe-ként fut)
if sys.stdout is not None:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(console_handler)

# GUI feliratkozók (a Tkinter felület élő frissítéséhez)
_gui_callbacks = []


def register_gui_callback(callback):
    """Regisztrál egy GUI függvényt, ami megkapja a naplóüzeneteket."""
    if callback not in _gui_callbacks:
        _gui_callbacks.append(callback)


def log(msg):
    """Ezt hívja a program mindenhol print helyett."""
    clean_msg = str(msg).strip()
    if not clean_msg:
        return
    logger.info(clean_msg)
    time_str = datetime.now().strftime("%H:%M:%S")
    formatted_gui_msg = f"[{time_str}] {clean_msg}"
    for cb in _gui_callbacks:
        try:
            cb(formatted_gui_msg)
        except Exception:
            pass