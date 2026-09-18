import os
import re
import time
import requests
import logging
from playwright.sync_api import sync_playwright

logger = logging.getLogger("EpicAPI")

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
          pageType
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
}


def _extract_valid_slug(item):
    """Kiválasztja a működő bolti slugot, eldobva a 32 jegyű belső kódokat."""
    # 1. Elsődleges: offerMappings (ez a valódi bolti URL azonosító)
    for mapping in item.get("offerMappings", []):
        page_slug = mapping.get("pageSlug")
        if page_slug:
            return page_slug

    # 2. Ha nincs mapping, megnézzük a productSlug-ot (ha nem 32 karakteres hash)
    prod_slug = item.get("productSlug")
    if prod_slug:
        prod_slug = prod_slug.removesuffix("/home")
        if not re.match(r"^[0-9a-fA-F]{32}$", prod_slug):
            return prod_slug

    # 3. urlSlug (szintén szűrve)
    url_slug = item.get("urlSlug")
    if url_slug and not re.match(r"^[0-9a-fA-F]{32}$", url_slug):
        return url_slug

    return prod_slug or url_slug


def _fetch_via_graphql():
    """Játékok lekérése közvetlenül a GraphQL végpontról."""
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
                slug = _extract_valid_slug(item)
                if slug:
                    title = item.get("title", "Ismeretlen játék")
                    active_games.append({
                        "title": title,
                        "slug": slug,
                        "url": f"https://store.epicgames.com/hu/p/{slug}"
                    })
    return active_games


def _fetch_via_browser():
    """Tartalék felderítés böngészővel, ha a GraphQL blokkolva lenne."""
    print("[API: Böngésző] Tartalék felderítés indítása Chrome-mal...")
    games = []
    cache_dir = os.path.abspath("./profiles/.cache_browser")

    with sync_playwright() as p:
        try:
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
            time.sleep(5)

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
    """Elsődlegesen a GraphQL API-t használja, hiba esetén vált böngészős felderítésre."""
    try:
        games = _fetch_via_graphql()
        if games:
            # Duplikációk szűrése
            seen = set()
            unique_games = []
            for g in games:
                if g["slug"] not in seen:
                    seen.add(g["slug"])
                    unique_games.append(g)

            print(f"[API] Sikeres lekérdezés GraphQL-ből! Érvényes címek ({len(unique_games)} db): {[g['title'] for g in unique_games]}")
            return unique_games
    except Exception as e:
        print(f"[API] GraphQL kivétel: {e}")

    print("[API] Váltás böngészős felderítésre...")
    games = _fetch_via_browser()
    print(f"[API] Felderítés kész. Összesen talált cím: {len(games)}")
    return games