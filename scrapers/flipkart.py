"""
scrapers/flipkart.py — updated selectors for 2024/2025 Flipkart HTML
"""
import re
import aiohttp
from bs4 import BeautifulSoup
from .base import BaseScraper


class FlipkartScraper(BaseScraper):
    site_name = "Flipkart"
    base_url = "https://www.flipkart.com"

    def _headers(self):
        h = super()._headers()
        h["Referer"] = "https://www.flipkart.com/"
        h["Host"] = "www.flipkart.com"
        return h

    async def search(self, query: str, session: aiohttp.ClientSession) -> list[dict]:
        url = f"{self.base_url}/search?q={query.replace(' ', '+')}&otracker=search&marketplace=FLIPKART"
        html = await self.fetch_html(url, session)
        if not html:
            return self._mock_search(query)

        soup = BeautifulSoup(html, "lxml")
        results = []

        # Flipkart 2024 uses multiple layout variants
        # Try all known card selectors
        cards = (
            soup.select("div._75nlfW") or        # grid layout 2024
            soup.select("div._1AtVbE > div") or  # old grid
            soup.select("div[data-id]") or
            soup.select("div._2kHMtA")
        )

        TITLE_SELS = ["div._4rR01T", "a.s1Q9rs", "div.KzDlHZ", "div._2WkVRV", "a._2rpwqI span"]
        PRICE_SELS = ["div._30jeq3", "div.Nx9bqj", "div._25b18c ._30jeq3"]
        ORIG_SELS  = ["div._3I9_wc", "div.yRaY8j", "div._3auQ3N"]
        LINK_SELS  = ["a._1fQZEK", "a.s1Q9rs", "a._2rpwqI", "a.CGtC98"]
        IMG_SELS   = ["img._396cs4", "img.DByuf4", "img._2r_T1I"]
        RATE_SELS  = ["div._3LWZlK", "div.XQDdHH"]

        for card in cards[:6]:
            title_el = None
            for sel in TITLE_SELS:
                title_el = card.select_one(sel)
                if title_el:
                    break
            price_el = None
            for sel in PRICE_SELS:
                price_el = card.select_one(sel)
                if price_el:
                    break
            if not (title_el and price_el):
                continue

            orig_el   = next((card.select_one(s) for s in ORIG_SELS if card.select_one(s)), None)
            link_el   = next((card.select_one(s) for s in LINK_SELS if card.select_one(s)), None)
            img_el    = next((card.select_one(s) for s in IMG_SELS  if card.select_one(s)), None)
            rating_el = next((card.select_one(s) for s in RATE_SELS if card.select_one(s)), None)

            price = self.parse_price(price_el.text)
            if not price:
                continue

            orig = self.parse_price(orig_el.text) if orig_el else price
            href = link_el["href"] if link_el else ""
            if href and not href.startswith("http"):
                href = self.base_url + href
            # Remove tracking
            href = re.sub(r'\?.*$', '', href) if href else href

            try:
                rating = float(rating_el.text.strip()) if rating_el else 0
            except (ValueError, AttributeError):
                rating = 0

            results.append(self._result(
                title=title_el.text.strip(),
                price=price,
                original_price=orig,
                rating=rating,
                link=href or f"https://www.flipkart.com/search?q={query.replace(' ', '+')}",
                image=img_el.get("src") if img_el else "",
                delivery="Free",
                delivery_date="In 2 days",
            ))

        return results if results else self._mock_search(query)

    async def scrape_product(self, url: str, session: aiohttp.ClientSession) -> dict:
        html = await self.fetch_html(url, session)
        if not html:
            return self._mock_product(url)

        soup = BeautifulSoup(html, "lxml")

        title_el  = soup.select_one("span.B_NuCI, h1._9E25nV, h1.yhB1nd")
        price_el  = soup.select_one("div._30jeq3._16Jk6d, div.Nx9bqj.CxhGGd, div._16Jk6d")
        orig_el   = soup.select_one("div._3I9_wc._2p6lqe, div.yRaY8j")
        rating_el = soup.select_one("div._3LWZlK._32lA32, div.XQDdHH")
        img_el    = soup.select_one("img._396cs4._3exPp9, img.DByuf4")

        title = title_el.text.strip() if title_el else ""
        price = self.parse_price(price_el.text) if price_el else 0
        orig  = self.parse_price(orig_el.text)  if orig_el  else price

        return self._result(
            title=title, price=price, original_price=orig,
            rating=float(rating_el.text.strip()) if rating_el else 0,
            link=url,
            image=img_el.get("src", "") if img_el else "",
            delivery="Free", delivery_date="In 2 days",
            search_title=" ".join(title.split()[:7]),
        )

    def _mock_search(self, query: str) -> list[dict]:
        return [self._result(
            title=f"{query} — Flipkart",
            price=0, original_price=0,
            rating=4.4, reviews="",
            link=f"https://www.flipkart.com/search?q={query.replace(' ', '+')}",
            delivery="Free", delivery_date="In 2 days",
            is_mock=True,
        )]

    def _mock_product(self, url: str) -> dict:
        return self._result(title="", price=0, link=url, is_mock=True, search_title="")
