"""
scrapers/base.py  — improved headers, retries, robust price parsing
"""
import aiohttp
import asyncio
import random
import re
from abc import ABC, abstractmethod

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
]

BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-IN,en-GB;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "max-age=0",
    "DNT": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Connection": "keep-alive",
}


class BaseScraper(ABC):
    site_name: str = ""
    base_url: str = ""
    timeout: int = 15

    def _headers(self):
        return {
            **BASE_HEADERS,
            "User-Agent": random.choice(USER_AGENTS),
        }

    async def fetch_html(self, url: str, session: aiohttp.ClientSession, retries: int = 2) -> str | None:
        for attempt in range(retries + 1):
            try:
                if attempt > 0:
                    await asyncio.sleep(1.5 * attempt)
                async with session.get(
                    url, headers=self._headers(),
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    ssl=False, allow_redirects=True,
                ) as resp:
                    if resp.status == 200:
                        return await resp.text(errors="replace")
                    elif resp.status in (403, 429, 503):
                        print(f"[{self.site_name}] HTTP {resp.status}, attempt {attempt+1}")
                    else:
                        return None
            except asyncio.TimeoutError:
                print(f"[{self.site_name}] timeout attempt {attempt+1}")
            except Exception as e:
                print(f"[{self.site_name}] error: {e}")
        return None

    def parse_price(self, raw: str) -> float:
        if not raw:
            return 0.0
        cleaned = re.sub(r'[₹\u20b9,\s]', '', str(raw))
        m = re.search(r'\d+(?:\.\d+)?', cleaned)
        if m:
            try:
                return float(m.group())
            except ValueError:
                pass
        return 0.0

    @abstractmethod
    async def search(self, query: str, session: aiohttp.ClientSession) -> list[dict]: ...

    @abstractmethod
    async def scrape_product(self, url: str, session: aiohttp.ClientSession) -> dict: ...

    def _result(self, **kwargs) -> dict:
        return {
            "site": self.site_name,
            "title": kwargs.get("title", ""),
            "price": kwargs.get("price", 0),
            "original_price": kwargs.get("original_price", 0),
            "rating": kwargs.get("rating", 0),
            "reviews": kwargs.get("reviews", ""),
            "link": kwargs.get("link", ""),
            "delivery": kwargs.get("delivery", ""),
            "delivery_date": kwargs.get("delivery_date", ""),
            "image": kwargs.get("image", ""),
            "search_title": kwargs.get("search_title", kwargs.get("title", "")),
            "in_stock": kwargs.get("in_stock", True),
            "is_mock": kwargs.get("is_mock", False),
        }
