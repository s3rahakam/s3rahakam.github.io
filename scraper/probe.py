"""فحص متاجر مصرية: مين بيرد على السكربت وشكل بياناته إيه."""
import re
from curl_cffi import requests as http
Q = "dualsense"
URLS = {
 "btech": f"https://btech.com/en/catalogsearch/result/?q={Q}",
 "2b": f"https://2b.com.eg/en/catalogsearch/result/?q={Q}",
 "raya": f"https://www.rayashop.com/en/catalogsearch/result/?q={Q}",
 "dream2000": f"https://dream2000.com/catalogsearch/result/?q={Q}",
 "carrefour": f"https://www.carrefouregypt.com/mafegy/en/search?keyword={Q}",
 "select": f"https://www.select.com.eg/en/catalogsearch/result/?q={Q}",
 "games2egypt": f"https://games2egypt.com/search?q={Q}",
 "jumia_ar": f"https://www.jumia.com.eg/ar/catalog/?q={Q}",
}
def title(t):
    m = re.search(r"<title[^>]*>(.*?)</title>", t, re.S | re.I); return m.group(1).strip()[:80] if m else "-"
for name, url in URLS.items():
    try:
        r = http.get(url, impersonate="chrome", timeout=40, headers={"Accept-Language": "en-US,en;q=0.9"})
        t = r.text
        hints = [h for h in ["Shopify", "Magento", "mage/", "__NEXT_DATA__", "__NUXT__", "woocommerce", "algolia", "cloudflare", "captcha"] if h.lower() in t.lower()]
        print(f"{name}: {r.status_code} final={r.url[:70]} size={len(t)} title={title(t)!r} ld={t.count('ld+json')} "
              f"egp={len(re.findall(r'EGP|ج\\.م|LE ', t))} dualsense={t.lower().count('dualsense')} hints={hints}")
        for pat in [r'data-price-amount="([\d.]+)"', r'"price"\s*:\s*"?([\d.]+)', r'class="price"[^>]*>([^<]{0,30})']:
            m = re.findall(pat, t)
            if m: print("   ", pat[:25], m[:5])
    except Exception as e:
        print(f"{name}: ERROR {str(e)[:120]}")
