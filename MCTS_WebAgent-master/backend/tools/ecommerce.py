
# # backend/tools/ecommerce.py
# """
# Real-time e-commerce price scraper — India.

# Sources:
#   1. Amazon.in  — CSS selectors + full-page text scan fallback
#   2. Flipkart   — CSS selectors (all known variants) + text scan fallback
#   3. Myntra     — JSON API (only if product is fashion/lifestyle)
#   4. Official   — schema.org / OpenGraph / text scan (if URL given)

# Per-platform Bing snippet fallback when direct scraping blocked.
# ZERO LLM-generated prices.
# """

# import requests
# import re
# import time
# import random
# from bs4 import BeautifulSoup
# from config import REQUEST_TIMEOUT, MCTS_SIMULATIONS
# from mcts.web_scraping_mcts import run_mcts_scraping


# # ──────────────────────────────────────────────────────────────────
# # Category price floors  (stops ₹9,999 passing as laptop price)
# # ──────────────────────────────────────────────────────────────────
# CATEGORY_FLOORS = {
#     "macbook": 80000, "imac": 80000,
#     "laptop": 15000,  "notebook": 15000, "chromebook": 12000,
#     "desktop": 15000, "computer": 10000,
#     "iphone": 40000,
#     "smartphone": 5000, "mobile": 3000, "phone": 3000,
#     "oneplus": 15000, "samsung": 3000, "pixel": 30000,
#     "redmi": 5000, "realme": 5000, "poco": 7000,
#     "vivo": 5000, "oppo": 5000, "motorola": 7000,
#     "ipad": 30000, "tablet": 5000,
#     "smart tv": 10000, "television": 10000, "tv": 8000,
#     "oled": 30000, "qled": 25000,
#     "refrigerator": 10000, "fridge": 10000,
#     "washing machine": 10000, "washer": 10000,
#     "air conditioner": 15000, "microwave": 5000, "oven": 5000,
#     "headphone": 500, "earphone": 200, "earbuds": 300,
#     "speaker": 500, "soundbar": 3000,
#     "camera": 5000, "dslr": 20000, "mirrorless": 30000,
#     "smartwatch": 2000, "watch": 500,
#     "keyboard": 300, "mouse": 200, "monitor": 5000,
#     "printer": 3000, "router": 1000,
#     "hard disk": 2000, "ssd": 1500,
#     "gpu": 15000, "graphics card": 15000,
#     "mixer": 1500, "grinder": 500, "iron": 500,
#     "trimmer": 500, "shaver": 500, "fan": 500,
#     "cooler": 2000, "heater": 1000, "purifier": 3000,
#     "default": 200,
# }
# PRICE_MAX = 500000

# # Products Myntra actually sells (fashion / lifestyle / accessories)
# MYNTRA_SELLS = {
#     "watch","watches","shoe","shoes","sneaker","sandal","bag","bags",
#     "backpack","handbag","tshirt","shirt","dress","jeans","trouser",
#     "kurta","saree","jacket","coat","hoodie","sweater","sunglasses",
#     "earring","necklace","bracelet","perfume","lipstick","moisturizer",
#     "trimmer","shaver","earbuds","headphone","smartwatch",
#     "fastrack","titan","boat","noise","zebronics","skullcandy",
# }


# def _floor(product: str) -> int:
#     p = product.lower()
#     for kw, f in CATEGORY_FLOORS.items():
#         if kw in p:
#             return f
#     return CATEGORY_FLOORS["default"]


# def _valid(price, floor: int) -> bool:
#     return price is not None and floor <= float(price) <= PRICE_MAX


# def _myntra_ok(product: str) -> bool:
#     p = product.lower()
#     return any(cat in p for cat in MYNTRA_SELLS)


# # ──────────────────────────────────────────────────────────────────
# # Session factory
# # ──────────────────────────────────────────────────────────────────
# _UA = [
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
#     "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) "
#     "Gecko/20100101 Firefox/124.0",
#     "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 "
#     "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
# ]


# def _session(ref="https://www.google.co.in/"):
#     s = requests.Session()
#     s.headers.update({
#         "User-Agent":                random.choice(_UA),
#         "Accept-Language":           "en-IN,en;q=0.9,hi;q=0.8",
#         "Accept":                    "text/html,application/xhtml+xml,"
#                                      "application/xml;q=0.9,image/avif,"
#                                      "image/webp,*/*;q=0.8",
#         "Accept-Encoding":           "gzip, deflate, br",
#         "Referer":                   ref,
#         "DNT":                       "1",
#         "Connection":                "keep-alive",
#         "Upgrade-Insecure-Requests": "1",
#     })
#     return s


# # ──────────────────────────────────────────────────────────────────
# # Parsers
# # ──────────────────────────────────────────────────────────────────
# def _parse_inr(text: str):
#     if not text:
#         return None
#     text = re.sub(r'[,\xa0\u200b]', '', str(text)).strip()
#     for pat in [r'₹\s*([0-9]+(?:\.[0-9]{1,2})?)',
#                 r'Rs\.?\s*([0-9]+(?:\.[0-9]{1,2})?)',
#                 r'INR\s*([0-9]+(?:\.[0-9]{1,2})?)']:
#         m = re.search(pat, text, re.IGNORECASE)
#         if m:
#             try:
#                 return float(m.group(1))
#             except Exception:
#                 continue
#     return None


# def _parse_rating(text: str):
#     if not text:
#         return None
#     m = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*(?:out\s*of\s*5|/5|stars?)?',
#                   str(text), re.IGNORECASE)
#     if m:
#         try:
#             v = float(m.group(1))
#             if 0.0 < v <= 5.0:
#                 return round(v, 1)
#         except Exception:
#             pass
#     return None


# def _all_prices(text: str, floor: int) -> list:
#     """Extract every valid ₹ price from text that meets the floor."""
#     text  = re.sub(r'[,]', '', str(text))
#     found = []
#     for pat in [r'₹\s*([0-9]+(?:\.[0-9]{1,2})?)',
#                 r'Rs\.?\s*([0-9]+(?:\.[0-9]{1,2})?)',
#                 r'INR\s*([0-9]+(?:\.[0-9]{1,2})?)']:
#         for m in re.findall(pat, text, re.IGNORECASE):
#             try:
#                 v = float(m)
#                 if _valid(v, floor):
#                     found.append(v)
#             except Exception:
#                 continue
#     return sorted(set(found))


# def _median(prices: list):
#     """Median of prices, trimming top 20% outliers."""
#     if not prices:
#         return None
#     prices  = sorted(prices)
#     trimmed = prices[:max(1, int(len(prices) * 0.8))]
#     return trimmed[len(trimmed) // 2]


# # ──────────────────────────────────────────────────────────────────
# # Main handler
# # ──────────────────────────────────────────────────────────────────
# def handle_ecommerce(query: str) -> str:
#     try:
#         product      = extract_product_name(query)
#         official_url = extract_official_url(query)
#         floor        = _floor(product)
#         use_myntra   = _myntra_ok(product)

#         out  = f"🔍 Real-Time Price Comparison — India\n{'='*70}\n"
#         out += f"🛍️  Product      : {product.title()}\n"
#         out += f"💰 Price floor   : ₹{floor:,} (junk values rejected below this)\n"
#         srcs = "Amazon.in | Flipkart"
#         if use_myntra:
#             srcs += " | Myntra"
#         if official_url:
#             srcs += " | Official Site"
#         out += f"📡 Sources       : {srcs}\n\n"

#         # Build platforms
#         platforms = [
#             {'name': 'Amazon India', 'base_url': 'https://www.amazon.in',
#              'search_path': '/s?k=', 'priority': 1, 'type': 'amazon'},
#             {'name': 'Flipkart',     'base_url': 'https://www.flipkart.com',
#              'search_path': '/search?q=', 'priority': 2, 'type': 'flipkart'},
#         ]
#         if use_myntra:
#             platforms.append({'name': 'Myntra', 'base_url': 'https://www.myntra.com',
#                               'search_path': '/', 'priority': 3, 'type': 'myntra'})
#         if official_url:
#             platforms.insert(0, {'name': 'Official Site', 'base_url': official_url,
#                                  'search_path': '', 'priority': 0,
#                                  'type': 'official', 'direct_url': official_url})

#         # MCTS-guided scraping
#         out += f"🌳 MCTS ({MCTS_SIMULATIONS} simulations) deciding visit order...\n"
#         results, visited = run_mcts_scraping(platforms, product, MCTS_SIMULATIONS)
#         results = {k: v for k, v in results.items() if _valid(v.get('price'), floor)}
#         out += f"📊 Visited   : {' → '.join(visited)}\n"
#         out += f"✅ Direct hit: {len(results)}/{len(platforms)}\n"

#         # Per-platform Bing fallback for every platform that failed
#         failed = [p for p in platforms if p['name'] not in results]
#         if failed:
#             out += f"⚠️  {len(failed)} platform(s) blocked → Bing snippet fallback...\n"
#             for p in failed:
#                 bd = _bing_platform(product, p['name'], floor)
#                 if bd:
#                     results[p['name']] = bd
#                     out += f"   ✅ {p['name']}: ₹{bd['price']:,.0f} via Bing\n"
#                 else:
#                     out += f"   ❌ {p['name']}: no price found\n"

#         if results:
#             out += f"\n{'='*70}\n\n"
#             return _fmt_results(out, results, product)

#         return out + _fmt_none('', product)

#     except Exception as e:
#         return f"❌ Error: {str(e)}"


# # ──────────────────────────────────────────────────────────────────
# # Amazon.in scraper
# # ──────────────────────────────────────────────────────────────────
# def _scrape_amazon(product: str, floor: int):
#     q   = product.replace(' ', '+')
#     url = f"https://www.amazon.in/s?k={q}"
#     try:
#         s = _session("https://www.amazon.in/")
#         try:
#             s.get("https://www.amazon.in/", timeout=5)
#             time.sleep(0.5)
#         except Exception:
#             pass
#         r = s.get(url, timeout=REQUEST_TIMEOUT)
#         if r.status_code != 200:
#             return None

#         soup  = BeautifulSoup(r.text, 'html.parser')
#         cards = soup.select('div[data-component-type="s-search-result"]')

#         for card in cards[:15]:
#             # Skip ads
#             if card.get('data-adfeedbackdetails') or \
#                card.select_one('[aria-label*="Sponsored"]'):
#                 continue
#             price = None
#             for sel in ['span.a-price span.a-offscreen',
#                         'span.a-price-whole',
#                         '.a-price .a-offscreen',
#                         'span.a-color-price']:
#                 el = card.select_one(sel)
#                 if el:
#                     p = _parse_inr(el.get_text())
#                     if p and _valid(p, floor):
#                         price = p
#                         break
#             if not price:
#                 continue
#             title_el = card.select_one('h2 a span')
#             title    = title_el.get_text(strip=True)[:80] if title_el else product
#             rat_el   = card.select_one('span.a-icon-alt')
#             rating   = _parse_rating(rat_el.get_text()) if rat_el else None
#             rev_el   = card.select_one('span.a-size-base.s-underline-text')
#             reviews  = rev_el.get_text(strip=True) if rev_el else None
#             link_el  = card.select_one('h2 a')
#             purl     = ("https://www.amazon.in" + link_el['href']) if link_el else url
#             return {'price': price, 'rating': rating, 'reviews': reviews,
#                     'title': title, 'url': purl,
#                     'currency': 'INR', 'source': 'amazon.in'}

