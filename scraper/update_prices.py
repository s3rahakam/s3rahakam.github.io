"""
بيحدّث products.json لوحده.

لكل كلمة بحث في searches.csv:
  1. يبحث في نون وأمازون مصر ويجيب أول نتايج (الاسم، السعر، الصورة، التوفر، اللينك).
  2. يطابق المنتج الواحد بين المتجرين بالاسم.
  3. يكتب النتيجة في products.json اللي الموقع بيقرا منه.

لو متجر فشل، بيحتفظ بآخر أسعار معروفة ليه ويعلّم عليها "قديم".
"""
import csv
import html as htmllib
import json
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

from curl_cffi import requests as http

ROOT = Path(__file__).resolve().parent.parent
SEARCHES = ROOT / "searches.csv"
OUTPUT = ROOT / "products.json"
PER_STORE = 8  # كام نتيجة من كل متجر لكل كلمة

STORES = {
    "noon":   {"name": "نون",        "affiliate": False, "search": "https://www.noon.com/egypt-en/search/?q="},
    "amazon": {"name": "أمازون مصر", "affiliate": False, "search": "https://www.amazon.eg/s?k="},
    "btech":  {"name": "B.TECH",     "affiliate": False, "search": "https://btech.com/en/s?q="},
    "2b":     {"name": "2B",         "affiliate": False, "search": "https://2b.com.eg/en/catalogsearch/result/?q="},
    "carrefour": {"name": "كارفور",  "affiliate": False, "search": "https://www.carrefouregypt.com/mafegy/en/search?keyword="},
    "jumia":  {"name": "جوميا",      "affiliate": False, "search": "https://www.jumia.com.eg/catalog/?q="},
}


def fetch(url, tries=3):
    for attempt in range(tries):
        r = http.get(url, impersonate="chrome", timeout=40,
                     headers={"Accept-Language": "en-US,en;q=0.9,ar;q=0.8"})
        if r.status_code == 200:
            return r.text
        if r.status_code in (429, 503) and attempt < tries - 1:
            wait = 20 * (attempt + 1) + random.uniform(0, 10)
            print(f"  … HTTP {r.status_code}، هستنى {wait:.0f} ثانية وأجرب تاني")
            time.sleep(wait)
            continue
        raise RuntimeError(f"HTTP {r.status_code}")


def money(s):
    if s is None:
        return None
    m = re.search(r"\d[\d,]*(?:\.\d+)?", str(s))
    if not m:
        return None
    n = float(m.group(0).replace(",", ""))
    return round(n) if n > 0 else None


# ---------- نون ----------

def search_noon(q):
    page = fetch(STORES["noon"]["search"] + quote_plus(q))
    start = page.find("hits:")
    if start < 0:
        raise RuntimeError("شكل صفحة نون اتغير (ملقتش النتايج)")
    chunks = page[start:].split('{offer_code:"')[1:]
    out = []
    for c in chunks:
        c = c[:4000]
        code = c.split('"', 1)[0]
        def field(name, pat=r'"((?:[^"\\]|\\.)*)"'):
            m = re.search(r'[{,]' + name + r':' + pat, "," + c)
            return m.group(1) if m else None
        name = field("name")
        sku = field("sku")
        slug = field("url")
        price = money(field("sale_price", r"([\d.]+)")) or money(field("price", r"([\d.]+)"))
        if not (name and sku and slug and price):
            continue
        buy = field("is_buyable", r"(!0|!1|true|false)")
        brand = field("brand")
        out.append({
            "store": "noon",
            "brand": json.loads(f'"{brand}"') if brand else "Generic",
            "name": json.loads(f'"{name}"'),
            "price": price,
            "old_price": money(field("price", r"([\d.]+)")),
            "image": json.loads(f'"{field("image_url") or ""}"'),
            "url": f"https://www.noon.com/egypt-en/{slug}/{sku}/p/?o={code}",
            "in_stock": buy not in ("!1", "false"),
            "key": "noon:" + sku,
        })
        if len(out) >= PER_STORE:
            break
    return out


# ---------- أمازون ----------

