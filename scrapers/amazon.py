"""
scrapers/amazon.py — Amazon.in with updated selectors + SerpAPI fallback hint
"""
import re
import aiohttp
from bs4 import BeautifulSoup
from .base import BaseScraper


class AmazonScraper(BaseScraper):
    site_name = "Amazon"
    base_url = "https://www.amazon.in"

    def _headers(self):
        h = super()._headers()
        h["Referer"] = "https://www.amazon.in/"
        h["Host"] = "www.amazon.in"
        return h

    async def search(self, query: str, session: aiohttp.ClientSession) -> list[dict]:
        url = f"{self.base_url}/s?k={query.replace(' ', '+')}&i=electronics&ref=nb_sb_noss"
        html = await self.fetch_html(url, session)
        if not html:
            return self._mock_search(query)

        soup = BeautifulSoup(html, "lxml")
        results = []

        for item in soup.select("[data-component-type='s-search-result']")[:5]:
            title_el  = item.select_one("h2 a span")
            # Amazon 2024 price selectors
            price_whole = item.select_one(".a-price-whole")
            price_frac  = item.select_one(".a-price-fraction")
            price_el    = item.select_one(".a-price .a-offscreen")
            orig_el     = item.select_one(".a-price.a-text-price .a-offscreen")
            rating_el   = item.select_one(".a-icon-alt")
            review_el   = item.select_one(".a-size-base.s-underline-text")
            link_el     = item.select_one("h2 a")
            img_el      = item.select_one("img.s-image")

            if not title_el:
                continue

            # Build price from whole + fraction if offscreen not found
            if price_whole:
                whole = price_whole.text.strip().replace(",", "").replace(".", "")
                frac  = price_frac.text.strip() if price_frac else "00"
                try:
                    price = float(f"{whole}.{frac}")
                except ValueError:
                    price = self.parse_price(price_el.text) if price_el else 0
            elif price_el:
                price = self.parse_price(price_el.text)
            else:
                continue  # skip if no price

            orig = self.parse_price(orig_el.text) if orig_el else price
            rating_text = rating_el.text if rating_el else ""
            rating_match = re.search(r"[\d.]+", rating_text)
            rating = float(rating_match.group()) if rating_match else 0

            href = self.base_url + link_el["href"] if link_el else self.base_url
            # Clean affiliate/tracking params for cleaner URL
            href = re.sub(r'/ref=[^?]*', '', href)

            results.append(self._result(
                title=title_el.text.strip(),
                price=price,
                original_price=orig,
                rating=rating,
                reviews=review_el.text.strip() if review_el else "",
                link=href,
                image=img_el["src"] if img_el else "",
                delivery="Free",
                delivery_date="Tomorrow",
            ))

        return results if results else self._mock_search(query)

    async def scrape_product(self, url: str, session: aiohttp.ClientSession) -> dict:
        html = await self.fetch_html(url, session)
        if not html:
            return self._mock_product(url)

        soup = BeautifulSoup(html, "lxml")

        title_el    = soup.select_one("#productTitle")
        # Multiple price selector attempts for Amazon's varied layouts
        price_el    = (
            soup.select_one(".priceToPay .a-offscreen") or
            soup.select_one(".a-price.priceToPay .a-offscreen") or
            soup.select_one("#priceblock_ourprice") or
            soup.select_one("#priceblock_dealprice") or
            soup.select_one(".a-price .a-offscreen")
        )
        orig_el     = soup.select_one(".a-text-price .a-offscreen")
        rating_el   = soup.select_one("#acrPopover .a-size-base.a-color-base")
        review_el   = soup.select_one("#acrCustomerReviewText")
        img_el      = soup.select_one("#landingImage, #imgBlkFront")
        delivery_el = soup.select_one("#deliveryBlockMessage .a-color-base, #mir-layout-DELIVERY_BLOCK")

        title = title_el.text.strip() if title_el else ""
        price = self.parse_price(price_el.text) if price_el else 0
        orig  = self.parse_price(orig_el.text) if orig_el else price

        return self._result(
            title=title,
            price=price,
            original_price=orig,
            rating=float(rating_el.text.strip()) if rating_el else 0,
            reviews=review_el.text.strip() if review_el else "",
            link=url,
            image=img_el.get("data-old-hires") or img_el.get("src", "") if img_el else "",
            delivery="Free",
            delivery_date=delivery_el.text.strip()[:30] if delivery_el else "Tomorrow",
            search_title=self._distill_title(title),
        )

    def _distill_title(self, full_title: str) -> str:
        words = full_title.split()[:7]
        return " ".join(words)

    def _mock_search(self, query: str) -> list[dict]:
        return [self._result(
            title=f"{query} — Amazon.in",
            price=0, original_price=0,
            rating=4.5, reviews="",
            link=f"https://www.amazon.in/s?k={query.replace(' ', '+')}",
            delivery="Free", delivery_date="Tomorrow",
            is_mock=True,
        )]

    def _mock_product(self, url: str) -> dict:
        return self._result(
            title="", price=0, original_price=0,
            link=url, is_mock=True,
            search_title="",
        )
