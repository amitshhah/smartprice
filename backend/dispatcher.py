"""
backend/dispatcher.py — parallel async scraping with improved error handling
"""

import asyncio
import aiohttp

from scrapers.amazon import AmazonScraper
from scrapers.flipkart import FlipkartScraper
from scrapers.meesho import MeeshoScraper
from scrapers.croma import CromaScraper


SCRAPERS = [AmazonScraper(), FlipkartScraper(), MeeshoScraper(), CromaScraper()]

SITE_SCRAPER_MAP = {
    "Amazon": AmazonScraper(),
    "Flipkart": FlipkartScraper(),
    "Meesho": MeeshoScraper(),
    "Croma": CromaScraper(),
}


class ProductDispatcher:

    async def search_all(self, query: str, exclude_site: str = None) -> list[dict]:

        scrapers = [s for s in SCRAPERS if s.site_name != exclude_site]

        connector = aiohttp.TCPConnector(limit=10, ssl=False, force_close=True)
        timeout = aiohttp.ClientTimeout(total=20)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = [self._safe_search(s, query, session) for s in scrapers]
            nested = await asyncio.gather(*tasks)

        flat = []

        for results in nested:
            if isinstance(results, list):
                flat.extend(results)

        return flat


    async def _safe_search(self, scraper, query: str, session) -> list[dict]:

        try:
            return await scraper.search(query, session)

        except Exception as e:
            print(f"[{scraper.site_name}] search_all error: {e}")
            return scraper._mock_search(query)


    async def scrape_product_page(self, url: str, site: str) -> dict:

        scraper = SITE_SCRAPER_MAP.get(site)

        if not scraper:
            return {}

        connector = aiohttp.TCPConnector(ssl=False, force_close=True)

        async with aiohttp.ClientSession(connector=connector) as session:

            try:
                return await scraper.scrape_product(url, session)

            except Exception as e:
                print(f"[{site}] scrape_product error: {e}")
                return {}