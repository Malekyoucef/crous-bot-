import json
import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
}

BASE_URL = "https://trouverunlogement.lescrous.fr"

def get_available_rooms(tool_id=47, target_department="63", max_pages=3):
    print("🔍 [Scraper] Fetching rooms from Crous...")
    all_rooms = []
    seen_ids = set()

    for page in range(1, max_pages + 1):
        url = f"{BASE_URL}/tools/{tool_id}/search?page={page}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                print(f"⚠️ [Scraper] Error {resp.status_code} fetching page {page}")
                break
                
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # The most reliable method: Extract the JSON embedded directly by the website
            script_tag = soup.find('script', attrs={'data-url': lambda u: u and '/api/fr/search/' in u})
            
            if not script_tag or not script_tag.string:
                print(f"⚠️ [Scraper] No JSON data found on page {page}. (End of results or blocked)")
                break
                
            data = json.loads(script_tag.string)
            body = json.loads(data['body'])
            items = body.get('results', {}).get('items', [])
            
            if not items:
                print(f"✅ [Scraper] Page {page} is empty. Stopping pagination.")
                break
                
            for item in items:
                room_id = str(item.get('id'))
                if room_id in seen_ids:
                    continue
                seen_ids.add(room_id)
                
                # Extract clean Title and Address
                residence = item.get('residence', {})
                title = residence.get('label', 'Logement inconnu').strip()
                address = residence.get('address', 'Adresse inconnue').strip()
                
                # Postal code extraction for your department filter
                postal_code_match = re.search(r"\b\d{5}\b", address)
                postal_code = postal_code_match.group(0) if postal_code_match else ""
                
                matches_dept = False
                if target_department and postal_code:
                    matches_dept = postal_code.startswith(str(target_department))

                # Price extraction (Crous JSON stores prices in cents, e.g. 23700 = 237.00€)
                price_str = "Prix non indiqué"
                modes = item.get('occupationModes', [])
                if modes:
                    rents = [m['rent']['min'] for m in modes if 'rent' in m and 'min' in m['rent']]
                    if rents:
                        price_str = f"{min(rents) / 100:.2f} €".replace('.', ',')

                link = f"{BASE_URL}/tools/{tool_id}/accommodations/{room_id}"
                
                # We include multiple keys to ensure compatibility with your bot's other files
                room_data = {
                    "id": room_id,
                    "title": title,
                    "name": title,          # Fallback if bot uses item['name']
                    "address": address,
                    "location": address,    # Fallback if bot uses item['location']
                    "price": price_str,
                    "postal_code": postal_code,
                    "matches_dept": matches_dept,
                    "link": link,
                    "url": link             # Fallback if bot uses item['url']
                }
                all_rooms.append(room_data)
                
            print(f"✅ [Scraper] Page {page}: Extracted {len(items)} rooms.")
            
        except Exception as e:
            print(f"❌ [Scraper] Exception on page {page}: {e}")
            break

    print(f"🎉 [Scraper] Total unique rooms extracted: {len(all_rooms)}")
    return all_rooms

# Aliases just in case your main.py uses a different import name
scrape_rooms = get_available_rooms
get_rooms = get_available_rooms

# Optional: You can test this file directly by running `python scraper.py`
if __name__ == "__main__":
    rooms = get_available_rooms(max_pages=1)
    if rooms:
        print("\nTest Output of the first room:")
        print(json.dumps(rooms[0], indent=4, ensure_ascii=False))
