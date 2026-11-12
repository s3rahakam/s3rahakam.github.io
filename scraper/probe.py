"""فحص: بيشوف المتاجر بترد على السكربت إزاي، ويطبع ملخص نحلله."""
import json, re
from curl_cffi import requests as http

def get(url, imp="chrome"):
    return http.get(url, impersonate=imp, timeout=30, headers={"Accept-Language": "en-US,en;q=0.9,ar;q=0.8"})

def title(t):
    m = re.search(r"<title[^>]*>(.*?)</title>", t, re.S | re.I); return (m.group(1).strip()[:120] if m else "-")

print("=== JUMIA ===")
for imp in ["chrome", "chrome120", "safari17_0", "firefox133", "chrome131_android"]:
    for url in ["https://www.jumia.com.eg/catalog/?q=dualsense", "https://www.jumia.com.eg/"]:
        try:
            r = get(url, imp); print(imp, url[25:], r.status_code, len(r.text), "|", title(r.text), "| server:", r.headers.get("server"))
        except Exception as e:
            print(imp, url, "ERR", e)

print("=== AMAZON ===")
for imp in ["chrome", "safari17_0", "firefox133"]:
    r = get("https://www.amazon.eg/s?k=dualsense&language=en_AE", imp)
    print(imp, r.status_code, len(r.text), "|", title(r.text), "|", re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", r.text))[:200])

print("=== NOON ===")
r = get("https://www.noon.com/egypt-en/search/?q=dualsense")
t = r.text
print("status", r.status_code, len(t), title(t))
for i, b in enumerate(re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', t, re.S)):
    print(f"--- ld+json #{i} ({len(b)} chars):", b[:700].replace("\n", " "))
# أشكال الأسعار في الصفحة
print("price-like:", re.findall(r'"(?:price|sale_price|salePrice|offer_price)"\s*:\s*[\d.]+', t)[:10])
print("product urls:", list(dict.fromkeys(re.findall(r'href="(/egypt-en/[^"]+/p/[^"]*)"', t)))[:5])
i = t.find("sale_price"); print("ctx:", t[max(0,i-400):i+300].replace("\n"," ") if i>=0 else "none")
