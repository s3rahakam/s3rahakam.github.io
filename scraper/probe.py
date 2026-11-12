import re, json
from curl_cffi import requests as http
def get(u): return http.get(u, impersonate="chrome", timeout=40, headers={"Accept-Language": "en-US,en;q=0.9"})
def title(t):
    m = re.search(r"<title[^>]*>(.*?)</title>", t, re.S | re.I); return m.group(1).strip()[:70] if m else "-"
def ctx(t, needle, before=300, after=900):
    i = t.find(needle); return re.sub(r"\s+", " ", t[max(0, i-before):i+after]) if i >= 0 else "NONE"

print("##### 2B")
t = get("https://2b.com.eg/en/catalogsearch/result/?q=dualsense").text
print(ctx(t, 'product-item-info', 0, 1800))

print("##### CARREFOUR")
t = get("https://www.carrefouregypt.com/mafegy/en/search?keyword=dualsense").text
for n in ["__NEXT_DATA__", "self.__next_f", "applicableOffer", "originalPrice", '"price"']:
    print(n, t.count(n))
print(ctx(t, "DualSense", 600, 1200))

for name, urls in {
  "btech": ["https://btech.com/en/search?q=dualsense", "https://btech.com/en/catalogsearch/result/?q=dualsense", "https://btech.com/en/"],
  "dream2000": ["https://dream2000.com/search?q=dualsense&type=product", "https://dream2000.com/search/suggest.json?q=dualsense&resources[type]=product&resources[limit]=5"],
  "games2egypt": ["https://www.games2egypt.com/en/catalogsearch/result/?q=dualsense", "https://www.games2egypt.com/catalogsearch/result/?q=dualsense"],
  "raya": ["https://www.rayashop.com/en/catalogsearch/result?q=dualsense"],
}.items():
    print("#####", name)
    for u in urls:
        try:
            r = get(u); t = r.text
            print(r.status_code, u[8:70], "->", r.url[8:70], len(t), title(t), "dualsense:", t.lower().count("dualsense"))
            if "suggest.json" in u and r.status_code == 200:
                print(t[:900])
            elif r.status_code == 200 and t.lower().count("dualsense") > 3:
                print("  ", ctx(t, "ualSense", 400, 700)[:1100])
        except Exception as e:
            print("ERR", u, str(e)[:100])