#         # Text-scan fallback
#         prices = _all_prices(soup.get_text(), floor)
#         best   = _median(prices)
#         if best:
#             return {'price': best, 'rating': None, 'reviews': None,
#                     'title': product, 'url': url,
#                     'currency': 'INR', 'source': 'amazon.in (scan)'}
#     except Exception:
#         pass
#     return None


# # ──────────────────────────────────────────────────────────────────
# # Flipkart scraper — 4 strategies
# # ──────────────────────────────────────────────────────────────────
# def _scrape_flipkart(product: str, floor: int):
#     q   = product.replace(' ', '+')
#     url = f"https://www.flipkart.com/search?q={q}"
#     try:
#         s = _session("https://www.flipkart.com/")
#         s.cookies.set('T', '0', domain='.flipkart.com')
#         r = s.get(url, timeout=REQUEST_TIMEOUT)
#         if r.status_code != 200:
#             return None

#         soup = BeautifulSoup(r.text, 'html.parser')

#         # Strategy 1: known product card containers
#         card_selectors = [
#             'div._1AtVbE', 'div.cPHDOP', 'div.col.col-7-12',
#             'div._13oc-S', 'div._2kHMtA', 'div._4ddWXP',
#             'li.col', 'div[data-id]',
#         ]
#         cards = []
#         for csel in card_selectors:
#             found = soup.select(csel)
#             if len(found) > 1:
#                 cards = found
#                 break

#         # Price classes Flipkart uses (changes often — cover all known)
#         price_classes = [
#             'div.Nx9bqj', 'div.Nx9bqj.CxhGGd',   # 2024-2025
#             'div._30jeq3', 'div._30jeq3._1_WHN1',  # 2022-2023
#             'div._1vC4OE', 'div._3qQ9m1',           # older
#             'div.UOCQB1',  'div.hl05eU',
#         ]

#         for card in cards[:15]:
#             price = None

#             # Try known price class selectors
#             for psel in price_classes:
#                 el = card.select_one(psel)
#                 if el:
#                     p = _parse_inr(el.get_text())
#                     if p and _valid(p, floor):
#                         price = p
#                         break

#             # Strategy 2: any element whose text starts with ₹
#             if not price:
#                 for el in card.find_all(string=re.compile(r'₹')):
#                     p = _parse_inr(str(el))
#                     if p and _valid(p, floor):
#                         price = p
#                         break

#             if not price:
#                 continue

#             # Title
#             title = product
#             for tsel in ['div.KzDlHZ', 'div._4rR01T', 'a.s1Q9rs',
#                          'div._2WkVRV', 'a.IRpwTa', 'p.txtnm']:
#                 el = card.select_one(tsel)
#                 if el:
#                     title = el.get_text(strip=True)[:80]
#                     break

#             # Rating
#             rating = None
#             for rsel in ['div.XQDdHH', 'div._3LWZlK', 'span._2_R_DZ']:
#                 el = card.select_one(rsel)
#                 if el:
#                     rating = _parse_rating(el.get_text())
#                     if rating:
#                         break

#             # Link
#             link_el = (card.select_one('a[href*="/p/"]') or
#                        card.select_one('a[href*="flipkart.com/"]') or
#                        card.select_one('a[href]'))
#             if link_el and link_el.get('href'):
#                 href = link_el['href']
#                 purl = href if href.startswith('http') \
#                        else "https://www.flipkart.com" + href
#             else:
#                 purl = url

#             return {'price': price, 'rating': rating, 'reviews': None,
#                     'title': title, 'url': purl,
#                     'currency': 'INR', 'source': 'flipkart.com'}

#         # Strategy 3: full-page ₹ text scan (floor rejects junk)
#         prices = _all_prices(soup.get_text(), floor)
#         best   = _median(prices)
#         if best:
#             return {'price': best, 'rating': None, 'reviews': None,
#                     'title': product, 'url': url,
#                     'currency': 'INR', 'source': 'flipkart.com (scan)'}

#     except Exception:
#         pass
#     return None


# # ──────────────────────────────────────────────────────────────────
# # Myntra — JSON API (fashion/lifestyle only)
# # ──────────────────────────────────────────────────────────────────
# def _scrape_myntra(product: str, floor: int):
#     q   = product.replace(' ', '%20')
#     url = f"https://www.myntra.com/gateway/v2/search/{q}?rawQuery={q}&p=1&rows=8"
#     try:
#         s = _session("https://www.myntra.com/")
#         s.headers.update({"X-Myntra-Abtest": "false"})
#         r = s.get(url, timeout=REQUEST_TIMEOUT)
#         if r.status_code == 200:
#             data  = r.json()
#             prods = (data.get('searchData', {})
#                          .get('results', {})
#                          .get('products', [])
#                      or data.get('products', []))
#             for p in prods[:10]:
#                 po    = p.get('priceV3') or p.get('price') or {}
#                 price = None
#                 if isinstance(po, dict):
#                     raw = po.get('discounted') or po.get('mrp')
#                     if raw:
#                         price = float(str(raw).replace(',', ''))
#                 elif isinstance(p.get('discountedPrice'), (int, float)):
#                     price = float(p['discountedPrice'])
#                 elif isinstance(p.get('price'), (int, float)):
#                     price = float(p['price'])
#                 if not price or not _valid(price, floor):
#                     continue
#                 title   = p.get('productName') or product
#                 slug    = p.get('landingPageUrl', '')
#                 purl    = f"https://www.myntra.com/{slug}" if slug \
#                           else f"https://www.myntra.com/{product.replace(' ', '-')}"
#                 return {'price': float(price),
#                         'rating': float(p['rating']) if p.get('rating') else None,
#                         'reviews': str(p.get('ratingCount', '') or ''),
#                         'title': str(title)[:80], 'url': purl,
#                         'currency': 'INR', 'source': 'myntra.com'}
#     except Exception:
#         pass
#     return None


# # ──────────────────────────────────────────────────────────────────
# # Official brand site
# # ──────────────────────────────────────────────────────────────────
# def _scrape_official(platform: dict, product: str, floor: int):
#     url = platform.get('direct_url') or platform.get('base_url')
#     if not url:
#         return None
#     try:
#         s    = _session()
#         r    = s.get(url, timeout=REQUEST_TIMEOUT)
#         if r.status_code != 200:
#             return None
#         soup = BeautifulSoup(r.text, 'html.parser')
#         price = None
#         el    = soup.find('span', {'itemprop': 'price'})
#         if el:
#             price = _parse_inr(el.get('content', '') or el.get_text())
#         if not price or not _valid(price, floor):
#             og = soup.find('meta', {'property': 'product:price:amount'})
#             if og:
#                 try:
#                     price = float(og.get('content', '0').replace(',', ''))
#                 except Exception:
#                     pass
#         if not price or not _valid(price, floor):
#             price = _median(_all_prices(soup.get_text(), floor))
#         if price and _valid(price, floor):
#             og_t  = soup.find('meta', {'property': 'og:title'})
#             title = og_t.get('content', '') if og_t else ''
#             if not title:
#                 h1    = soup.find('h1')
#                 title = h1.get_text(strip=True) if h1 else product
#             rat_el = soup.find('span', {'itemprop': 'ratingValue'})
#             rating = _parse_rating(rat_el.get_text()) if rat_el else None
#             return {'price': price, 'rating': rating, 'reviews': None,
#                     'title': title[:80], 'url': url,
#                     'currency': 'INR', 'source': 'official site'}
#     except Exception:
#         pass
#     return None


# def _scrape_generic(platform: dict, product: str, floor: int):
#     q   = product.replace(' ', '+')
#     url = platform['base_url'] + platform['search_path'] + q
#     try:
#         r = requests.get(url, headers={"User-Agent": random.choice(_UA)},
#                          timeout=REQUEST_TIMEOUT)
#         if r.status_code != 200:
#             return None
#         price = _median(_all_prices(
#             BeautifulSoup(r.text, 'html.parser').get_text(), floor))
#         if price:
#             return {'price': price, 'rating': None, 'reviews': None,
#                     'title': product, 'url': url,
#                     'currency': 'INR', 'source': 'scraped'}
#     except Exception:
#         pass
#     return None


# # ──────────────────────────────────────────────────────────────────
# # Platform dispatcher (called by web_scraping_mcts.py)
# # ──────────────────────────────────────────────────────────────────
# def scrape_platform_real_time(platform: dict, product_name: str):
#     ptype = platform.get('type', 'generic')
#     floor = _floor(product_name)
#     try:
#         if   ptype == 'amazon':   return _scrape_amazon(product_name, floor)
#         elif ptype == 'flipkart': return _scrape_flipkart(product_name, floor)
#         elif ptype == 'myntra':   return _scrape_myntra(product_name, floor)
#         elif ptype == 'official': return _scrape_official(platform, product_name, floor)
#         else:                     return _scrape_generic(platform, product_name, floor)
#     except Exception:
#         return None


# # ──────────────────────────────────────────────────────────────────
# # Bing per-platform fallback
# # ──────────────────────────────────────────────────────────────────
# _PLATFORM_DOMAINS = {
#     'Amazon India': 'amazon.in',
#     'Flipkart':     'flipkart.com',
#     'Myntra':       'myntra.com',
# }


# def _bing_platform(product: str, platform_name: str, floor: int):
#     """Search Bing: '{product} price site:{domain}' and extract ₹."""
#     domain = _PLATFORM_DOMAINS.get(platform_name)
#     if not domain:
#         return None
#     try:
#         q   = f"{product} price site:{domain}".replace(' ', '+')
#         url = f"https://www.bing.com/search?q={q}&mkt=en-IN&setlang=en-IN"
#         s   = _session("https://www.bing.com/")
#         r   = s.get(url, timeout=8)
#         if r.status_code != 200:
#             return None
#         soup = BeautifulSoup(r.text, 'html.parser')
#         for res in soup.select('li.b_algo')[:8]:
#             prices = _all_prices(res.get_text(), floor)
#             best   = _median(prices)
#             if best:
#                 link_el  = res.select_one('h2 a')
#                 title_el = res.select_one('h2 a')
#                 title    = title_el.get_text(strip=True)[:80] if title_el else product
#                 href     = link_el.get('href', '') if link_el else \
#                            f"https://www.{domain}/search?q={product.replace(' ', '+')}"
#                 return {'price': best, 'rating': None, 'reviews': None,
#                         'title': title, 'url': href,
#                         'currency': 'INR', 'source': f'bing→{domain}'}
#         return None
#     except Exception:
#         return None


# # ──────────────────────────────────────────────────────────────────
# # extract_product_name  — strips ALL filler, cleans punctuation
# # ──────────────────────────────────────────────────────────────────
# def extract_product_name(query: str) -> str:
#     """
#     Strips filler words AND trailing punctuation from each word.
#     Works correctly even when query contains 'Platforms.' with a dot.

