import httpx
import asyncio
from bs4 import BeautifulSoup

BASE_URL = "https://trouverunlogement.lescrous.fr"
SEARCH_URL = f"{BASE_URL}/tools/47/search"


async def get_available_rooms():
    rooms = []
    seen = set()
    page = 1

    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        while True:
            url = f"{SEARCH_URL}?page={page}"
            
            try:
                response = await client.get(url)
                response.raise_for_status()
            except Exception as e:
                print(f"Error fetching page {page}: {e}")
                break

            soup = BeautifulSoup(response.text, "html.parser")
            
            # --- NEW METHOD: Find all accommodation cards first ---
            cards = soup.select('.fr-card')

            # If no cards are found, we reached the last page
            if not cards:
                break

            new_rooms_on_page = False

            for card in cards:
                # 1. Find the link inside the card
                link = card.select_one('a[href*="/accommodations/"]')
                if not link:
                    continue

                href = link.get("href")
                if not href or href in seen:
                    continue

                new_rooms_on_page = True
                seen.add(href)

                # 2. Extract Title
                title = link.get_text(strip=True)
                
                # 3. Extract Location (City / Address)
                desc_elem = card.select_one('.fr-card__desc')
                location = desc_elem.get_text(strip=True) if desc_elem else "Lieu inconnu"

                # 4. Extract Price (Using p.fr-badge to avoid clicking the heart button)
                price_elem = card.select_one('p.fr-badge')
                price = price_elem.get_text(strip=True) if price_elem else "Prix inconnu"

                # Save room
                rooms.append({
                    "title": title,
                    "location": location,
                    "price": price,
                    "url": BASE_URL + href,
                })

            if not new_rooms_on_page:
                break

            page += 1
            await asyncio.sleep(1)

    return rooms