def search_amazon(q):
    page = fetch(STORES["amazon"]["search"] + quote_plus(q) + "&language=en_AE")
    if "triggerInterstitialChallenge" in page or re.search(r"captcha", page[:5000], re.I):
        raise RuntimeError("أمازون طلب تحقق (اتقفل)")
    blocks = re.split(r'(?=<div[^>]*data-component-type="s-search-result")', page)[1:]
    out = []
    for b in blocks:
        b = b[:30000]
        asin = re.search(r'data-asin="([A-Z0-9]{10})"', b)
        if not asin or "AdHolder" in b[:600] or ">Sponsored<" in b:
            continue
        title = re.search(r'<h2[^>]*aria-label="([^"]+)"', b) or \
            re.search(r'<h2[^>]*>.*?<span[^>]*>([^<]+)</span>', b, re.S)
        price = re.search(r'<span class="a-price"[^>]*>\s*<span class="a-offscreen">([^<]+)<', b)
        old = re.search(r'<span class="a-price a-text-price"[^>]*>\s*<span class="a-offscreen">([^<]+)<', b)
        img = re.search(r'<img[^>]+class="s-image"[^>]+src="([^"]+)"', b)
        if not (title and price):
            continue
        name = htmllib.unescape(title.group(1)).strip()
        name = re.sub(r"^Sponsored Ad - ", "", name)
        out.append({
            "store": "amazon",
            "name": name,
            "price": money(price.group(1)),
            "old_price": money(old.group(1)) if old else None,
            "image": img.group(1) if img else "",
            "url": f"https://www.amazon.eg/dp/{asin.group(1)}",
            "in_stock": True,  # أمازون مش بيعرض سعر لغير المتوفر
            "key": "amazon:" + asin.group(1),
        })
        if len(out) >= PER_STORE:
            break
    return out


# ---------- B.TECH ----------

def search_btech(q):
    page = fetch("https://btech.com/en/s?q=" + quote_plus(q))
    data = page.replace('\\"', '"')
    out, seen = [], set()
    for m in re.finditer(r'\{"variant_id":"[^"]+","product_id":"[^"]+"', data):
        c = data[m.start():m.start() + 3000]
        name = re.search(r'"name":"((?:[^"\\]|\\.)*)"', c)
        brand = re.search(r'"brand":"((?:[^"\\]|\\.)*)"', c)
        price = re.search(r'"final_price":([\d.]+)', c)
        base = re.search(r'"base_price":([\d.]+)', c)
        stock = re.search(r'"is_in_stock":(true|false)', c)
        thumb = re.search(r'"thumbnail_url":"([^"]+)"', c)
        slug = re.search(r'"slug":"([^"]+)"', c[c.find('"color_options"') if '"color_options"' in c else 0:]) \
            or re.search(r'"product_slug":"([^"]+)"', c)
        sku = re.search(r'"sku":"([^"]+)"', c)
        if not (name and price and sku) or sku.group(1) in seen:
            continue
        seen.add(sku.group(1))
        out.append({
            "store": "btech",
            "brand": brand.group(1) if brand else "",
            "name": name.group(1),
            "price": money(price.group(1)),
            "old_price": money(base.group(1)) if base else None,
            "image": "https://media.btech.com/" + thumb.group(1) if thumb else "",
            "url": f"https://btech.com/en/p/{slug.group(1)}" if slug else "https://btech.com/en/s?q=" + quote_plus(q),
            "in_stock": not stock or stock.group(1) == "true",
            "key": "btech:" + sku.group(1),
        })
        if len(out) >= PER_STORE:
            break
    if not out and "is_in_stock" not in data:
        raise RuntimeError("شكل صفحة B.TECH اتغير")
    return out


# ---------- 2B ----------