#     Examples:
#       "compare HP Laptop prices on various Platforms." → "hp laptop"
#       "compare hp laptop prices on various platforms"  → "hp laptop"
#       "iPhone 15 price on amazon and flipkart"         → "iphone 15"
#     """
#     STOP = {
#         'compare','comparing','buy','purchase','find','search','best',
#         'price','prices','pricing','cost','costs','rate','rates',
#         'on','in','at','of','to','for','a','an','the',
#         'different','platforms','platform','sites','site','store',
#         'stores','check','over','across','various','multiple',
#         'show','get','me','give','tell','list','top',
#         'cheap','cheaper','cheapest','lowest','affordable',
#         'review','reviews','rating','ratings',
#         'official','website','from','http','https',
#         'online','shopping','india','indian',
#         'and','or','with','all','do','i','is','are','can',
#         'real','time','live','now','today','current','latest',
#         'please','want','need','help','know',
#         'amazon','flipkart','myntra','meesho','nykaa',
#         'croma','reliance','tatacliq','snapdeal','paytm',
#     }
#     # Remove URLs first
#     query = re.sub(r'https?://\S+', '', query)
#     # Split, strip punctuation from each token, filter STOP words
#     words   = query.lower().split()
#     cleaned = []
#     for w in words:
#         w = re.sub(r'^[^a-z0-9]+|[^a-z0-9]+$', '', w)  # strip non-alnum edges
#         if w and w not in STOP and len(w) > 1:
#             cleaned.append(w)
#     return ' '.join(cleaned).strip()


# def extract_official_url(query: str):
#     m = re.search(r'https?://[^\s]+', query)
#     return m.group(0).rstrip('.,)') if m else None


# # ──────────────────────────────────────────────────────────────────
# # Output formatters
# # ──────────────────────────────────────────────────────────────────
# def _fmt_results(output: str, results: dict, product: str) -> str:
#     sorted_r = sorted(results.items(), key=lambda x: x[1]['price'])

#     output += f"{'PLATFORM':<18} {'PRICE (INR)':>12}  {'RATING':>8}  SOURCE\n"
#     output += f"{'-'*18} {'-'*12}  {'-'*8}  {'-'*24}\n"

#     for name, data in sorted_r:
#         price  = f"₹{data['price']:,.0f}"
#         rating = f"{data['rating']}/5 ⭐" if data.get('rating') else "N/A"
#         source = data.get('source', 'scraped')[:24]
#         output += f"{name:<18} {price:>12}  {rating:>8}  {source}\n"

#     best = sorted_r[0]
#     bd   = best[1]
#     output += f"\n{'='*70}\n"
#     output += f"✅ BEST PRICE  : {best[0]}  →  ₹{bd['price']:,.0f}\n"
#     if bd.get('rating'):
#         output += f"⭐ RATING       : {bd['rating']}/5\n"
#     if bd.get('reviews'):
#         output += f"💬 REVIEWS      : {bd['reviews']}\n"
#     output += f"🔗 BUY HERE     : {bd.get('url', 'N/A')}\n"
#     output += f"{'='*70}\n\n"

#     if len(sorted_r) > 1:
#         output += "🔗 All Links:\n"
#         for name, data in sorted_r:
#             if data.get('url'):
#                 note = "  [bing fallback]" if 'bing' in data.get('source', '') else ''
#                 output += f"  • {name:<16}: {data['url']}{note}\n"
#         output += "\n"

#     output += "📡 Prices scraped live — zero AI-generated values.\n"
#     output += "⚠️  Prices change — verify on platform before purchase.\n"
#     return output


# def _fmt_none(output: str, product: str) -> str:
#     q = product.replace(' ', '+')
#     output += "\n❌ Could not fetch live prices from any source.\n\n"
#     output += "🔍 Search manually:\n"
#     output += f"  • Amazon.in  : https://www.amazon.in/s?k={q}\n"
#     output += f"  • Flipkart   : https://www.flipkart.com/search?q={q}\n"
#     output += f"  • Myntra     : https://www.myntra.com/{product.replace(' ','-')}\n"
#     return output


# # Legacy aliases kept for web_scraping_mcts.py
# def format_results(out, results, product_name=''):
#     return _fmt_results(out, results, product_name)

# def format_no_results(out, product_name):
#     return _fmt_none(out, product_name)
# #########################################################################
# backend/tools/ecommerce.py
# """
# Real-time e-commerce price scraper — India.

# Sources tried for EVERY query:
#   1. Amazon.in       — CSS selectors + full-page text scan fallback
#   2. Flipkart        — multi-strategy CSS + ₹ string scan + text scan
#   3. Myntra          — JSON API (only for fashion/lifestyle products)
#   4. Official Site   — auto-detected from brand name OR user-supplied URL

# Bing search snippet fallback per platform when direct scraping blocked.
# ZERO LLM-generated prices.
# """

# import requests
# import re
# import time
# import random
# from bs4 import BeautifulSoup
# from config import REQUEST_TIMEOUT, MCTS_SIMULATIONS
# from mcts.web_scraping_mcts import run_mcts_scraping


# # ──────────────────────────────────────────────────────────────────
# # Brand → official site mapping
# # Auto-detected from product name — no URL needed from user
# # ──────────────────────────────────────────────────────────────────
# BRAND_SITES = {
#     # Laptops / Computers
#     "iphone":     "https://www.apple.com/in/shop/buy-iphone",
#     "macbook":    "https://www.apple.com/in/shop/buy-mac",
#     "hp":         "https://www.hp.com/in-en/shop/laptops.html",
#     "dell":       "https://www.dell.com/en-in/cat/laptops",
#     "lenovo":     "https://www.lenovo.com/in/en/laptops/",
#     "asus":       "https://www.asus.com/in/laptops/",
#     "acer":       "https://store.acer.com/en-in/laptops",
#     "apple":      "https://www.apple.com/in/",
#     "msi":        "https://in.msi.com/Laptops",
#     "lg":         "https://www.lg.com/in/laptops",
#     "microsoft":  "https://www.microsoft.com/en-in/surface",
#     # Phones
#     "samsung":    "https://www.samsung.com/in/smartphones/",
#     "oneplus":    "https://www.oneplus.in/smartphones",
#     "realme":     "https://www.realme.com/in/smartphones",
#     "redmi":      "https://www.mi.com/in/phones",
#     "xiaomi":     "https://www.mi.com/in/phones",
#     "mi ":        "https://www.mi.com/in/phones",
#     "poco":       "https://www.poco.in/mobiles",
#     "vivo":       "https://www.vivo.com/in/products/smartphones",
#     "oppo":       "https://www.oppo.com/in/smartphones/",
#     "motorola":   "https://www.motorola.in/smartphones",
#     "nokia":      "https://www.nokia.com/phones/en_in/",
#     "iqoo":       "https://www.iqoo.com/in/phone.html",
#     # Audio
#     "boat":       "https://www.boat-lifestyle.com/collections/headphones",
#     "jbl":        "https://in.jbl.com/headphones/",
#     "sony":       "https://www.sony.co.in/en/category/headphone",
#     "bose":       "https://www.bose.in/en_in/products/headphones/",
#     "sennheiser": "https://www.sennheiser.com/en-in/",
#     "skullcandy": "https://www.skullcandy.in/",
#     "noise":      "https://www.gonoise.com/",
#     "zebronics":  "https://www.zebronics.com/",
#     # Watches
#     "fastrack":   "https://www.fastrack.in/",
#     "titan":      "https://www.titan.co.in/",
#     "fossil":     "https://www.fossil.com/en-in/",
#     "garmin":     "https://www.garmin.com/en-IN/",
#     "fitbit":     "https://www.fitbit.com/in/home",
#     # TVs
#     "tcl":        "https://www.tcl.com/in/en/televisions.html",
#     "mi tv":      "https://www.mi.com/in/tv",
#     # Cameras
#     "canon":      "https://in.canon/en/consumer/cameras",
#     "nikon":      "https://www.nikonindia.com/cameras/",
#     "fujifilm":   "https://www.fujifilmgfx.com/in/products/cameras/",
#     "gopro":      "https://gopro.com/en/in/",
#     # Appliances
#     "bosch":      "https://www.bosch-home.com/in/",
#     "whirlpool":  "https://www.whirlpoolindia.com/",
#     "haier":      "https://www.haier.com/in/",
#     "voltas":     "https://www.voltas.com/",
# }


# def _get_brand_site(product: str) -> tuple:
#     """
#     Auto-detect official brand site from product name.
#     Returns (brand_name, url) or (None, None).
#     """
#     p = product.lower()
#     for brand, url in BRAND_SITES.items():
#         if brand in p:
#             return brand.title(), url
#     return None, None


# # ──────────────────────────────────────────────────────────────────
# # Category price floors
# # ──────────────────────────────────────────────────────────────────
# CATEGORY_FLOORS = {
#     "macbook": 80000, "imac": 80000,
#     "laptop": 15000,  "notebook": 15000, "chromebook": 12000,
#     "desktop": 15000, "computer": 10000,
#     "iphone": 40000,
#     "smartphone": 5000, "mobile": 3000, "phone": 3000,
#     "oneplus": 15000, "samsung": 3000, "pixel": 30000,
#     "redmi": 5000, "realme": 5000, "poco": 7000,
#     "vivo": 5000, "oppo": 5000, "motorola": 7000,
#     "ipad": 30000, "tablet": 5000,
#     "smart tv": 10000, "television": 10000, "tv": 8000,
#     "oled": 30000, "qled": 25000,
#     "refrigerator": 10000, "fridge": 10000,
#     "washing machine": 10000, "washer": 10000,
#     "air conditioner": 15000, "microwave": 5000, "oven": 5000,
#     "headphone": 500, "earphone": 200, "earbuds": 300,
#     "speaker": 500, "soundbar": 3000,
#     "camera": 5000, "dslr": 20000, "mirrorless": 30000,
#     "smartwatch": 2000, "watch": 500,
#     "keyboard": 300, "mouse": 200, "monitor": 5000,
#     "printer": 3000, "router": 1000,
#     "hard disk": 2000, "ssd": 1500,
#     "gpu": 15000, "graphics card": 15000,
#     "mixer": 1500, "grinder": 500, "iron": 500,
#     "trimmer": 500, "shaver": 500, "fan": 500,
#     "cooler": 2000, "heater": 1000, "purifier": 3000,
#     "default": 200,
# }
# PRICE_MAX = 500000

# MYNTRA_SELLS = {
#     "watch","watches","shoe","shoes","sneaker","sandal","bag","bags",
#     "backpack","handbag","tshirt","shirt","dress","jeans","trouser",
#     "kurta","saree","jacket","coat","hoodie","sweater","sunglasses",
#     "earring","necklace","bracelet","perfume","lipstick","moisturizer",
#     "trimmer","shaver","earbuds","headphone","smartwatch",
#     "fastrack","titan","boat","noise","zebronics","skullcandy",
# }


# def _floor(product: str) -> int:
#     p = product.lower()
#     for kw, f in CATEGORY_FLOORS.items():
#         if kw in p:
#             return f
#     return CATEGORY_FLOORS["default"]


# def _valid(price, floor: int) -> bool:
#     return price is not None and floor <= float(price) <= PRICE_MAX


# def _myntra_ok(product: str) -> bool:
#     p = product.lower()
#     return any(cat in p for cat in MYNTRA_SELLS)


# # ──────────────────────────────────────────────────────────────────
# # Session factory
# # ──────────────────────────────────────────────────────────────────
# _UA = [
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
#     "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) "
#     "Gecko/20100101 Firefox/124.0",
#     "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 "
#     "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
# ]


