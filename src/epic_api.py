import os
import time
import requests
from playwright.sync_api import sync_playwright

GRAPHQL_URL = "https://store.epicgames.com/graphql"

GRAPHQL_QUERY = """
query freeGamesQuery($locale: String, $country: String, $allowCountries: String) {
  Catalog {
    searchStore(
      category: "freegames"
      locale: $locale
      country: $country
      allowCountries: $allowCountries
      count: 30
    ) {
      elements {
        title
        productSlug
        urlSlug
        offerMappings {
          pageSlug
        }
        promotions {
          promotionalOffers {
            promotionalOffers {
              discountSetting {
                discountPercentage
              }
            }
          }
        }
      }
    }
  }
}
"""

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def _fetch_via_graphql():
    print("[API: GraphQL] Lekérés indítása az Epic Store szerver felé...")
    payload = {
        "query": GRAPHQL_QUERY,
        "variables": {
            "locale": "hu",
            "country": "HU",
            "allowCountries": "HU"
        }
    }

    response = requests.post(GRAPHQL_URL, json=payload, headers=HEADERS, timeout=12)
    print(f"[API: GraphQL] Válasz státuszkód: {response.status_code}")

    if response.status_code != 200:
        return []

    data = response.json()
    elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])
    print(f"[API: GraphQL] Nyers elemek száma: {len(elements)}")

    active_games = []
    for item in elements:
        promotions = item.get("promotions")
        if not promotions or not promotions.get("promotionalOffers"):
            continue

        offers = promotions["promotionalOffers"][0].get("promotionalOffers", [])
        for offer in offers:
            if offer.get("discountSetting", {}).get("discountPercentage") == 0:
                slug = item.get("productSlug") or item.get("urlSlug")
                if not slug and item.get("offerMappings"):
                    slug = item["offerMappings"][0].get("pageSlug")

                if slug:
                    title = item.get("title", "Ismeretlen játék")
                    active_games.append({
                        "title": title,
                        "slug": slug,
                        "url": f"https://store.epicgames.com/hu/p/{slug}"
                    })
    return active_games


def _fetch_via_browser():
    print("[API: Böngésző] Tartalék felderítés indítása Chrome-mal...")
    games = []
    cache_dir = os.path.abspath("./profiles/.cache_browser")

    with sync_playwright() as p:
        try:
            # Valódi Chrome indítása az automatizációs jelzők rejtésével
            context = p.chromium.launch_persistent_context(
                user_data_dir=cache_dir,
                headless=True,
                channel="chrome",
                args=["--disable-blink-features=AutomationControlled"]
            )
        except Exception:
            context = p.chromium.launch_persistent_context(
                user_data_dir=cache_dir,
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )

        page = context.pages[0] if context.pages else context.new_page()
        try:
            page.goto("https://store.epicgames.com/hu/free-games", wait_until="domcontentloaded", timeout=35000)
            time.sleep(5)  # Megvárjuk az áruház kártyáinak kirajzolását

            links = page.locator("a[href*='/p/']").all()
            print(f"[API: Böngésző] Megtalált bolt linkek: {len(links)}")

            for link in links:
                try:
                    text = link.inner_text().lower()
                    href = link.get_attribute("href") or ""
                    parent_text = ""
                    try:
                        parent_text = link.locator("xpath=..").inner_text().lower()
                    except Exception:
                        pass

                    full_text = f"{text} {parent_text}"
                    # Csak a jelenleg futó ingyenes címek kellenek (a hamarosan érkezők nem)
                    if any(k in full_text for k in ["ingyenes most", "free now", "ingyenes"]):
                        slug = href.split("/p/")[-1].strip("/").split("?")[0]
                        title = link.inner_text().split("\n")[0].strip() or slug
                        if slug and not any(g["slug"] == slug for g in games):
                            games.append({
                                "title": title,
                                "slug": slug,
                                "url": f"https://store.epicgames.com/hu/p/{slug}"
                            })
                except Exception:
                    continue
        except Exception as e:
            print(f"[API: Böngésző Hiba] {e}")
        finally:
            context.close()

    return games


def fetch_free_games():
    """Elsődlegesen a GraphQL-ből kérdezi le a játékokat, szükség esetén böngészővel pótolja."""
    try:
        games = _fetch_via_graphql()
        if games:
            print(f"[API] Sikeres lekérdezés GraphQL-ből! Talált címek: {len(games)}")
            return games
    except Exception as e:
        print(f"[API] GraphQL kivétel: {e}")

    print("[API] Váltás böngészős felderítésre...")
    games = _fetch_via_browser()
    print(f"[API] Felderítés kész. Összesen talált cím: {len(games)}")
    return games