def search_2b(q):
    page = fetch("https://2b.com.eg/en/catalogsearch/result/?q=" + quote_plus(q))
    out = []
    for c in page.split('class="product-item-link"')[1:]:
        c = c[:6000]
        link = re.search(r'href="([^"]+)"[^>]*>\s*([^<]+?)\s*</a>', c)
        price = re.search(r'data-price-amount="([\d.]+)"[^>]*data-price-type="finalPrice"', c) or \
            re.search(r'data-price-type="finalPrice"[^>]*data-price-amount="([\d.]+)"', c)
        old = re.search(r'data-price-amount="([\d.]+)"[^>]*data-price-type="oldPrice"', c)
        if not (link and price):
            continue
        out.append({
            "store": "2b",
            "name": htmllib.unescape(link.group(2)),
            "price": money(price.group(1)),
            "old_price": money(old.group(1)) if old else None,
            "image": "",
            "url": link.group(1),
            "in_stock": "out-of-stock" not in c[:3000] and "unavailable" not in c[:3000],
            "key": "2b:" + link.group(1).rstrip("/").rsplit("/", 1)[-1][:80],
        })
        if len(out) >= PER_STORE:
            break
    return out


# ---------- كارفور ----------

def search_carrefour(q):
    page = fetch("https://www.carrefouregypt.com/mafegy/en/search?keyword=" + quote_plus(q))
    out = []
    for m in re.finditer(r'<a[^>]+href="(/mafegy/en/[^"]+/p/(\d+)[^"]*)"[^>]*><span[^>]*>([^<]+)</span></a>'
                         r'<div[^>]*>(.{0,600}?)</div>', page):
        prices = re.findall(r'>([\d,]+(?:\.\d+)?)</span>', m.group(4))
        if not prices:
            continue
        vals = [money(p) for p in prices if money(p)]
        img = re.findall(r'<img[^>]+src="(https://cdn[^"]+/(?:pim|product)[^"]+)"', page[max(0, m.start() - 4000):m.start()])
        out.append({
            "store": "carrefour",
            "name": htmllib.unescape(m.group(3)),
            "price": min(vals),
            "old_price": max(vals) if len(vals) > 1 else None,
            "image": img[-1] if img else "",
            "url": "https://www.carrefouregypt.com" + htmllib.unescape(m.group(1)),
            "in_stock": True,
            "key": "carrefour:" + m.group(2),
        })
        if len(out) >= PER_STORE:
            break
    return out


SEARCHERS = {"noon": search_noon, "amazon": search_amazon, "btech": search_btech,
             "2b": search_2b, "carrefour": search_carrefour}


# ---------- المطابقة بين المتاجر ----------

STOP = set("for with the and of to in by new original official version edition wireless "
           "gaming console controller ps5 ps playstation 5 pack bundle egypt uae ksa "
           "warranty international black white sony apple samsung xiaomi anker jbl logitech "
           "lenovo hp dell huawei oppo realme honor infinix tecno nokia electronic arts ea sports".split())
COLORS = set("black white red blue green grey gray silver gold pink purple yellow orange "
             "camouflage camo midnight cosmic starlight volcanic chroma sterling indigo teal".split())


VARIANTS = set("pro max plus ultra mini edge lite fe slim digital disc air se neo prime".split())


BRANDS = set("sony apple samsung xiaomi redmi anker jbl logitech lenovo hp dell huawei oppo realme "
             "honor infinix tecno nokia havit baseus ugreen oraimo joyroom lg razer hyperx redragon "
             "corsair steelseries soundcore beats bose marshall amazfit garmin generic".split())
GENERIC_NUM = {"ps5", "ps4", "5g", "4g", "usb", "3a", "2", "1"}


def keywords(name):
    """الكلمات المهمة بالترتيب (أول الاسم هو اللي فيه الموديل عادةً)."""
    n = name.lower()
    n = re.sub(r"play\s*station\s*5|\bps\s*5\b", " ps5 ", n)
    n = re.sub(r"(\d+)\s+(gb|tb|mah|w|mm|inch|hz|k)\b", r"\1\2", n)
    n = re.sub(r"\bdual\s+sense\b", "dualsense", n)
    n = re.sub(r"\blight\s+sync\b", "lightsync", n)
    return re.findall(r"[a-z0-9]+", n)


