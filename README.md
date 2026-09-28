# SmartPrice — Real-Time Price Comparison

Compare product prices across **Amazon**, **Flipkart**, **Meesho**, and **Croma** in one place.

## Features
- 🔍 **Keyword search** — search any product and compare across all stores
- 🔗 **Link compare** — paste any product URL and find better prices elsewhere
- 👑 **Best price winner** — highlighted at the top with one-click buy
- 📊 **Price chart** — visual bar comparison across all stores
- 💚 **Buy Now buttons** — open the exact product page on each store
- 🤍 **Save products** — bookmark items for later (stored in browser)
- ⚡ **15-min cache** — results cached to avoid repeated scraping

## Setup

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python app.py
```

Open http://localhost:5000 in your browser.

## Notes on Scraping

E-commerce sites (especially Amazon) actively block bots. When scraping fails, the app shows the store's search page link so you can check manually.

For production use, consider:
- **ScraperAPI** or **Bright Data** proxy rotation
- **Playwright** with stealth plugin for JS-heavy pages  
- Official affiliate APIs where available

## Project Structure

```
smartprice/
├── app.py                  # Flask routes
├── requirements.txt
├── scrapers/
│   ├── base.py             # Base scraper (headers, fetch, price parse)
│   ├── amazon.py           # Amazon.in scraper
│   ├── flipkart.py         # Flipkart scraper
│   ├── meesho.py           # Meesho (API + fallback)
│   ├── croma.py            # Croma scraper
│   ├── dispatcher.py       # Async parallel orchestrator
│   └── link_parser.py      # URL → site + product ID
├── cache/
│   └── price_cache.py      # In-memory TTL cache
├── static/
│   ├── css/style.css
│   └── js/app.js
└── templates/
    └── index.html
```
