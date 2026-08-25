import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
}

BASE_URL = "https://trouverunlogement.lescrous.fr"


def fetch_page(tool_id=47, page=1):
    """Fetches the search results HTML page from Crous."""
    url = f"{BASE_URL}/tools/{tool_id}/search?page={page}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=12)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"❌ Error fetching Crous page: {e}")
        return None


def parse_page(html_content):
    """
    Parses each accommodation card using the modern DSFR HTML classes.
    """
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, "html.parser")
    cards = soup.find_all("div", class_="fr-card")
    rooms = []

    for card in cards:
        # --- 1. Scrape Title and Link ---
        title_el = card.select_one("h3.fr-card__title a")
        if not title_el:
            continue

        title = title_el.get_text(strip=True)
        rel_link = title_el.get("href", "").strip()
        link = f"{BASE_URL}{rel_link}" if rel_link.startswith("/") else rel_link

        # Extract numerical accommodation ID from link (e.g. 1521)
        id_match = re.search(r"/accommodations/(\d+)", link)
        room_id = id_match.group(1) if id_match else link

        # --- 2. Scrape Address & Postal Code ---
        desc_el = card.select_one("p.fr-card__desc")
        address = desc_el.get_text(strip=True) if desc_el else "N/A"

        postal_code_match = re.search(r"\b\d{5}\b", address)
        postal_code = postal_code_match.group(0) if postal_code_match else ""

        # --- 3. Scrape Price ---
        badge_el = card.select_one("ul.fr-badges-group p.fr-badge")
        price = badge_el.get_text(strip=True) if badge_el else "N/A"

        rooms.append({
            "id": str(room_id),
            "title": title,
            "address": address,
            "price": price,
            "postal_code": postal_code,
            "link": link,
            "url": link,  # Provided as fallback for bots using room['url']
        })

    return rooms


def get_available_rooms(tool_id=47, max_pages=3):
    """
    Main function called by bot.py / notifier.py.
    Scrapes multiple pages and deduplicates the results.
    """
    all_rooms = []
    seen_ids = set()

    for page in range(1, max_pages + 1):
        html = fetch_page(tool_id=tool_id, page=page)
        if not html:
            break

        rooms = parse_page(html)
        if not rooms:
            break

        for room in rooms:
            if room["id"] not in seen_ids:
                seen_ids.add(room["id"])
                all_rooms.append(room)

    return all_rooms


# Fallback alias in case other files import under alternative names
scrape_rooms = get_available_rooms
get_rooms = get_available_rooms
