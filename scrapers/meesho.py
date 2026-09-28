"""
scrapers/meesho.py — uses Meesho's public search API (JSON)
"""
import aiohttp
import json
from .base import BaseScraper


class MeeshoScraper(BaseScraper):
    site_name = "Meesho"
    base_url = "https://www.meesho.com"

    def _headers(self):
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-IN,en;q=0.9",
            "Origin": "https://www.meesho.com",
            "Referer": "https://www.meesho.com/",
        }

    async def search(self, query: str, session: aiohttp.ClientSession) -> list[dict]:
        # Meesho catalog search API
        api_url = "https://www.meesho.com/api/v1/products/search"
        params = {
            "q": query,
            "num_results": 5,
        }
        try:
            async with session.get(
                api_url, params=params, headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=12), ssl=False,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    items = data.get("products") or data.get("data", {}).get("products", [])
                    results = []
                    for item in items[:4]:
                        try:
                            price = float(item.get("min_price") or item.get("price") or 0)
                            orig  = float(item.get("mrp") or item.get("original_price") or price)
                            pid   = item.get("product_id") or item.get("id") or ""
                            slug  = item.get("slug") or item.get("name", query).lower().replace(" ", "-")
                            link  = f"https://www.meesho.com/{slug}/p/{pid}" if pid else f"https://www.meesho.com/search?q={query.replace(' ', '+')}"
                            img   = item.get("cover_image", {}).get("url") or item.get("image_url") or ""
                            if not img and item.get("images"):
                                img = item["images"][0].get("url", "")
                            results.append(self._result(
                                title=item.get("name", f"{query} — Meesho"),
                                price=price,
                                original_price=orig,
                                rating=float(item.get("rating") or 4.0),
                                reviews=str(item.get("review_count") or ""),
                                link=link,
                                image=img,
                                delivery="₹49",
                                delivery_date="In 4–5 days",
                            ))
                        except Exception:
                            continue
                    if results:
                        return results
        except Exception as e:
            print(f"[Meesho] API error: {e}")

        return self._mock_search(query)

    async def scrape_product(self, url: str, session: aiohttp.ClientSession) -> dict:
        return self._mock_product(url)

    def _mock_search(self, query: str) -> list[dict]:
        return [self._result(
            title=f"{query} — Meesho",
            price=0, original_price=0,
            rating=4.0,
            link=f"https://www.meesho.com/search?q={query.replace(' ', '+')}",
            delivery="₹49", delivery_date="In 4–5 days",
            is_mock=True,
        )]

    def _mock_product(self, url: str) -> dict:
        return self._result(title="", price=0, link=url, is_mock=True, search_title="")
