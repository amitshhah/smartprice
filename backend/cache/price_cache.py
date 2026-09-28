"""
cache/price_cache.py
In-memory TTL cache + price history tracking.
"""

import time
from collections import defaultdict


class PriceCache:
    def __init__(self, ttl_minutes: int = 15):
        self._ttl = ttl_minutes * 60
        self._store = {}
        self._history = defaultdict(list)

    def get(self, key: str):
        if key in self._store:
            expires_at, data = self._store[key]
            if time.time() < expires_at:
                return data
            del self._store[key]
        return None

    def set(self, key: str, value: dict):
        self._store[key] = (time.time() + self._ttl, value)
        if value.get("results"):
            snapshot = {
                "ts": int(time.time()),
                "prices": [{"site": r["site"], "price": r["price"]} for r in value["results"] if r.get("price")],
            }
            self._history[key].append(snapshot)
            self._history[key] = self._history[key][-30:]

    def get_history(self, product_id: str):
        return self._history.get(product_id, [])