def similar(a, b):
    wa, wb = keywords(a), keywords(b)
    ta, tb = set(wa), set(wb)
    if ta & VARIANTS != tb & VARIANTS:  # iPhone 16 غير iPhone 16 Pro
        return 0
    ka = [w for w in wa if w not in STOP][:8]
    kb = [w for w in wb if w not in STOP][:8]
    if not ka or not kb:
        return 0
    sa, sb = set(ka), set(kb)
    # أول لون مذكور هو لون المنتج نفسه (اللي بعده غالبًا لون الحزام أو العلبة)
    ca = next((w for w in wa if w in COLORS), None)
    cb = next((w for w in wb if w in COLORS), None)
    if ca and cb and ca != cb and {ca, cb} != {"grey", "gray"}:
        return 0
    if ("wired" in ta) != ("wired" in tb) and ("wireless" in ta or "wireless" in tb):
        return 0
    # ماركات مختلفة = منتجات مختلفة
    head = lambda w: set(w[:next((i for i, x in enumerate(w) if x in ("for", "compatible", "with")), len(w))])
    ba, bb = head(wa) & BRANDS, head(wb) & BRANDS
    if ba and bb and not (ba & bb):
        return 0
    # أرقام مختلفة (مقاس، مساحة، سنة الموديل) = منتجات مختلفة
    na = {w for w in sa if any(c.isdigit() for c in w)} - GENERIC_NUM
    nb = {w for w in sb if any(c.isdigit() for c in w)} - GENERIC_NUM
    if na and nb and not (na <= nb or nb <= na):
        return 0
    score = len(sa & sb) / len(sa | sb)
    if na & nb and any(c.isalpha() for w in na & nb for c in w):
        score += 0.3  # كود موديل مشترك زي G102 أو A56
    return score


def merge(results, category, query):
    """يحوّل نتايج المتاجر لمنتجات، وكل منتج فيه عروض من أكتر من متجر."""
    products = []
    for r in sorted(results, key=lambda x: x["store"] != "noon"):
        best, score = None, 0
        for p in products:
            if any(o["store"] == r["store"] for o in p["offers"]):
                continue
            s = similar(p.get("brand", "") + " " + p["name"], r.get("brand", "") + " " + r["name"])
            if s > score:
                best, score = p, s
        offer = {k: r[k] for k in ("store", "price", "old_price", "url", "in_stock")}
        if best and score >= 0.5:
            best["offers"].append(offer)
            best["image"] = best["image"] or r["image"]
        else:
            products.append({
                "brand": r.get("brand", ""),
                "id": r["key"].replace(":", "-"),
                "name": r["name"],
                "category": category,
                "search": query,
                "image": r["image"],
                "offers": [offer],
            })
    return products


# ---------- التشغيل ----------

def main():
    try:
        old = json.loads(OUTPUT.read_text(encoding="utf-8"))
        old = [] if old.get("demo") else old.get("products", [])
    except (OSError, ValueError):
        old = []

    rows = [r for r in csv.DictReader(SEARCHES.open(encoding="utf-8-sig")) if (r.get("search") or "").strip()]
    products, seen, ok, failed = [], set(), 0, []

    for row in rows:
        q, cat = row["search"].strip(), (row.get("category") or "أخرى").strip()
        results, dead = [], []
        for store, fn in SEARCHERS.items():
            try:
                found = fn(q)
                results += found
                ok += 1
                print(f"✓ {q} / {store}: {len(found)} منتج")
            except Exception as e:  # noqa: BLE001
                failed.append(f"{q} / {store}: {e}")
                dead.append(store)
                print(f"✗ {q} / {store}: {e}", file=sys.stderr)
            time.sleep(random.uniform(4, 8))

        merged = merge(results, cat, q)
        # متجر فشل؟ رجّع آخر أسعاره المعروفة لنفس الكلمة
        for p in old:
            if p.get("search") != q:
                continue
            for o in p.get("offers", []):
                if o["store"] in dead and not any(m["id"] == p["id"] for m in merged):
                    merged.append({**p, "offers": [{**o, "stale": True}]})

        for p in merged:
            if p["id"] not in seen:
                seen.add(p["id"])
                products.append(p)

    data = {
        "demo": False,
        "updated": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "stores": STORES,
        "products": products,
    }
    multi = sum(1 for p in products if len(p["offers"]) > 1)
    print(f"\nتم: {len(products)} منتج ({multi} منهم متقارن في أكتر من متجر). "
          f"{ok} بحث نجح، {len(failed)} فشل.")
    if not products:
        sys.exit("ولا منتج اتجاب. مش هغيّر الموقع.")
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
