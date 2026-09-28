"""
scrapers/link_parser.py
Detects which e-commerce site a URL belongs to and extracts
product identifiers / search hints from the URL structure.
"""

import re
from urllib.parse import urlparse, parse_qs


def parse_product_link(url: str):
    """
    Returns { site, product_id, query_hint } or None if unsupported.
    """
    try:
        parsed = urlparse(url.strip())
        host = parsed.netloc.lower().replace("www.", "")
    except Exception:
        return None

    extractors = {
        "amazon.in": ("Amazon", _extract_amazon),
        "amzn.in": ("Amazon", _extract_amazon),
        "flipkart.com": ("Flipkart", _extract_flipkart),
        "dl.flipkart.com": ("Flipkart", _extract_flipkart),
        "meesho.com": ("Meesho", _extract_meesho),
        "croma.com": ("Croma", _extract_croma),
    }

    for domain, (site, fn) in extractors.items():
        if host == domain or host.endswith("." + domain):
            info = fn(parsed)
            return {"site": site, **(info or {"product_id": None, "query_hint": ""})}

    return None


def _extract_amazon(parsed):
    path = parsed.path
    m = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", path)
    product_id = m.group(1) if m else None
    slug = path.split("/dp/")[0].lstrip("/")
    query_hint = slug.replace("-", " ").strip() if slug else ""
    return {"product_id": product_id, "query_hint": query_hint}


def _extract_flipkart(parsed):
    path = parsed.path
    qs = parse_qs(parsed.query)
    slug = path.strip("/").split("/")[0]
    query_hint = slug.replace("-", " ")
    pid = qs.get("pid", [None])[0]
    return {"product_id": pid, "query_hint": query_hint}


def _extract_meesho(parsed):
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    slug = parts[0] if parts else ""
    query_hint = slug.replace("-", " ")
    product_id = parts[2] if len(parts) > 2 else None
    return {"product_id": product_id, "query_hint": query_hint}


def _extract_croma(parsed):
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    product_id = parts[-1] if parts and parts[-1].isdigit() else None
    slug = parts[-2] if len(parts) >= 2 else ""
    query_hint = slug.replace("-", " ")
    return {"product_id": product_id, "query_hint": query_hint}
