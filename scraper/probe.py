import re
from curl_cffi import requests as http
def get(u): return http.get(u, impersonate="chrome", timeout=40, headers={"Accept-Language": "en-US,en;q=0.9"})
t = get("https://btech.com/en/s?q=logitech%20g515").text
for m in list(re.finditer(r"imgi_2_Logitech_G515", t))[:4]:
    print("CTX:", re.sub(r"\s+"," ",t[m.start()-350:m.start()+80]))
imgs = re.findall(r'<img[^>]+>', t)
print("IMG tags:", [re.sub(r"\s+"," ",x)[:300] for x in imgs if "logo" not in x.lower()][:4])
