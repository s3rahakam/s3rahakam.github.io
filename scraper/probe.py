"""فحص: بيشوف المتاجر بترد على السكربت إزاي، ويحفظ الصفحات عشان نحللها."""
import pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from update_prices import fetch
out = pathlib.Path("probe"); out.mkdir(exist_ok=True)
urls = {
  "jumia_search": "https://www.jumia.com.eg/catalog/?q=dualsense",
  "noon_search": "https://www.noon.com/egypt-en/search/?q=dualsense",
  "amazon_search": "https://www.amazon.eg/s?k=dualsense",
}
for name, url in urls.items():
    try:
        r = fetch(url); t = r.text
        (out / f"{name}.html").write_text(t, encoding="utf-8")
        print(f"{name}: HTTP {r.status_code}, {len(t)} chars, ld+json={t.count('application/ld+json')}, "
              f"next_data={'__NEXT_DATA__' in t}, captcha={bool(re.search('captcha|robot check', t, re.I))}")
    except Exception as e:
        print(f"{name}: ERROR {e}")
