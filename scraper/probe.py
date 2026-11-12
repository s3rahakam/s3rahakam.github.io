"""تجربة: كل متجر بيرجع إيه لكلمة واحدة."""
import sys, pathlib, re
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import update_prices as u
for q in ["DualSense controller", "iPhone 16"]:
    for store, fn in u.SEARCHERS.items():
        if store in ("noon", "amazon"): continue
        try:
            r = fn(q); print(f"== {q} / {store}: {len(r)}")
            for x in r[:4]: print("   ", x["price"], x["old_price"], x["in_stock"], x["name"][:70], "|", x["url"][:90], "|", x["image"][:60])
        except Exception as e:
            print(f"== {q} / {store}: ERROR {e}")
# B.TECH: شكل لينك المنتج
t = u.fetch("https://btech.com/en/s?q=dualsense")
print("btech hrefs:", list(dict.fromkeys(re.findall(r'href="(/en/[^"?#]+)"', t)))[:25])
print("btech img:", re.findall(r'https://[a-z.]*btech[a-z.]*/[^"\\ ]+\.(?:jpg|png|webp)', t)[:3])
t = u.fetch("https://2b.com.eg/en/catalogsearch/result/?q=dualsense")
i = t.find('product-item-link'); print("2b ctx:", re.sub(r"\s+"," ",t[i-1500:i+1500]))
