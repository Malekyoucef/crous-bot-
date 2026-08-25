import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
}

def fetch_crous_accommodations(tool_id=47, page=1):
    """
    Fetches the HTML of the Crous search results page.
    """
    url = f"https://trouverunlogement.lescrous.fr/tools/{tool_id}/search?page={page}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error while fetching {url}: {e}")
        return None

def parse_accommodations(html_content, target_department=None):
    """
    Parses all accommodation cards from the page HTML.
    """
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, "html.parser")
    cards = soup.find_all("div", class_="fr-card")
    accommodations = []

    for card in cards:
        # 1. Title & Link
        title_el = card.select_one("h3.fr-card__title a")
        if not title_el:
            continue

        title = title_el.get_text(strip=True)
        rel_link = title_el.get("href", "").strip()
        link = f"https://trouverunlogement.lescrous.fr{rel_link}" if rel_link.startswith("/") else rel_link

        # 2. Address
        desc_el = card.select_one("p.fr-card__desc")
        address = desc_el.get_text(strip=True) if desc_el else "Adresse non spécifiée"

        # 3. Price
        badge_el = card.select_one("ul.fr-badges-group p.fr-badge")
        price = badge_el.get_text(strip=True) if badge_el else "Prix non indiqué"

        # 4. Department / Postal code detection
        postal_code_match = re.search(r"\b\d{5}\b", address)
        postal_code = postal_code_match.group(0) if postal_code_match else None

        # Check if it matches the target department (e.g., '63', '20')
        matches_dept = False
        if target_department and postal_code:
            matches_dept = postal_code.startswith(str(target_department))

        accommodations.append({
            "title": title,
            "address": address,
            "price": price,
            "postal_code": postal_code,
            "link": link,
            "matches_dept": matches_dept,
        })

    return accommodations

def format_telegram_message(item, target_dept):
    """
    Formats the accommodation dictionary into your bot's notification message.
    """
    status_icon = "✅ Matches department" if item["matches_dept"] else "⚠️ Not in"
    dept_label = f"{item['postal_code']}" if item["matches_dept"] else f"{target_dept}"

    message = (
        f"🟢 NEW CROUS ACCOMMODATION!\n\n"
        f"🏢 {item['title']}\n"
        f"📍 {item['address']}\n"
        f"💶 {item['price']}\n"
        f"{status_icon}: {dept_label}\n\n"
        f"🔗 {item['link']}"
    )
    return message

# ================================
# Example usage / Test run
# ================================
if __name__ == "__main__":
    TARGET_DEPT = "63"  # Change to your target department (e.g., '63', '20', etc.)

    print("Fetching Crous accommodations...")
    html = fetch_crous_accommodations(tool_id=47, page=1)
    results = parse_accommodations(html, target_department=TARGET_DEPT)

    print(f"Found {len(results)} accommodations on page 1.\n")
    
    for item in results:
        # If you only want to send notifications for matching departments:
        # if item["matches_dept"]:
        print(format_telegram_message(item, TARGET_DEPT))
        print("-" * 50)
