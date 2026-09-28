"""
scrapers/croma.py — updated selectors
"""
import re
import aiohttp
from bs4 import BeautifulSoup
from .base import BaseScraper


class CromaScraper(BaseScraper):
    site_name = "Croma"
    base_url = "https://www.croma.com"

    def _headers(self):
        h = super()._headers()
        h["Referer"] = "https://www.croma.com/"
        return h

    async def search(self, query: str, session: aiohttp.ClientSession) -> list[dict]:
        url = f"{self.base_url}/searchresults?q={query.replace(' ', '%20')}&prefn1=inStockFlag&prefv1=true"
        html = await self.fetch_html(url, session)
        if not html:
            return self._mock_search(query)

        soup = BeautifulSoup(html, "lxml")
        results = []

        # Croma 2024 selectors
        CARD_SELS  = ["li.product-item", "div.product-item", "div.cp-product"]
        TITLE_SELS = ["a.product-title", "h3.product-title", "p.product-title", "h4.cp-title"]
        PRICE_SELS = ["span.amount", "span.cp-price", "div.amount", "p.amount"]
        LINK_SELS  = ["a.product-title-link", "a.product-image-wrapper", "a.pdpLink"]
        IMG_SELS   = ["img.product-img", "img.cp-img", "img.lozad"]

        cards = []
        for cs in CARD_SELS:
            cards = soup.select(cs)
            if cards:
                break

        for card in cards[:5]:
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

            price = self.parse_price(price_el.text)
            if not price:
                continue

            link_el = next((card.select_one(s) for s in LINK_SELS if card.select_one(s)), None)
            img_el  = next((card.select_one(s) for s in IMG_SELS  if card.select_one(s)), None)

            href = link_el.get("href", "") if link_el else ""
            if href and not href.startswith("http"):
                href = self.base_url + href

            img_src = ""
            if img_el:
                img_src = img_el.get("data-src") or img_el.get("src") or ""

            results.append(self._result(
                title=title_el.text.strip(),
                price=price,
                original_price=price,
                rating=4.2,
                link=href or f"https://www.croma.com/search/?q={query.replace(' ', '%20')}",
                image=img_src,
                delivery="Free",
                delivery_date="Today",
            ))

        return results if results else self._mock_search(query)

    async def scrape_product(self, url: str, session: aiohttp.ClientSession) -> dict:
        html = await self.fetch_html(url, session)
        if not html:
            return self._mock_product(url)

        soup = BeautifulSoup(html, "lxml")
        title_el = soup.select_one("h1.pdp-title, h1.cp-title, h1.product-name")
        price_el = soup.select_one("span.amount, span.cp-price, div.pdp-price span")
        img_el   = soup.select_one("div.pdp-main-img img, div.cp-main-img img")

        title = title_el.text.strip() if title_el else ""
        price = self.parse_price(price_el.text) if price_el else 0

        return self._result(
            title=title, price=price, original_price=price,
            rating=4.2, link=url,
            image=img_el.get("src", "") if img_el else "",
            delivery="Free", delivery_date="Today",
            search_title=" ".join(title.split()[:7]),
        )

    def _mock_search(self, query: str) -> list[dict]:
        return [self._result(
            title=f"{query} — Croma",
            price=0, original_price=0,
            rating=4.2,
            link=f"https://www.croma.com/search/?q={query.replace(' ', '%20')}",
            delivery="Free", delivery_date="Today",
            is_mock=True,
        )]

    def _mock_product(self, url: str) -> dict:
        return self._result(title="", price=0, link=url, is_mock=True, search_title="")
