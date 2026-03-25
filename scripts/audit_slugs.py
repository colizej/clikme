"""Audit OpenCart slugs vs Django DB to find what will 404 after migration."""
import re
import os
import sys
import django

sys.path.insert(0, '/Users/colizej/Documents/webApp/clikme')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.blog.models import Article
from apps.vendors.models import Vendor, Product
from apps.pages.models import Page

sql = open('opencart/u2971222_ocar341.sql').read()

match = re.search(r"INSERT INTO `oc9a_seo_url` VALUES (.*?);", sql, re.DOTALL)
block = match.group(1)
entries = re.findall(r"\(\d+,\d+,\d+,'([^']+)','([^']+)'\)", block)

products, vendors, infos, categories, other = [], [], [], [], []
for key, slug in entries:
    if key.startswith('product_id='):
        products.append((key, slug))
    elif key.startswith('vendor_id='):
        vendors.append((key, slug))
    elif key.startswith('information_id='):
        infos.append((key, slug))
    elif key.startswith('category_id='):
        categories.append((key, slug))
    else:
        other.append((key, slug))

print(f"=== OpenCart SEO URLs: {len(entries)} total ===")
print(f"  Products:   {len(products)}")
print(f"  Vendors:    {len(vendors)}")
print(f"  Info pages: {len(infos)}")
print(f"  Categories: {len(categories)}")
print(f"  Other:      {len(other)}")

# --- Check products ---
missing_products = []
for key, slug in products:
    if not Product.objects.filter(slug=slug).exists():
        missing_products.append(slug)

# --- Check vendors ---
missing_vendors = []
for key, slug in vendors:
    if not Vendor.objects.filter(slug=slug).exists():
        missing_vendors.append(slug)

# --- Check info pages (articles + pages) ---
missing_infos = []
for key, slug in infos:
    found = (Article.objects.filter(slug=slug).exists() or
             Page.objects.filter(slug=slug).exists())
    if not found:
        missing_infos.append((key, slug))

print(f"\n=== COVERAGE ===")
print(f"Products: {len(products) - len(missing_products)}/{len(products)} in Django")
print(f"Vendors:  {len(vendors) - len(missing_vendors)}/{len(vendors)} in Django")
print(f"Info pages: {len(infos) - len(missing_infos)}/{len(infos)} in Django")

if missing_products:
    print(f"\nMISSING PRODUCTS ({len(missing_products)}):")
    for s in missing_products:
        print(f"  /{s}/")

if missing_vendors:
    print(f"\nMISSING VENDORS ({len(missing_vendors)}):")
    for s in missing_vendors:
        print(f"  /{s}/")

if missing_infos:
    print(f"\nMISSING INFO PAGES ({len(missing_infos)}) - need redirects:")
    for k, s in missing_infos:
        print(f"  /{s}/  ({k})")

print(f"\n=== CATEGORIES — all need redirects ({len(categories)}) ===")
for k, s in sorted(categories, key=lambda x: x[1]):
    print(f"  /{s}/")

print(f"\nOTHER: {[o[0] for o in other]}")
