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
        print(f"❌ Network error while fetching {url}: {e}")
        return None


def parse_accommodations(html_content, target_department=None):
    """
    Parses every accommodation card on the page using modern DSFR selectors.
    """
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, "html.parser")
    cards = soup.find_all("div", class_="fr-card")
    accommodations = []

    for card in cards:
        # 1. Scrape Title and Link
        title_tag = card.select_one("h3.fr-card__title a")
        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        rel_link = title_tag.get("href", "").strip()
        link = f"{BASE_URL}{rel_link}" if rel_link.startswith("/") else rel_link

        # 2. Extract Accommodation ID
        id_match = re.search(r"/accommodations/(\d+)", link)
        acc_id = id_match.group(1) if id_match else link

        # 3. Scrape Address & Postal Code
        desc_tag = card.select_one("p.fr-card__desc")
        address = desc_tag.get_text(strip=True) if desc_tag else "N/A"

        postal_code_match = re.search(r"\b\d{5}\b", address)
        postal_code = postal_code_match.group(0) if postal_code_match else ""

        # 4. Scrape Price
        badge_tag = card.select_one("ul.fr-badges-group p.fr-badge")
        price = badge_tag.get_text(strip=True) if badge_tag else "Non spécifié"

        # 5. Department Matching (e.g., '63', '20')
        matches_dept = False
        if target_department and postal_code:
            matches_dept = postal_code.startswith(str(target_department))

        accommodations.append({
            "id": str(acc_id),
            "title": title,
            "address": address,
            "price": price,
            "postal_code": postal_code,
            "link": link,
            "matches_dept": matches_dept,
        })

    return accommodations


def get_available_rooms(tool_id=47, target_department=None, max_pages=3):
    """
    Main scraping function required by bot.py and notifier.py.
    Fetches all available accommodations across multiple pages.
    """
    all_rooms = []
    seen_ids = set()

    for page in range(1, max_pages + 1):
        html = fetch_page(tool_id=tool_id, page=page)
        if not html:
            break

        rooms = parse_accommodations(html, target_department=target_department)
        if not rooms:
            break

        for room in rooms:
            if room["id"] not in seen_ids:
                seen_ids.add(room["id"])
                all_rooms.append(room)

    return all_rooms