# def _session(ref="https://www.google.co.in/"):
#     s = requests.Session()
#     s.headers.update({
#         "User-Agent":                random.choice(_UA),
#         "Accept-Language":           "en-IN,en;q=0.9,hi;q=0.8",
#         "Accept":                    "text/html,application/xhtml+xml,"
#                                      "application/xml;q=0.9,image/avif,"
#                                      "image/webp,*/*;q=0.8",
#         "Accept-Encoding":           "gzip, deflate, br",
#         "Referer":                   ref,
#         "DNT":                       "1",
#         "Connection":                "keep-alive",
#         "Upgrade-Insecure-Requests": "1",
#     })
#     return s


# # ──────────────────────────────────────────────────────────────────
# # Parsers
# # ──────────────────────────────────────────────────────────────────
# def _parse_inr(text: str):
#     if not text:
#         return None
#     text = re.sub(r'[,\xa0\u200b]', '', str(text)).strip()
#     for pat in [r'₹\s*([0-9]+(?:\.[0-9]{1,2})?)',
#                 r'Rs\.?\s*([0-9]+(?:\.[0-9]{1,2})?)',
#                 r'INR\s*([0-9]+(?:\.[0-9]{1,2})?)']:
#         m = re.search(pat, text, re.IGNORECASE)
#         if m:
#             try:
#                 return float(m.group(1))
#             except Exception:
#                 continue
#     return None


# def _parse_rating(text: str):
#     if not text:
#         return None
#     m = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*(?:out\s*of\s*5|/5|stars?)?',
#                   str(text), re.IGNORECASE)
#     if m:
#         try:
#             v = float(m.group(1))
#             if 0.0 < v <= 5.0:
#                 return round(v, 1)
#         except Exception:
#             pass
#     return None


# def _all_prices(text: str, floor: int) -> list:
#     text  = re.sub(r'[,]', '', str(text))
#     found = []
#     for pat in [r'₹\s*([0-9]+(?:\.[0-9]{1,2})?)',
#                 r'Rs\.?\s*([0-9]+(?:\.[0-9]{1,2})?)',
#                 r'INR\s*([0-9]+(?:\.[0-9]{1,2})?)']:
#         for m in re.findall(pat, text, re.IGNORECASE):
#             try:
#                 v = float(m)
#                 if _valid(v, floor):
#                     found.append(v)
#             except Exception:
#                 continue
#     return sorted(set(found))


# def _median(prices: list):
#     if not prices:
#         return None
#     prices  = sorted(prices)
#     trimmed = prices[:max(1, int(len(prices) * 0.8))]
#     return trimmed[len(trimmed) // 2]


# # ──────────────────────────────────────────────────────────────────
# # Main handler
# # ──────────────────────────────────────────────────────────────────
# def handle_ecommerce(query: str) -> str:
#     try:
#         product      = extract_product_name(query)
#         official_url = extract_official_url(query)
#         floor        = _floor(product)
#         use_myntra   = _myntra_ok(product)

#         # Auto-detect brand official site if no URL given
#         auto_brand, auto_site = _get_brand_site(product)
#         if not official_url and auto_site:
#             official_url = auto_site

#         out  = f"🔍 Real-Time Price Comparison — India\n{'='*70}\n"
#         out += f"🛍️  Product      : {product.title()}\n"
#         out += f"💰 Price floor   : ₹{floor:,} (junk values rejected below this)\n"

#         srcs = "Amazon.in | Flipkart"
#         if use_myntra:
#             srcs += " | Myntra"
#         if official_url:
#             brand_label = auto_brand or "Official Site"
#             srcs += f" | {brand_label} Official"
#         out += f"📡 Sources       : {srcs}\n\n"

#         # ── Build platform list ───────────────────────────────────
#         platforms = [
#             {'name': 'Amazon India', 'base_url': 'https://www.amazon.in',
#              'search_path': '/s?k=', 'priority': 1, 'type': 'amazon'},
#             {'name': 'Flipkart',     'base_url': 'https://www.flipkart.com',
#              'search_path': '/search?q=', 'priority': 2, 'type': 'flipkart'},
#         ]
#         if use_myntra:
#             platforms.append(
#                 {'name': 'Myntra', 'base_url': 'https://www.myntra.com',
#                  'search_path': '/', 'priority': 3, 'type': 'myntra'})
#         if official_url:
#             brand_label = auto_brand or "Official Site"
#             platforms.insert(0, {
#                 'name':       f'{brand_label} Official',
#                 'base_url':   official_url,
#                 'search_path': '',
#                 'priority':   0,
#                 'type':       'official',
#                 'direct_url': official_url,
#             })

#         # ── MCTS-guided scraping ──────────────────────────────────
#         out += f"🌳 MCTS ({MCTS_SIMULATIONS} simulations) deciding visit order...\n"
#         results, visited = run_mcts_scraping(platforms, product, MCTS_SIMULATIONS)
#         results = {k: v for k, v in results.items() if _valid(v.get('price'), floor)}
#         out += f"📊 Visited   : {' → '.join(visited)}\n"
#         out += f"✅ Direct hit: {len(results)}/{len(platforms)}\n"

#         # ── Per-platform Bing fallback ────────────────────────────
#         failed = [p for p in platforms if p['name'] not in results]
#         if failed:
#             out += f"⚠️  {len(failed)} platform(s) blocked → Bing fallback...\n"
#             for p in failed:
#                 bd = _bing_platform(product, p['name'], floor,
#                                     p.get('base_url', ''))
#                 if bd:
#                     results[p['name']] = bd
#                     out += f"   ✅ {p['name']}: ₹{bd['price']:,.0f} via Bing\n"
#                 else:
#                     out += f"   ❌ {p['name']}: no price found\n"

#         if results:
#             out += f"\n{'='*70}\n\n"
#             return _fmt_results(out, results, product)

#         return out + _fmt_none('', product)

#     except Exception as e:
#         return f"❌ Error: {str(e)}"


# # ──────────────────────────────────────────────────────────────────
# # Amazon.in
# # ──────────────────────────────────────────────────────────────────
# def _scrape_amazon(product: str, floor: int):
#     q   = product.replace(' ', '+')
#     url = f"https://www.amazon.in/s?k={q}"
#     try:
#         s = _session("https://www.amazon.in/")
#         try:
#             s.get("https://www.amazon.in/", timeout=5)
#             time.sleep(0.5)
#         except Exception:
#             pass
#         r = s.get(url, timeout=REQUEST_TIMEOUT)
#         if r.status_code != 200:
#             return None
#         soup  = BeautifulSoup(r.text, 'html.parser')
#         cards = soup.select('div[data-component-type="s-search-result"]')
#         for card in cards[:15]:
#             if card.get('data-adfeedbackdetails') or \
#                card.select_one('[aria-label*="Sponsored"]'):
#                 continue
#             price = None
#             for sel in ['span.a-price span.a-offscreen',
#                         'span.a-price-whole',
#                         '.a-price .a-offscreen',
#                         'span.a-color-price']:
#                 el = card.select_one(sel)
#                 if el:
#                     p = _parse_inr(el.get_text())
#                     if p and _valid(p, floor):
#                         price = p
#                         break
#             if not price:
#                 continue
#             title_el = card.select_one('h2 a span')
#             title    = title_el.get_text(strip=True)[:80] if title_el else product
#             rat_el   = card.select_one('span.a-icon-alt')
#             rating   = _parse_rating(rat_el.get_text()) if rat_el else None
#             rev_el   = card.select_one('span.a-size-base.s-underline-text')
#             reviews  = rev_el.get_text(strip=True) if rev_el else None
#             link_el  = card.select_one('h2 a')
#             purl     = ("https://www.amazon.in" + link_el['href']) if link_el else url
#             return {'price': price, 'rating': rating, 'reviews': reviews,
#                     'title': title, 'url': purl,
#                     'currency': 'INR', 'source': 'amazon.in'}
#         # text scan fallback
#         prices = _all_prices(soup.get_text(), floor)
#         best   = _median(prices)
#         if best:
#             return {'price': best, 'rating': None, 'reviews': None,
#                     'title': product, 'url': url,
#                     'currency': 'INR', 'source': 'amazon.in (scan)'}
#     except Exception:
#         pass
#     return None


# # ──────────────────────────────────────────────────────────────────
# # Flipkart — multi-strategy
# # ──────────────────────────────────────────────────────────────────
# def _scrape_flipkart(product: str, floor: int):
#     q   = product.replace(' ', '+')
#     url = f"https://www.flipkart.com/search?q={q}"
#     try:
#         s = _session("https://www.flipkart.com/")
#         s.cookies.set('T', '0', domain='.flipkart.com')
#         r = s.get(url, timeout=REQUEST_TIMEOUT)
#         if r.status_code != 200:
#             return None
#         soup = BeautifulSoup(r.text, 'html.parser')

#         # Find product cards
#         cards = []
#         for csel in ['div._1AtVbE', 'div.cPHDOP', 'div.col.col-7-12',
#                      'div._13oc-S', 'div._2kHMtA', 'div._4ddWXP',
#                      'li.col', 'div[data-id]']:
#             found = soup.select(csel)
#             if len(found) > 1:
#                 cards = found
#                 break

#         for card in cards[:15]:
#             price = None
#             # Known price CSS classes
#             for psel in ['div.Nx9bqj', 'div.Nx9bqj.CxhGGd',
#                          'div._30jeq3', 'div._30jeq3._1_WHN1',
#                          'div._1vC4OE', 'div._3qQ9m1',
#                          'div.UOCQB1',  'div.hl05eU']:
#                 el = card.select_one(psel)
#                 if el:
#                     p = _parse_inr(el.get_text())
#                     if p and _valid(p, floor):
#                         price = p
#                         break
#             # Scan for ₹ in card text
#             if not price:
#                 for el in card.find_all(string=re.compile(r'₹')):
#                     p = _parse_inr(str(el))
#                     if p and _valid(p, floor):
#                         price = p
#                         break
#             if not price:
#                 continue
#             title = product
#             for tsel in ['div.KzDlHZ', 'div._4rR01T', 'a.s1Q9rs',
#                          'div._2WkVRV', 'a.IRpwTa', 'p.txtnm']:
#                 el = card.select_one(tsel)
#                 if el:
#                     title = el.get_text(strip=True)[:80]
#                     break
#             rating = None
#             for rsel in ['div.XQDdHH', 'div._3LWZlK', 'span._2_R_DZ']:
#                 el = card.select_one(rsel)
#                 if el:
#                     rating = _parse_rating(el.get_text())
#                     if rating:
#                         break
#             link_el = (card.select_one('a[href*="/p/"]') or
#                        card.select_one('a[href*="flipkart.com/"]') or
#                        card.select_one('a[href]'))
#             if link_el and link_el.get('href'):
#                 href = link_el['href']
#                 purl = href if href.startswith('http') \
#                        else "https://www.flipkart.com" + href
#             else:
#                 purl = url
#             return {'price': price, 'rating': rating, 'reviews': None,
#                     'title': title, 'url': purl,
#                     'currency': 'INR', 'source': 'flipkart.com'}

#         # Full page text scan
#         prices = _all_prices(soup.get_text(), floor)
#         best   = _median(prices)
#         if best:
#             return {'price': best, 'rating': None, 'reviews': None,
#                     'title': product, 'url': url,
#                     'currency': 'INR', 'source': 'flipkart.com (scan)'}
#     except Exception:
#         pass
#     return None


