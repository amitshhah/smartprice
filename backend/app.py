"""
SmartPrice — Flask Application Entry Point (improved)
"""
import asyncio
import json
import time
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS


from backend.dispatcher import ProductDispatcher
from backend.link_parser import parse_product_link
from backend.cache.price_cache import PriceCache

app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static"
)
CORS(app)

cache = PriceCache(ttl_minutes=15)
dispatcher = ProductDispatcher()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/search", methods=["POST"])
def search_by_keyword():
    data  = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"error": "Query is required"}), 400

    cache_key = f"search:{query.lower()}"
    cached = cache.get(cache_key)
    if cached:
        return jsonify({**cached, "cached": True})

    start   = time.time()
    results = asyncio.run(dispatcher.search_all(query))
    elapsed = round(time.time() - start, 2)

    response = _build_response(results, elapsed, query=query)
    cache.set(cache_key, response)
    return jsonify(response)


@app.route("/api/compare-link", methods=["POST"])
def compare_by_link():
    data = request.get_json(silent=True) or {}
    url  = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "URL is required"}), 400

    parsed = parse_product_link(url)
    if not parsed:
        return jsonify({"error": "Unsupported URL. Please paste a link from Amazon, Flipkart, Meesho, or Croma."}), 422

    cache_key = f"link:{url}"
    cached = cache.get(cache_key)
    if cached:
        return jsonify({**cached, "cached": True})

    start = time.time()
    source_result = asyncio.run(dispatcher.scrape_product_page(url, parsed["site"]))
    search_query  = source_result.get("search_title") or parsed.get("query_hint", "")
    all_results   = asyncio.run(dispatcher.search_all(search_query))

    if source_result.get("title") and source_result.get("price", 0) > 0:
        all_results = [r for r in all_results if r["site"].lower() != parsed["site"].lower()]
        all_results.insert(0, source_result)

    elapsed  = round(time.time() - start, 2)
    response = _build_response(
        all_results, elapsed,
        query=search_query,
        source_url=url,
        source_site=parsed["site"],
    )
    cache.set(cache_key, response)
    return jsonify(response)


@app.route("/api/price-history/<path:product_id>", methods=["GET"])
def price_history(product_id):
    history = cache.get_history(product_id)
    return jsonify({"history": history or []})


# ── helpers ────────────────────────────────────────────────────────────────

def _build_response(results, elapsed, **meta):
    if not results:
        return {"results": [], "elapsed": elapsed, "savings": 0, **meta}

    # Filter out empty/mock results that have no price
    valid = [r for r in results if r.get("price", 0) > 0]
    if not valid:
        # Return all even if no price — UI will mark as unavailable
        valid = results

    prices    = [r["price"] for r in valid if r.get("price", 0) > 0]
    min_price = min(prices) if prices else 0
    max_price = max(prices) if prices else 0

    enriched = []
    for r in valid:
        p = r.get("price", 0)
        enriched.append({
            **r,
            "is_best": p == min_price and p > 0,
            "discount_pct": _calc_discount(p, r.get("original_price", 0)),
            "savings_vs_max": max_price - p if p > 0 else 0,
        })

    enriched.sort(key=lambda x: x.get("price") or 999999)

    return {
        "results": enriched,
        "elapsed": elapsed,
        "savings": max_price - min_price,
        "best_store": enriched[0]["site"] if enriched and enriched[0].get("price", 0) > 0 else "",
        "stores_count": len(enriched),
        "min_price": min_price,
        "max_price": max_price,
        **meta,
    }


def _calc_discount(price, original):
    if original and original > price > 0:
        return round(((original - price) / original) * 100)
    return 0
import os
import webbrowser
from threading import Timer
def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000")

if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        Timer(1, open_browser).start()
    app.run(debug=True, port=5000)
