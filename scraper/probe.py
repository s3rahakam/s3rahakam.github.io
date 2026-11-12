import re, json
from curl_cffi import requests as http
def get(u, **k): return http.get(u, impersonate="chrome", timeout=40, headers={"Accept-Language": "en-US,en;q=0.9"}, **k)
def sq(s): return re.sub(r"\s+", " ", s)
print("##### 2B")
t = get("https://2b.com.eg/en/catalogsearch/result/?q=dualsense").text
i = t.find('<li class="item product product-item'); print(sq(t[i:i+3500]) if i >= 0 else "no li")
print("##### BTECH search")
t = get("https://btech.com/en").text
print(set(re.findall(r'(?:action|href)="(/en/[^"]*(?:search|q=)[^"]*)"', t)))
print(set(re.findall(r'"(/en/[a-z-]*search[^"]{0,40})"', t)))
for u in ["https://btech.com/en/search-results?q=dualsense", "https://btech.com/en/products?search=dualsense", "https://btech.com/en/s?q=dualsense", "https://btech.com/en/search/dualsense"]:
    r = get(u); print(r.status_code, u, len(r.text), r.text.lower().count("dualsense"))
print("##### DREAM2000")
r = get("https://dream2000.com/products.json?limit=3"); print("products.json", r.status_code, sq(r.text[:600]))
r = get("https://dream2000.com/search/suggest.json?q=dualsense&resources%5Btype%5D=product&resources%5Blimit%5D=5"); print("suggest", r.status_code, sq(r.text[:900]))
t = get("https://dream2000.com/search?q=dualsense&type=product").text
i = t.lower().find("dualsense", t.find("<main")); print(sq(t[i-1500:i+800]))