# # ──────────────────────────────────────────────────────────────────
# # Myntra — JSON API (fashion only)
# # ──────────────────────────────────────────────────────────────────
# def _scrape_myntra(product: str, floor: int):
#     q   = product.replace(' ', '%20')
#     url = f"https://www.myntra.com/gateway/v2/search/{q}?rawQuery={q}&p=1&rows=8"
#     try:
#         s = _session("https://www.myntra.com/")
#         s.headers.update({"X-Myntra-Abtest": "false"})
#         r = s.get(url, timeout=REQUEST_TIMEOUT)
#         if r.status_code == 200:
#             data  = r.json()
#             prods = (data.get('searchData', {})
#                          .get('results', {})
#                          .get('products', [])
#                      or data.get('products', []))
#             for p in prods[:10]:
#                 po    = p.get('priceV3') or p.get('price') or {}
#                 price = None
#                 if isinstance(po, dict):
#                     raw = po.get('discounted') or po.get('mrp')
#                     if raw:
#                         price = float(str(raw).replace(',', ''))
#                 elif isinstance(p.get('discountedPrice'), (int, float)):
#                     price = float(p['discountedPrice'])
#                 elif isinstance(p.get('price'), (int, float)):
#                     price = float(p['price'])
#                 if not price or not _valid(price, floor):
#                     continue
#                 title = p.get('productName') or product
#                 slug  = p.get('landingPageUrl', '')
#                 purl  = f"https://www.myntra.com/{slug}" if slug \
#                         else f"https://www.myntra.com/{product.replace(' ','-')}"
#                 return {'price': float(price),
#                         'rating': float(p['rating']) if p.get('rating') else None,
#                         'reviews': str(p.get('ratingCount', '') or ''),
#                         'title': str(title)[:80], 'url': purl,
#                         'currency': 'INR', 'source': 'myntra.com'}
#     except Exception:
#         pass
#     return None


# # ──────────────────────────────────────────────────────────────────
# # Official brand site — schema.org / OG / text scan
# # ──────────────────────────────────────────────────────────────────
# def _scrape_official(platform: dict, product: str, floor: int):
#     url = platform.get('direct_url') or platform.get('base_url')
#     if not url:
#         return None
#     try:
#         s = _session()
#         r = s.get(url, timeout=REQUEST_TIMEOUT)
#         if r.status_code != 200:
#             return None
#         soup  = BeautifulSoup(r.text, 'html.parser')
#         price = None
#         # schema.org
#         el = soup.find('span', {'itemprop': 'price'})
#         if el:
#             price = _parse_inr(el.get('content', '') or el.get_text())
#         # Open Graph
#         if not price or not _valid(price, floor):
#             og = soup.find('meta', {'property': 'product:price:amount'})
#             if og:
#                 try:
#                     price = float(og.get('content', '0').replace(',', ''))
#                 except Exception:
#                     pass
#         # Text scan
#         if not price or not _valid(price, floor):
#             price = _median(_all_prices(soup.get_text(), floor))
#         if price and _valid(price, floor):
#             og_t  = soup.find('meta', {'property': 'og:title'})
#             title = og_t.get('content', '') if og_t else ''
#             if not title:
#                 h1    = soup.find('h1')
#                 title = h1.get_text(strip=True) if h1 else product
#             rat_el = soup.find('span', {'itemprop': 'ratingValue'})
#             rating = _parse_rating(rat_el.get_text()) if rat_el else None
#             return {'price': price, 'rating': rating, 'reviews': None,
#                     'title': title[:80], 'url': url,
#                     'currency': 'INR', 'source': platform['name']}
#     except Exception:
#         pass
#     return None


# def _scrape_generic(platform: dict, product: str, floor: int):
#     q   = product.replace(' ', '+')
#     url = platform['base_url'] + platform['search_path'] + q
#     try:
#         r = requests.get(url, headers={"User-Agent": random.choice(_UA)},
#                          timeout=REQUEST_TIMEOUT)
#         if r.status_code != 200:
#             return None
#         price = _median(_all_prices(
#             BeautifulSoup(r.text, 'html.parser').get_text(), floor))
#         if price:
#             return {'price': price, 'rating': None, 'reviews': None,
#                     'title': product, 'url': url,
#                     'currency': 'INR', 'source': 'scraped'}
#     except Exception:
#         pass
#     return None


# # ──────────────────────────────────────────────────────────────────
# # Platform dispatcher (called by web_scraping_mcts.py)
# # ──────────────────────────────────────────────────────────────────
# def scrape_platform_real_time(platform: dict, product_name: str):
#     ptype = platform.get('type', 'generic')
#     floor = _floor(product_name)
#     try:
#         if   ptype == 'amazon':   return _scrape_amazon(product_name, floor)
#         elif ptype == 'flipkart': return _scrape_flipkart(product_name, floor)
#         elif ptype == 'myntra':   return _scrape_myntra(product_name, floor)
#         elif ptype == 'official': return _scrape_official(platform, product_name, floor)
#         else:                     return _scrape_generic(platform, product_name, floor)
#     except Exception:
#         return None


# # ──────────────────────────────────────────────────────────────────
# # Bing per-platform fallback
# # ──────────────────────────────────────────────────────────────────
# def _bing_platform(product: str, platform_name: str, floor: int,
#                    base_url: str = ''):
#     """
#     Bing search: '{product} price site:{domain}'
#     Extracts ₹ from result snippets.
#     For official/brand sites, uses the base_url domain.
#     """
#     # Determine domain to search
#     if 'amazon' in platform_name.lower():
#         domain = 'amazon.in'
#     elif 'flipkart' in platform_name.lower():
#         domain = 'flipkart.com'
#     elif 'myntra' in platform_name.lower():
#         domain = 'myntra.com'
#     elif base_url:
#         # Extract domain from base_url
#         m = re.search(r'https?://(?:www\.)?([^/]+)', base_url)
#         domain = m.group(1) if m else None
#     else:
#         domain = None

#     if not domain:
#         return None

#     try:
#         q   = f"{product} price site:{domain}".replace(' ', '+')
#         url = f"https://www.bing.com/search?q={q}&mkt=en-IN&setlang=en-IN"
#         s   = _session("https://www.bing.com/")
#         r   = s.get(url, timeout=8)
#         if r.status_code != 200:
#             return None
#         soup = BeautifulSoup(r.text, 'html.parser')
#         for res in soup.select('li.b_algo')[:8]:
#             prices = _all_prices(res.get_text(), floor)
#             best   = _median(prices)
#             if best:
#                 link_el = res.select_one('h2 a')
#                 title   = link_el.get_text(strip=True)[:80] if link_el else product
#                 href    = link_el.get('href', '') if link_el else \
#                           f"https://www.{domain}"
#                 return {'price': best, 'rating': None, 'reviews': None,
#                         'title': title, 'url': href,
#                         'currency': 'INR', 'source': f'bing→{domain}'}
#         return None
#     except Exception:
#         return None


# # ──────────────────────────────────────────────────────────────────
# # Query helpers
# # ──────────────────────────────────────────────────────────────────
# def extract_product_name(query: str) -> str:
#     """
#     Strips filler + punctuation. Handles 'Platforms.' correctly.
#     'compare HP Laptop prices on various Platforms.' → 'hp laptop'
#     """
#     STOP = {
#         'compare','comparing','buy','purchase','find','search','best',
#         'price','prices','pricing','cost','costs','rate','rates',
#         'on','in','at','of','to','for','a','an','the',
#         'different','platforms','platform','sites','site','store',
#         'stores','check','over','across','various','multiple',
#         'show','get','me','give','tell','list','top',
#         'cheap','cheaper','cheapest','lowest','affordable',
#         'review','reviews','rating','ratings',
#         'official','website','from','http','https',
#         'online','shopping','india','indian',
#         'and','or','with','all','do','i','is','are','can',
#         'real','time','live','now','today','current','latest',
#         'please','want','need','help','know',
#         'amazon','flipkart','myntra','meesho','nykaa',
#         'croma','reliance','tatacliq','snapdeal','paytm',
#     }
#     query   = re.sub(r'https?://\S+', '', query)
#     words   = query.lower().split()
#     cleaned = []
#     for w in words:
#         w = re.sub(r'^[^a-z0-9]+|[^a-z0-9]+$', '', w)
#         if w and w not in STOP and len(w) > 1:
#             cleaned.append(w)
#     return ' '.join(cleaned).strip()


# def extract_official_url(query: str):
#     m = re.search(r'https?://[^\s]+', query)
#     return m.group(0).rstrip('.,)') if m else None


# # ──────────────────────────────────────────────────────────────────
# # Formatters
# # ──────────────────────────────────────────────────────────────────
# def _fmt_results(output: str, results: dict, product: str) -> str:
#     sorted_r = sorted(results.items(), key=lambda x: x[1]['price'])

#     output += f"{'PLATFORM':<22} {'PRICE (INR)':>12}  {'RATING':>8}  SOURCE\n"
#     output += f"{'-'*22} {'-'*12}  {'-'*8}  {'-'*24}\n"

#     for name, data in sorted_r:
#         price  = f"₹{data['price']:,.0f}"
#         rating = f"{data['rating']}/5 ⭐" if data.get('rating') else "N/A"
#         source = data.get('source', 'scraped')[:24]
#         output += f"{name:<22} {price:>12}  {rating:>8}  {source}\n"

#     best = sorted_r[0]
#     bd   = best[1]
#     output += f"\n{'='*70}\n"
#     output += f"✅ BEST PRICE  : {best[0]}  →  ₹{bd['price']:,.0f}\n"
#     if bd.get('rating'):
#         output += f"⭐ RATING       : {bd['rating']}/5\n"
#     if bd.get('reviews'):
#         output += f"💬 REVIEWS      : {bd['reviews']}\n"
#     output += f"🔗 BUY HERE     : {bd.get('url', 'N/A')}\n"
#     output += f"{'='*70}\n\n"

#     if len(sorted_r) > 1:
#         output += "🔗 All Platform Links:\n"
#         for name, data in sorted_r:
#             if data.get('url'):
#                 note = "  ⚠️ bing" if 'bing' in data.get('source', '') else ''
#                 output += f"  • {name:<20}: {data['url']}{note}\n"
#         output += "\n"

#     output += "📡 All prices scraped live — zero AI-generated values.\n"
#     output += "⚠️  Prices change frequently — verify on platform before purchase.\n"
#     return output


# def _fmt_none(output: str, product: str) -> str:
#     q = product.replace(' ', '+')
#     output += "\n❌ Could not fetch live prices from any source.\n\n"
#     output += "🔍 Search manually:\n"
#     output += f"  • Amazon.in : https://www.amazon.in/s?k={q}\n"
#     output += f"  • Flipkart  : https://www.flipkart.com/search?q={q}\n"
#     output += f"  • Myntra    : https://www.myntra.com/{product.replace(' ','-')}\n"
#     return output


# # Legacy aliases
# def format_results(out, results, product_name=''):
#     return _fmt_results(out, results, product_name)

# def format_no_results(out, product_name):
#     return _fmt_none(out, product_name)
#####################################################################
# backend/tools/ecommerce.py
"""
Real-time e-commerce price scraper — India.

Sources tried for EVERY query:
  1. Amazon.in       — CSS selectors + full-page text scan fallback
  2. Flipkart        — multi-strategy CSS + ₹ string scan + text scan
  3. Myntra          — JSON API (only for fashion/lifestyle products)
  4. Official Site   — auto-detected from brand name OR user-supplied URL

Bing search snippet fallback per platform when direct scraping blocked.
ZERO LLM-generated prices.
"""

