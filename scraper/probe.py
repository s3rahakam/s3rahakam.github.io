import re
from curl_cffi import requests as http
t = http.get("https://www.carrefouregypt.com/mafegy/en/search?keyword=logitech%20mouse", impersonate="chrome", timeout=40,
             headers={"Accept-Language": "en-US,en;q=0.9"}).text
ids = list(dict.fromkeys(re.findall(r'/p/(\d{6,})', t)))[:3]
print("ids:", ids, "size:", len(t))
for pid in ids[:2]:
    for m in list(re.finditer(pid, t))[:6]:
        s = t[max(0, m.start()-500):m.start()+700]
        if "http" in s:
            print("CTX", pid, ":", re.sub(r"\s+", " ", s).replace("\\\"", '"')[:1200]); print()
print("img-like:", list(dict.fromkeys(re.findall(r'https?:(?:\\?/){2}[a-z0-9.-]+(?:\\?/)[^"\s,\\]*(?:jpg|jpeg|png|webp)[^"\s,\\]*', t)))[:12])
print("maf hosts:", sorted(set(re.findall(r'https?://([a-z0-9.-]*maf[a-z0-9.-]*)', t))))
