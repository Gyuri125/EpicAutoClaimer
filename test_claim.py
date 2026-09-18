from src.database import init_db, get_accounts
from src.epic_api import fetch_free_games
from src.claimer import claim_for_account


def test_notify(title, msg):
    print(f"[ÉRTESÍTÉS] {title}: {msg}")


if __name__ == "__main__":
    init_db()
    accounts = get_accounts()

    if not accounts:
        print("[!] Nincs regisztrált fiók az adatbázisban! Előbb add hozzá a GUI-ban.")
        exit()

    print(f"[*] Talált fiókok: {[a[0] for a in accounts]}")
    games = fetch_free_games()
    print(f"[*] Beszerzendő játékok ({len(games)} db): {[g['title'] for g in games]}")

    # Csak az ELSŐ fiókkal teszteljük le élesben
    test_acc_name, test_acc_dir = accounts[0]
    print(f"\n---> Teszt indítása: {test_acc_name} <---")
    claim_for_account(test_acc_name, test_acc_dir, games, test_notify)