import requests
import re
import time
import random
from bs4 import BeautifulSoup
from config import REQUEST_TIMEOUT, MCTS_SIMULATIONS
from mcts.web_scraping_mcts import run_mcts_scraping


# ──────────────────────────────────────────────────────────────────
# Brand → official site mapping
# Auto-detected from product name — no URL needed from user
# ──────────────────────────────────────────────────────────────────
BRAND_SITES = {
    # Laptops / Computers
    "iphone":     "https://www.apple.com/in/shop/buy-iphone",
    "macbook":    "https://www.apple.com/in/shop/buy-mac",
    "hp":         "https://www.hp.com/in-en/shop/laptops.html",
    "dell":       "https://www.dell.com/en-in/cat/laptops",
    "lenovo":     "https://www.lenovo.com/in/en/laptops/",
    "asus":       "https://www.asus.com/in/laptops/",
    "acer":       "https://store.acer.com/en-in/laptops",
    "apple":      "https://www.apple.com/in/",
    "msi":        "https://in.msi.com/Laptops",
    "lg":         "https://www.lg.com/in/laptops",
    "microsoft":  "https://www.microsoft.com/en-in/surface",
    # Phones
    "samsung":    "https://www.samsung.com/in/smartphones/",
    "oneplus":    "https://www.oneplus.in/smartphones",
    "realme":     "https://www.realme.com/in/smartphones",
    "redmi":      "https://www.mi.com/in/phones",
    "xiaomi":     "https://www.mi.com/in/phones",
    "mi ":        "https://www.mi.com/in/phones",
    "poco":       "https://www.poco.in/mobiles",
    "vivo":       "https://www.vivo.com/in/products/smartphones",
    "oppo":       "https://www.oppo.com/in/smartphones/",
    "motorola":   "https://www.motorola.in/smartphones",
    "nokia":      "https://www.nokia.com/phones/en_in/",
    "iqoo":       "https://www.iqoo.com/in/phone.html",
    # Audio — Shopify sites use /search?q= + /products.json API
    "boat":       "https://www.boat-lifestyle.com",
    "jbl":        "https://in.jbl.com",
    "sony":       "https://www.sony.co.in",
    "bose":       "https://www.bose.in",
    "sennheiser": "https://www.sennheiser.com",
    "skullcandy": "https://www.skullcandy.in",
    "noise":      "https://www.gonoise.com",
    "zebronics":  "https://www.zebronics.com",
    # Watches
    "fastrack":   "https://www.fastrack.in",
    "titan":      "https://www.titan.co.in",
    "fossil":     "https://www.fossil.com/en-in/",
    "garmin":     "https://www.garmin.com/en-IN/",
    "fitbit":     "https://www.fitbit.com/in/home",
    # TVs
    "tcl":        "https://www.tcl.com/in/en/televisions.html",
    "mi tv":      "https://www.mi.com/in/tv",
    # Cameras
    "canon":      "https://in.canon/en/consumer/cameras",
    "nikon":      "https://www.nikonindia.com/cameras/",
    "fujifilm":   "https://www.fujifilmgfx.com/in/products/cameras/",
    "gopro":      "https://gopro.com/en/in/",
    # Appliances
    "bosch":      "https://www.bosch-home.com/in/",
    "whirlpool":  "https://www.whirlpoolindia.com/",
    "haier":      "https://www.haier.com/in/",
    "voltas":     "https://www.voltas.com/",
}


def _get_brand_site(product: str) -> tuple:
    """
    Auto-detect official brand site from product name.
    Returns (brand_name, url) or (None, None).
    """
    p = product.lower()
    for brand, url in BRAND_SITES.items():
        if brand in p:
            return brand.title(), url
    return None, None


# ──────────────────────────────────────────────────────────────────
# Category price floors
# ──────────────────────────────────────────────────────────────────
CATEGORY_FLOORS = {
    "macbook": 80000, "imac": 80000,
    "laptop": 15000,  "notebook": 15000, "chromebook": 12000,
    "desktop": 15000, "computer": 10000,
    "iphone": 40000,
    "smartphone": 5000, "mobile": 3000, "phone": 3000,
    "oneplus": 15000, "samsung": 3000, "pixel": 30000,
    "redmi": 5000, "realme": 5000, "poco": 7000,
    "vivo": 5000, "oppo": 5000, "motorola": 7000,
    "ipad": 30000, "tablet": 5000,
    "smart tv": 10000, "television": 10000, "tv": 8000,
    "oled": 30000, "qled": 25000,
    "refrigerator": 10000, "fridge": 10000,
    "washing machine": 10000, "washer": 10000,
    "air conditioner": 15000, "microwave": 5000, "oven": 5000,
    "headphone": 500, "earphone": 200, "earbuds": 300,
    "speaker": 500, "soundbar": 3000,
    "camera": 5000, "dslr": 20000, "mirrorless": 30000,
    "smartwatch": 2000, "watch": 500,
    "keyboard": 300, "mouse": 200, "monitor": 5000,
    "printer": 3000, "router": 1000,
    "hard disk": 2000, "ssd": 1500,
    "gpu": 15000, "graphics card": 15000,
    "mixer": 1500, "grinder": 500, "iron": 500,
    "trimmer": 500, "shaver": 500, "fan": 500,
    "cooler": 2000, "heater": 1000, "purifier": 3000,
    "default": 200,
}
PRICE_MAX = 500000

MYNTRA_SELLS = {
    "watch","watches","shoe","shoes","sneaker","sandal","bag","bags",
    "backpack","handbag","tshirt","shirt","dress","jeans","trouser",
    "kurta","saree","jacket","coat","hoodie","sweater","sunglasses",
    "earring","necklace","bracelet","perfume","lipstick","moisturizer",
    "trimmer","shaver","earbuds","headphone","smartwatch",
    "fastrack","titan","boat","noise","zebronics","skullcandy",
}


def _floor(product: str) -> int:
    p = product.lower()
    for kw, f in CATEGORY_FLOORS.items():
        if kw in p:
            return f
    return CATEGORY_FLOORS["default"]


def _valid(price, floor: int) -> bool:
    return price is not None and floor <= float(price) <= PRICE_MAX


def _myntra_ok(product: str) -> bool:
    p = product.lower()
    return any(cat in p for cat in MYNTRA_SELLS)


# ──────────────────────────────────────────────────────────────────
# Session factory
# ──────────────────────────────────────────────────────────────────
_UA = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) "
    "Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]


