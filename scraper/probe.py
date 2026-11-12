import sys, pathlib, re, time
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import update_prices as u
from curl_cffi import requests as http
url = "https://www.carrefouregypt.com/mafegy/en/search?keyword=dualsense"
for imp in ["chrome", "chrome120", "safari17_0", "firefox133", "chrome131_android", "edge101"]:
    for hv in [None, "v1"]:
        try:
            kw = {"http_version": hv} if hv else {}
            r = http.get(url, impersonate=imp, timeout=40, headers={"Accept-Language": "en-US,en;q=0.9"}, **kw)
            print(imp, hv, r.status_code, len(r.text), r.text.count("/p/"))
        except Exception as e:
            print(imp, hv, "ERR", str(e)[:90])
        time.sleep(3)
for q in ["DualSense controller"]:
    for store in ["btech", "2b"]:
        r = u.SEARCHERS[store](q)
        for x in r[:3]: print(store, x["price"], x["name"][:50], "|", x["url"][:80], "|", x["image"][:70])
