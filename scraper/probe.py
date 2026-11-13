import re
from curl_cffi import requests as http
def get(u): return http.get(u, impersonate="chrome", timeout=40, headers={"Accept-Language": "en-US,en;q=0.9"})
p = "9/8/7/5/9875543cca5c40d61e69e975d3ee98c47126024a_imgi_2_Logitech_G515_TKL.jpg"
for base in ["https://media.btech.com/media/catalog/product/", "https://media.btech.com/catalog/product/",
             "https://green-be-assets.btech.com/media/catalog/product/", "https://green-be-assets.btech.com/catalog/product/",
             "https://btech.com/media/catalog/product/", "https://media.btech.com/"]:
    try:
        r = get(base + p); print("BT", r.status_code, r.headers.get("content-type"), len(r.content), base)
    except Exception as e: print("BT ERR", base, str(e)[:60])
t = get("https://btech.com/en/s?q=logitech%20g515").text
print("BT any media urls:", list(dict.fromkeys(re.findall(r'https://(?:media|green-be-assets)\.btech\.com/[^"\s\\)]+', t)))[:6])
t = get("https://www.carrefouregypt.com/mafegy/en/search?keyword=dualsense").text
print("CF pim:", list(dict.fromkeys(re.findall(r'https?:\\?/\\?/[a-z0-9.-]*maf[a-z0-9.-]*\.com[^"\s,]*?\.(?:jpg|jpeg|png|webp)', t)))[:6])
i = t.find("1836147000713"); 
for m in re.finditer("1836147000713", t):
    s = t[m.start()-300:m.start()+600]
    if "jpg" in s or "image" in s.lower(): print("CF ctx:", re.sub(r"\s+"," ",s)[:900]); break
