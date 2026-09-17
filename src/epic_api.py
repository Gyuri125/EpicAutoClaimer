import requests

def fetch_free_games():
    url = "https://store-site-backend-static.akamaized.net/freeGamesPromotions?locale=hu-HU&country=HU&allowCountries=HU"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        elements = data["data"]["Catalog"]["searchStore"]["elements"]
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
        print(f"[API Error] Nem sikerult lekerdezni a jatekokat: {e}")
        return []