def _session(ref="https://www.google.co.in/"):
    s = requests.Session()
    s.headers.update({
        "User-Agent":                random.choice(_UA),
        "Accept-Language":           "en-IN,en;q=0.9,hi;q=0.8",
        "Accept":                    "text/html,application/xhtml+xml,"
                                     "application/xml;q=0.9,image/avif,"
                                     "image/webp,*/*;q=0.8",
        "Accept-Encoding":           "gzip, deflate, br",
        "Referer":                   ref,
        "DNT":                       "1",
        "Connection":                "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    })
    return s


# ──────────────────────────────────────────────────────────────────
# Parsers
# ──────────────────────────────────────────────────────────────────
def _parse_inr(text: str):
    if not text:
        return None
    text = re.sub(r'[,\xa0\u200b]', '', str(text)).strip()
    for pat in [r'₹\s*([0-9]+(?:\.[0-9]{1,2})?)',
                r'Rs\.?\s*([0-9]+(?:\.[0-9]{1,2})?)',
                r'INR\s*([0-9]+(?:\.[0-9]{1,2})?)']:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except Exception:
                continue
    return None


def _parse_rating(text: str):
    if not text:
        return None
    m = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*(?:out\s*of\s*5|/5|stars?)?',
                  str(text), re.IGNORECASE)
    if m:
        try:
            v = float(m.group(1))
            if 0.0 < v <= 5.0:
                return round(v, 1)
        except Exception:
            pass
    return None


def _all_prices(text: str, floor: int) -> list:
    text  = re.sub(r'[,]', '', str(text))
    found = []
    for pat in [r'₹\s*([0-9]+(?:\.[0-9]{1,2})?)',
                r'Rs\.?\s*([0-9]+(?:\.[0-9]{1,2})?)',
                r'INR\s*([0-9]+(?:\.[0-9]{1,2})?)']:
        for m in re.findall(pat, text, re.IGNORECASE):
            try:
                v = float(m)
                if _valid(v, floor):
                    found.append(v)
            except Exception:
                continue
    return sorted(set(found))


def _median(prices: list):
    if not prices:
        return None
    prices  = sorted(prices)
    trimmed = prices[:max(1, int(len(prices) * 0.8))]
    return trimmed[len(trimmed) // 2]


# ──────────────────────────────────────────────────────────────────
# Main handler
# ──────────────────────────────────────────────────────────────────
def handle_ecommerce(query: str) -> str:
    try:
        product      = extract_product_name(query)
        official_url = extract_official_url(query)
        floor        = _floor(product)
        use_myntra   = _myntra_ok(product)

        # Auto-detect brand official site if no URL given
        auto_brand, auto_site = _get_brand_site(product)
        if not official_url and auto_site:
            official_url = auto_site

        out  = f"🔍 Real-Time Price Comparison — India\n{'='*70}\n"
        out += f"🛍️  Product      : {product.title()}\n"
        out += f"💰 Price floor   : ₹{floor:,} (junk values rejected below this)\n"

        srcs = "Amazon.in | Flipkart"
        if use_myntra:
            srcs += " | Myntra"
        if official_url:
            brand_label = auto_brand or "Official Site"
            srcs += f" | {brand_label} Official"
        out += f"📡 Sources       : {srcs}\n\n"

        # ── Build platform list ───────────────────────────────────
        platforms = [
            {'name': 'Amazon India', 'base_url': 'https://www.amazon.in',
             'search_path': '/s?k=', 'priority': 1, 'type': 'amazon'},
            {'name': 'Flipkart',     'base_url': 'https://www.flipkart.com',
             'search_path': '/search?q=', 'priority': 2, 'type': 'flipkart'},
        ]
        if use_myntra:
            platforms.append(
                {'name': 'Myntra', 'base_url': 'https://www.myntra.com',
                 'search_path': '/', 'priority': 3, 'type': 'myntra'})
        if official_url:
            brand_label = auto_brand or "Official Site"
            platforms.insert(0, {
                'name':       f'{brand_label} Official',
                'base_url':   official_url,
                'search_path': '',
                'priority':   0,
                'type':       'official',
                'direct_url': official_url,
            })

        # ── MCTS-guided scraping ──────────────────────────────────
        out += f"🌳 MCTS ({MCTS_SIMULATIONS} simulations) deciding visit order...\n"
        results, visited = run_mcts_scraping(platforms, product, MCTS_SIMULATIONS)
        results = {k: v for k, v in results.items() if _valid(v.get('price'), floor)}
        out += f"📊 Visited   : {' → '.join(visited)}\n"
        out += f"✅ Direct hit: {len(results)}/{len(platforms)}\n"

        # ── Per-platform Bing fallback ────────────────────────────
        failed = [p for p in platforms if p['name'] not in results]
        if failed:
            out += f"⚠️  {len(failed)} platform(s) blocked → Bing fallback...\n"
            for p in failed:
                bd = _bing_platform(product, p['name'], floor,
                                    p.get('base_url', ''))
                if bd:
                    results[p['name']] = bd
                    out += f"   ✅ {p['name']}: ₹{bd['price']:,.0f} via Bing\n"
                else:
                    out += f"   ❌ {p['name']}: no price found\n"

        if results:
            out += f"\n{'='*70}\n\n"
            return _fmt_results(out, results, product)

        return out + _fmt_none('', product)

    except Exception as e:
        return f"❌ Error: {str(e)}"


# ──────────────────────────────────────────────────────────────────
# Amazon.in
# ──────────────────────────────────────────────────────────────────
def _scrape_amazon(product: str, floor: int):
    q   = product.replace(' ', '+')
    url = f"https://www.amazon.in/s?k={q}"
    try:
        s = _session("https://www.amazon.in/")
        try:
            s.get("https://www.amazon.in/", timeout=5)
            time.sleep(0.5)
        except Exception:
            pass
        r = s.get(url, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            return None
        soup  = BeautifulSoup(r.text, 'html.parser')
        cards = soup.select('div[data-component-type="s-search-result"]')
        for card in cards[:15]:
            if card.get('data-adfeedbackdetails') or \
               card.select_one('[aria-label*="Sponsored"]'):
                continue
            price = None
            for sel in ['span.a-price span.a-offscreen',
                        'span.a-price-whole',
                        '.a-price .a-offscreen',
                        'span.a-color-price']:
                el = card.select_one(sel)
                if el:
                    p = _parse_inr(el.get_text())
                    if p and _valid(p, floor):
                        price = p
                        break
            if not price:
                continue
            title_el = card.select_one('h2 a span')
            title    = title_el.get_text(strip=True)[:80] if title_el else product
            rat_el   = card.select_one('span.a-icon-alt')
            rating   = _parse_rating(rat_el.get_text()) if rat_el else None
            rev_el   = card.select_one('span.a-size-base.s-underline-text')
            reviews  = rev_el.get_text(strip=True) if rev_el else None
            link_el  = card.select_one('h2 a')
            purl     = ("https://www.amazon.in" + link_el['href']) if link_el else url
            return {'price': price, 'rating': rating, 'reviews': reviews,
                    'title': title, 'url': purl,
                    'currency': 'INR', 'source': 'amazon.in'}
        # text scan fallback
        prices = _all_prices(soup.get_text(), floor)
        best   = _median(prices)
        if best:
            return {'price': best, 'rating': None, 'reviews': None,
                    'title': product, 'url': url,
                    'currency': 'INR', 'source': 'amazon.in (scan)'}
    except Exception:
        pass
    return None


# ──────────────────────────────────────────────────────────────────
# Flipkart — multi-strategy
# ──────────────────────────────────────────────────────────────────
def _scrape_flipkart(product: str, floor: int):
    """
    4-strategy Flipkart scraper — robust against CSS class changes.

    Strategy 1: CSS class-based card parsing (works when classes are known)
    Strategy 2: ₹ string scan within every card (CSS-class-independent)
    Strategy 3: Full page text scan with median price selection
    Strategy 4: Flipkart mobile/lite URL (different HTML, often simpler)
    """
    q    = product.replace(' ', '+')
    # Multiple URL patterns — different params sometimes bypass bot detection
    urls = [
        f"https://www.flipkart.com/search?q={q}",
        f"https://www.flipkart.com/search?q={q}&sort=popularity_desc",
        f"https://www.flipkart.com/search?q={q}&otracker=search",
    ]

    for url in urls:
        try:
            s = _session("https://www.flipkart.com/")
            s.cookies.set('T', '0', domain='.flipkart.com')
            s.headers.update({
                "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
            })
            r = s.get(url, timeout=REQUEST_TIMEOUT)
            if r.status_code != 200:
                continue

            soup      = BeautifulSoup(r.text, 'html.parser')
            page_text = soup.get_text()

            # Quick check — if page has no ₹ at all, it's a bot-block page
            if '₹' not in page_text and 'Rs.' not in page_text:
                continue

            # ── Strategy 1 & 2: card-by-card ──────────────────────
            cards = []
            for csel in [
                # 2024-2025 Flipkart layouts
                'div.cPHDOP', 'div._75nlfW', 'div.slAVV4',
                # Classic layouts (still used for some categories)
                'div._1AtVbE', 'div._13oc-S', 'div._2kHMtA',
                'div._4ddWXP', 'div._1YokD2', 'li.col',
                'div[data-id]',
            ]:
                found = soup.select(csel)
                if len(found) > 1:
                    cards = found
                    break

            for card in cards[:20]:
                price = None

                # Strategy 1: known CSS price classes
                for psel in [
                    # 2024-2025
                    'div.Nx9bqj', 'div.Nx9bqj.CxhGGd', 'div._44qnta',
                    'div.hl05eU div.Nx9bqj', 'span.Nx9bqj',
                    # 2022-2023
                    'div._30jeq3', 'div._30jeq3._1_WHN1',
                    'div._25b18c div._30jeq3',
                    # older
                    'div._1vC4OE', 'div._3qQ9m1', 'div.UOCQB1',
                ]:
                    el = card.select_one(psel)
                    if el:
                        p = _parse_inr(el.get_text())
                        if p and _valid(p, floor):
                            price = p
                            break

                # Strategy 2: any text node containing ₹ inside the card
                if not price:
                    for node in card.find_all(string=re.compile(r'₹\s*[0-9]')):
                        p = _parse_inr(str(node))
                        if p and _valid(p, floor):
                            price = p
                            break

                if not price:
                    continue

                # Title
                title = product
                for tsel in [
                    'div.KzDlHZ', 'a.wjcEIp', 'div._4rR01T',
                    'a.s1Q9rs', 'div._2WkVRV', 'a.IRpwTa',
                    'p.txtnm', '[class*="name"]', 'h2', 'h3',
                ]:
                    el = card.select_one(tsel)
                    if el and el.get_text(strip=True):
                        title = el.get_text(strip=True)[:80]
                        break

                # Rating
                rating = None
                for rsel in [
                    'div.XQDdHH', 'div._3LWZlK', 'span._2_R_DZ',
                    '[class*="rating"]', 'span.Y1HWO0',
                ]:
                    el = card.select_one(rsel)
                    if el:
                        rating = _parse_rating(el.get_text())
                        if rating:
                            break

                # Link — prefer actual product pages /p/ path
                link_el = (
                    card.select_one('a[href*="/p/"]')   or
                    card.select_one('a[href*="dl="]')   or
                    card.select_one('a[href]')
                )
                if link_el and link_el.get('href'):
                    href = link_el['href']
                    purl = href if href.startswith('http') \
                           else "https://www.flipkart.com" + href
                else:
                    purl = url

                return {'price': price, 'rating': rating, 'reviews': None,
                        'title': title, 'url': purl,
                        'currency': 'INR', 'source': 'flipkart.com'}

            # ── Strategy 3: full-page text scan ───────────────────
            # Floor ensures junk (₹5, ₹99 offers) are filtered
            prices = _all_prices(page_text, floor)
            best   = _median(prices)
            if best:
                # Try to get a product link from the page
                link_el = soup.select_one('a[href*="/p/"]')
                purl    = ("https://www.flipkart.com" + link_el['href']
                           if link_el and link_el.get('href') else url)
                return {'price': best, 'rating': None, 'reviews': None,
                        'title': product, 'url': purl,
                        'currency': 'INR', 'source': 'flipkart.com (scan)'}

        except Exception:
            continue

    return None


# ──────────────────────────────────────────────────────────────────
# Myntra — JSON API (fashion only)
# ──────────────────────────────────────────────────────────────────
def _scrape_myntra(product: str, floor: int):
    q   = product.replace(' ', '%20')
    url = f"https://www.myntra.com/gateway/v2/search/{q}?rawQuery={q}&p=1&rows=8"
    try:
        s = _session("https://www.myntra.com/")
        s.headers.update({"X-Myntra-Abtest": "false"})
        r = s.get(url, timeout=REQUEST_TIMEOUT)
        if r.status_code == 200:
            data  = r.json()
            prods = (data.get('searchData', {})
                         .get('results', {})
                         .get('products', [])
                     or data.get('products', []))
            for p in prods[:10]:
                po    = p.get('priceV3') or p.get('price') or {}
                price = None
                if isinstance(po, dict):
                    raw = po.get('discounted') or po.get('mrp')
                    if raw:
                        price = float(str(raw).replace(',', ''))
                elif isinstance(p.get('discountedPrice'), (int, float)):
                    price = float(p['discountedPrice'])
                elif isinstance(p.get('price'), (int, float)):
                    price = float(p['price'])
                if not price or not _valid(price, floor):
                    continue
                title = p.get('productName') or product
                slug  = p.get('landingPageUrl', '')
                purl  = f"https://www.myntra.com/{slug}" if slug \
                        else f"https://www.myntra.com/{product.replace(' ','-')}"
                return {'price': float(price),
                        'rating': float(p['rating']) if p.get('rating') else None,
                        'reviews': str(p.get('ratingCount', '') or ''),
                        'title': str(title)[:80], 'url': purl,
                        'currency': 'INR', 'source': 'myntra.com'}
    except Exception:
        pass
    return None


# ──────────────────────────────────────────────────────────────────
# Official brand site scraper
#
# Strategy (in order):
#   1. Shopify JSON API  (/products.json?q=)  — instant JSON, no JS needed
#   2. Shopify search page (/search?q=)       — HTML with prices
#   3. schema.org itemprop="price"            — standard structured data
#   4. Open Graph product:price:amount        — meta tag
#   5. Full page text scan                    — last resort
#
# Most Indian brand sites (boAt, Noise, Fastrack, Titan) run on Shopify
# and expose the /products.json API which returns price data as JSON.
# ──────────────────────────────────────────────────────────────────
def _scrape_official(platform: dict, product: str, floor: int):
    base = (platform.get('direct_url') or platform.get('base_url') or '').rstrip('/')
    if not base:
        return None

    # Extract product search term (strip brand name if it matches the domain)
    search_q = product.replace(' ', '+')

    # ── Strategy 1: Shopify /products.json API ────────────────────
    # Works for: boAt, Noise, Fastrack, Titan, Skullcandy, Zebronics etc.
    try:
        api_url = f"{base}/products.json?q={search_q}&limit=10"
        s       = _session(base + '/')
        r       = s.get(api_url, timeout=8)
        if r.status_code == 200:
            try:
                data     = r.json()
                products = data.get('products', [])
                for p in products[:10]:
                    title    = p.get('title', product)
                    variants = p.get('variants', [])
                    # Collect all variant prices
                    v_prices = []
                    for v in variants:
                        raw = v.get('price') or v.get('compare_at_price')
                        if raw:
                            try:
                                v_prices.append(float(str(raw).replace(',', '')))
                            except Exception:
                                pass
                    # Pick lowest valid price (cheapest variant)
                    valid_prices = [p for p in v_prices if _valid(p, floor)]
                    if not valid_prices:
                        continue
                    price = min(valid_prices)
                    # Product URL
                    handle = p.get('handle', '')
                    purl   = f"{base}/products/{handle}" if handle else base
                    return {
                        'price':    price,
                        'rating':   None,
                        'reviews':  None,
                        'title':    title[:80],
                        'url':      purl,
                        'currency': 'INR',
                        'source':   platform['name'],
                    }
            except Exception:
                pass
    except Exception:
        pass

    # ── Strategy 2: Shopify /search?q= page ──────────────────────
    try:
        search_url = f"{base}/search?q={search_q}&type=product"
        s          = _session(base + '/')
        r          = s.get(search_url, timeout=REQUEST_TIMEOUT)
        if r.status_code == 200:
            soup  = BeautifulSoup(r.text, 'html.parser')
            # Shopify price selectors
            for psel in [
                'span.price', 'span[class*="price"]',
                'div[class*="price"]', 'p[class*="price"]',
                'span.product-price', 'span.money',
            ]:
                for el in soup.select(psel)[:5]:
                    p = _parse_inr(el.get_text())
                    if p and _valid(p, floor):
                        # Get title
                        title_el = soup.select_one(
                            'h2[class*="product"], h3[class*="product"], '
                            'a[class*="product-title"], a[class*="product-name"]'
                        )
                        title = title_el.get_text(strip=True)[:80]                                 if title_el else product
                        link_el = soup.select_one('a[href*="/products/"]')
                        purl    = (base + link_el['href'])                                   if link_el and link_el.get('href') else search_url
                        return {
                            'price': p, 'rating': None, 'reviews': None,
                            'title': title, 'url': purl,
                            'currency': 'INR', 'source': platform['name'],
                        }
    except Exception:
        pass

    # ── Strategy 3 & 4: schema.org / Open Graph ───────────────────
    try:
        s = _session()
        r = s.get(base, timeout=REQUEST_TIMEOUT)
        if r.status_code == 200:
            soup  = BeautifulSoup(r.text, 'html.parser')
            price = None
            el    = soup.find('span', {'itemprop': 'price'})
            if el:
                price = _parse_inr(el.get('content', '') or el.get_text())
            if not price or not _valid(price, floor):
                og = soup.find('meta', {'property': 'product:price:amount'})
                if og:
                    try:
                        price = float(og.get('content', '0').replace(',', ''))
                    except Exception:
                        pass
            # Strategy 5: full page text scan
            if not price or not _valid(price, floor):
                price = _median(_all_prices(soup.get_text(), floor))
            if price and _valid(price, floor):
                og_t  = soup.find('meta', {'property': 'og:title'})
                title = og_t.get('content', '') if og_t else ''
                if not title:
                    h1    = soup.find('h1')
                    title = h1.get_text(strip=True) if h1 else product
                rat_el = soup.find('span', {'itemprop': 'ratingValue'})
                rating = _parse_rating(rat_el.get_text()) if rat_el else None
                return {
                    'price': price, 'rating': rating, 'reviews': None,
                    'title': title[:80], 'url': base,
                    'currency': 'INR', 'source': platform['name'],
                }
    except Exception:
        pass

    return None


def _scrape_generic(platform: dict, product: str, floor: int):
    q   = product.replace(' ', '+')
    url = platform['base_url'] + platform['search_path'] + q
    try:
        r = requests.get(url, headers={"User-Agent": random.choice(_UA)},
                         timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            return None
        price = _median(_all_prices(
            BeautifulSoup(r.text, 'html.parser').get_text(), floor))
        if price:
            return {'price': price, 'rating': None, 'reviews': None,
                    'title': product, 'url': url,
                    'currency': 'INR', 'source': 'scraped'}
    except Exception:
        pass
    return None


# ──────────────────────────────────────────────────────────────────
# Platform dispatcher (called by web_scraping_mcts.py)
# ──────────────────────────────────────────────────────────────────
def scrape_platform_real_time(platform: dict, product_name: str):
    ptype = platform.get('type', 'generic')
    floor = _floor(product_name)
    try:
        if   ptype == 'amazon':   return _scrape_amazon(product_name, floor)
        elif ptype == 'flipkart': return _scrape_flipkart(product_name, floor)
        elif ptype == 'myntra':   return _scrape_myntra(product_name, floor)
        elif ptype == 'official': return _scrape_official(platform, product_name, floor)
        else:                     return _scrape_generic(platform, product_name, floor)
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────
# Bing per-platform fallback
# ──────────────────────────────────────────────────────────────────
def _get_domain(platform_name: str, base_url: str = '') -> str:
    """Determine the search domain for a platform."""
    pl = platform_name.lower()
    if 'amazon' in pl:    return 'amazon.in'
    if 'flipkart' in pl:  return 'flipkart.com'
    if 'myntra' in pl:    return 'myntra.com'
    if base_url:
        m = re.search(r'https?://(?:www\.)?([^/]+)', base_url)
        if m: return m.group(1)
    return ''


def _bing_platform(product: str, platform_name: str, floor: int,
                   base_url: str = ''):
    """
    Multi-engine search fallback per platform.
    Tries Bing → DuckDuckGo → Google (cached).
    Handles both ₹ and Rs. price formats in snippets.
    """
    domain = _get_domain(platform_name, base_url)
    if not domain:
        return None

    query   = f"{product} price site:{domain}"
    q_enc   = query.replace(' ', '+')

    # Engine 1: Bing
    result = _search_engine_price(
        f"https://www.bing.com/search?q={q_enc}&mkt=en-IN&setlang=en-IN",
        selectors=['li.b_algo', 'div.b_algo'],
        product=product, domain=domain, floor=floor,
        referer="https://www.bing.com/"
    )
    if result:
        return result

    # Engine 2: DuckDuckGo HTML (lite, no JS, scraping-friendly)
    result = _search_engine_price(
        f"https://html.duckduckgo.com/html/?q={q_enc}",
        selectors=['div.result__body', 'div.result'],
        product=product, domain=domain, floor=floor,
        referer="https://duckduckgo.com/"
    )
    if result:
        return result

    # Engine 3: Direct search URL for the platform (last resort)
    direct_url = f"https://www.{domain}/search?q={product.replace(' ', '+')}"
    try:
        s = _session(f"https://www.{domain}/")
        r = s.get(direct_url, timeout=8)
        if r.status_code == 200:
            text   = BeautifulSoup(r.text, 'html.parser').get_text()
            prices = _all_prices(text, floor)
            best   = _median(prices)
            if best:
                return {'price': best, 'rating': None, 'reviews': None,
                        'title': product, 'url': direct_url,
                        'currency': 'INR', 'source': f'{domain} (text scan)'}
    except Exception:
        pass

    return None


def _search_engine_price(url: str, selectors: list, product: str,
                         domain: str, floor: int, referer: str):
    """Hit a search engine URL and extract price from result snippets."""
    try:
        s = _session(referer)
        r = s.get(url, timeout=8)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, 'html.parser')

        results = []
        for sel in selectors:
            results = soup.select(sel)
            if results:
                break

        for res in results[:10]:
            text   = res.get_text()
            # Only use results that mention the domain or brand name
            text_lower = text.lower()
            domain_parts = re.split(r'[-.]', domain.lower())
            if not (domain.lower() in text_lower or
                    any(len(p) > 2 and p in text_lower for p in domain_parts)):
                continue
            prices = _all_prices(text, floor)
            best   = _median(prices)
            if best:
                link_el = res.select_one('a[href]')
                href    = ''
                if link_el:
                    href = link_el.get('href', '')
                    # DuckDuckGo wraps URLs
                    if 'duckduckgo.com' in href or href.startswith('//'):
                        m = re.search(r'uddg=([^&]+)', href)
                        if m:
                            from urllib.parse import unquote
                            href = unquote(m.group(1))
                title = link_el.get_text(strip=True)[:80] if link_el else product
                if not href:
                    href = f"https://www.{domain}"
                engine = 'bing' if 'bing.com' in url else 'ddg'
                return {'price': best, 'rating': None, 'reviews': None,
                        'title': title, 'url': href,
                        'currency': 'INR', 'source': f'{engine}→{domain}'}
        return None
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────
# Query helpers
# ──────────────────────────────────────────────────────────────────
def extract_product_name(query: str) -> str:
    """
    Strips filler + punctuation. Handles 'Platforms.' correctly.
    'compare HP Laptop prices on various Platforms.' → 'hp laptop'
    """
    STOP = {
        'compare','comparing','buy','purchase','find','search','best',
        'price','prices','pricing','cost','costs','rate','rates',
        'on','in','at','of','to','for','a','an','the',
        'different','platforms','platform','sites','site','store',
        'stores','check','over','across','various','multiple',
        'show','get','me','give','tell','list','top',
        'cheap','cheaper','cheapest','lowest','affordable',
        'review','reviews','rating','ratings',
        'official','website','from','http','https',
        'online','shopping','india','indian',
        'and','or','with','all','do','i','is','are','can',
        'real','time','live','now','today','current','latest',
        'please','want','need','help','know',
        'amazon','flipkart','myntra','meesho','nykaa',
        'croma','reliance','tatacliq','snapdeal','paytm',
    }
    query   = re.sub(r'https?://\S+', '', query)
    words   = query.lower().split()
    cleaned = []
    for w in words:
        w = re.sub(r'^[^a-z0-9]+|[^a-z0-9]+$', '', w)
        if w and w not in STOP and len(w) > 1:
            cleaned.append(w)
    return ' '.join(cleaned).strip()


def extract_official_url(query: str):
    m = re.search(r'https?://[^\s]+', query)
    return m.group(0).rstrip('.,)') if m else None


# ──────────────────────────────────────────────────────────────────
# Formatters
# ──────────────────────────────────────────────────────────────────
def _fmt_results(output: str, results: dict, product: str) -> str:
    sorted_r = sorted(results.items(), key=lambda x: x[1]['price'])

    output += f"{'PLATFORM':<22} {'PRICE (INR)':>12}  {'RATING':>8}  SOURCE\n"
    output += f"{'-'*22} {'-'*12}  {'-'*8}  {'-'*24}\n"

    for name, data in sorted_r:
        price  = f"₹{data['price']:,.0f}"
        rating = f"{data['rating']}/5 ⭐" if data.get('rating') else "N/A"
        source = data.get('source', 'scraped')[:24]
        output += f"{name:<22} {price:>12}  {rating:>8}  {source}\n"

    best = sorted_r[0]
    bd   = best[1]
    output += f"\n{'='*70}\n"
    output += f"✅ BEST PRICE  : {best[0]}  →  ₹{bd['price']:,.0f}\n"
    if bd.get('rating'):
        output += f"⭐ RATING       : {bd['rating']}/5\n"
    if bd.get('reviews'):
        output += f"💬 REVIEWS      : {bd['reviews']}\n"
    output += f"🔗 BUY HERE     : {bd.get('url', 'N/A')}\n"
    output += f"{'='*70}\n\n"

    if len(sorted_r) > 1:
        output += "🔗 All Platform Links:\n"
        for name, data in sorted_r:
            if data.get('url'):
                note = "  ⚠️ bing" if 'bing' in data.get('source', '') else ''
                output += f"  • {name:<20}: {data['url']}{note}\n"
        output += "\n"

    output += "📡 All prices scraped live — zero AI-generated values.\n"
    output += "⚠️  Prices change frequently — verify on platform before purchase.\n"
    return output


def _fmt_none(output: str, product: str) -> str:
    q = product.replace(' ', '+')
    output += "\n❌ Could not fetch live prices from any source.\n\n"
    output += "🔍 Search manually:\n"
    output += f"  • Amazon.in : https://www.amazon.in/s?k={q}\n"
    output += f"  • Flipkart  : https://www.flipkart.com/search?q={q}\n"
    output += f"  • Myntra    : https://www.myntra.com/{product.replace(' ','-')}\n"
    return output


# Legacy aliases
def format_results(out, results, product_name=''):
    return _fmt_results(out, results, product_name)

def format_no_results(out, product_name):
    return _fmt_none(out, product_name)