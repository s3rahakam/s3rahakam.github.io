import re
from curl_cffi import requests as http
def get(u): return http.get(u, impersonate="chrome", timeout=40, headers={"Accept-Language": "en-US,en;q=0.9"}).text
t = get("https://btech.com/en/s?q=logitech%20g515").replace('\\"', '"')
print("thumb:", re.findall(r'"thumbnail_url":"([^"]+)"', t)[:2])
print("img hosts:", sorted(set(re.findall(r'https?://([a-z0-9.-]+)/[^"\s]*\.(?:jpg|jpeg|png|webp)', t)))[:10])
print("sample imgs:", [u for u in re.findall(r'https?://[^"\s\\]+\.(?:jpg|jpeg|png|webp)[^"\s\\]*', t) if 'btech' in u][:4])
i = t.find('"thumbnail_url"'); print("ctx:", t[i-200:i+400])
t = get("https://www.carrefouregypt.com/mafegy/en/search?keyword=dualsense")
i = t.find('/p/'); print("CARREFOUR ctx:", re.sub(r"\s+", " ", t[i-2500:i+200]))
print("cf imgs:", list(dict.fromkeys(re.findall(r'(?:src|srcSet|srcset)="([^" ]+)', t)))[:8])
