"""
يحدّث products.json من صفحات المنتجات اللي في tracked.csv.

لكل منتج، بيفتح لينك كل متجر (جوميا / نون / أمازون)، ويطلع السعر والتوفر،
ويكتب النتيجة في products.json اللي الموقع بيقرا منه.

لو صفحة فشلت، بيحتفظ بآخر سعر معروف بدل ما يمسحه.
"""
import csv
import json
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from curl_cffi import requests as http  # بيقلّد متصفح Chrome، فبيتقفل أقل

    def fetch(url):
        return http.get(url, impersonate="chrome", timeout=30,
                        headers={"Accept-Language": "ar-EG,ar;q=0.9,en;q=0.8"})
except ImportError:  # احتياطي
    import requests as http

    def fetch(url):
        return http.get(url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept-Language": "ar-EG,ar;q=0.9,en;q=0.8"})

ROOT = Path(__file__).resolve().parent.parent
TRACKED = ROOT / "tracked.csv"
OUTPUT = ROOT / "products.json"

STORES = {
    "amazon": {"name": "أمازون مصر", "affiliate": False, "search": "https://www.amazon.eg/s?k="},
    "noon":   {"name": "نون",        "affiliate": False, "search": "https://www.noon.com/egypt-ar/search/?q="},
    "jumia":  {"name": "جوميا",      "affiliate": False, "search": "https://www.jumia.com.eg/catalog/?q="},
}
STORE_ORDER = ["jumia", "noon", "amazon"]


# ---------- استخراج السعر ----------

def to_number(value):
    """'EGP 3,899.00' أو '٣٬٨٩٩' -> 3899.0"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None
    s = str(value).translate(str.maketrans("٠١٢٣٤٥٦٧٨٩٬٫", "0123456789,."))
    m = re.search(r"\d[\d,]*(?:\.\d+)?", s)
    if not m:
        return None
    n = float(m.group(0).replace(",", ""))
    return n if n > 0 else None


def walk(obj):
    """يلف على كل القواميس جوه JSON متداخل."""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v)


def from_json_ld(html):
    """أغلب المتاجر بتحط بيانات المنتج في <script type="application/ld+json">."""
    for block in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.S | re.I):
        try:
            data = json.loads(block.strip())
        except ValueError:
            continue
        for node in walk(data):
            t = node.get("@type")
            types = t if isinstance(t, list) else [t]
            if "Product" not in types:
                continue
            offers = node.get("offers")
            for offer in ([offers] if isinstance(offers, dict) else offers or []):
                if not isinstance(offer, dict):
                    continue
                price = to_number(offer.get("price") or offer.get("lowPrice"))
                if price:
                    avail = str(offer.get("availability", ""))
                    in_stock = None
                    if avail:
                        in_stock = not re.search(r"OutOfStock|SoldOut|Discontinued", avail, re.I)
                    return price, in_stock
    return None, None


def from_meta(html):
    for pat in [
        r'<meta[^>]+(?:property|itemprop|name)=["\'](?:product:price:amount|og:price:amount|price)["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|itemprop|name)=["\'](?:product:price:amount|og:price:amount|price)["\']',
    ]:
        m = re.search(pat, html, re.I)
        if m and to_number(m.group(1)):
            return to_number(m.group(1)), None
    return None, None


def parse_jumia(html):
    price, stock = from_json_ld(html)
    if not price:
        # جوميا: <span class="-b -ubpt -tal -fs24 -prxs">EGP 3,899</span>
        m = re.search(r'data-price=["\']([\d.,]+)', html) or \
            re.search(r'class="-b -ubpt[^"]*"[^>]*>\s*(?:EGP|جنيه)?\s*([\d.,]+)', html)
        price = to_number(m.group(1)) if m else None
    if stock is None:
        stock = not re.search(r"out of stock|نفذت الكمية|غير متوفر", html, re.I)
    return price, stock


def parse_noon(html):
    price, stock = from_json_ld(html)
    if not price:
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
        if m:
            try:
                for node in walk(json.loads(m.group(1))):
                    p = node.get("sale_price") or node.get("salePrice") or node.get("price")
                    if to_number(p) and ("sku" in node or "offer_code" in node or "offerCode" in node):
                        price = to_number(p)
                        if "is_buyable" in node:
                            stock = bool(node["is_buyable"])
                        break
            except ValueError:
                pass
    if stock is None and price:
        stock = not re.search(r"out of stock|غير متوفر حاليا", html, re.I)
    return price, stock


def parse_amazon(html):
    if re.search(r"captcha|Robot Check", html, re.I):
        raise RuntimeError("أمازون طلب كابتشا (اتقفل)")
    m = re.search(r'class="a-price[^"]*"[^>]*>\s*<span class="a-offscreen">([^<]+)<', html) or \
        re.search(r'id="priceblock_(?:our|deal)price"[^>]*>([^<]+)<', html)
    price = to_number(m.group(1)) if m else None
    if not price:
        price, _ = from_json_ld(html)
    stock = not re.search(r'id="outOfStock"|Currently unavailable|غير متوفر حالياً', html, re.I)
    return price, stock


PARSERS = {"jumia": parse_jumia, "noon": parse_noon, "amazon": parse_amazon}


# ---------- التشغيل ----------

def load_previous():
    try:
        old = json.loads(OUTPUT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if old.get("demo"):
        return {}  # أسعار الأمثلة مش أسعار حقيقية، منحتفظش بيها
    return {(p["id"], o["store"]): o for p in old.get("products", []) for o in p.get("offers", [])}


def main():
    previous = load_previous()
    rows = list(csv.DictReader(TRACKED.open(encoding="utf-8-sig")))
    products, ok, failed = [], 0, []

    for row in rows:
        pid = (row.get("id") or "").strip()
        if not pid:
            continue
        offers = []
        for store in STORE_ORDER:
            url = (row.get(store) or "").strip()
            if not url:
                continue
            offer = {"store": store, "url": url, "price": 0, "in_stock": None, "checked": None}
            try:
                r = fetch(url)
                if r.status_code != 200:
                    raise RuntimeError(f"HTTP {r.status_code}")
                price, in_stock = PARSERS[store](r.text)
                if not price:
                    raise RuntimeError("ملقتش السعر في الصفحة")
                offer.update(price=round(price), in_stock=in_stock,
                             checked=datetime.now(timezone.utc).isoformat(timespec="minutes"))
                ok += 1
                print(f"✓ {pid} / {store}: {price:,.0f} ج.م {'متوفر' if in_stock else 'غير متوفر'}")
            except Exception as e:  # noqa: BLE001
                failed.append(f"{pid} / {store}: {e}")
                print(f"✗ {pid} / {store}: {e}", file=sys.stderr)
                old = previous.get((pid, store))
                if old:  # احتفظ بآخر سعر معروف
                    offer.update(price=old.get("price", 0), in_stock=old.get("in_stock"),
                                 checked=old.get("checked"), stale=True)
            offers.append(offer)
            time.sleep(random.uniform(3, 7))  # متضغطش على المتجر
        products.append({
            "id": pid,
            "name": row.get("name", pid).strip(),
            "category": (row.get("category") or "أخرى").strip(),
            "search": (row.get("search") or row.get("name") or "").strip(),
            "offers": offers,
        })

    data = {
        "demo": False,
        "updated": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "stores": STORES,
        "products": products,
    }
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nتم: {ok} سعر اتحدث، {len(failed)} فشل.")
    if ok == 0 and failed:
        sys.exit("ولا سعر اتحدث. غالبًا المتاجر قافلة السكربت، أو اللينكات غلط.")


if __name__ == "__main__":
    main()
