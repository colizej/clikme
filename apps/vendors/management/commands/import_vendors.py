"""
Management command: import_vendors
Импортирует 42 вендора из SQL-дампа + скрапит детали с live clikme.ru.

Данные из SQL:
  - oc9a_vendor: vendor_id, display_name, image, telephone, address, city,
                 map_url, facebook_url, about, logo, banner
  - oc9a_vendor_description: short description
  - oc9a_seo_url: vendor slug
  - oc9a_vendor_to_product + oc9a_product: products with slugs

Использование:
    python manage.py import_vendors
    python manage.py import_vendors --dry-run
    python manage.py import_vendors --force
    python manage.py import_vendors --skip-products
    python manage.py import_vendors --skip-images
"""

import html
import re
import shutil
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.vendors.models import Vendor, Product


# ── Constants ─────────────────────────────────────────────────────────────────

SQL_PATH = Path(settings.BASE_DIR) / "opencart" / "u2971222_ocar341.sql"
OC_IMAGE_ROOT = Path(settings.BASE_DIR) / "opencart" / "image"
MEDIA_ROOT = Path(settings.MEDIA_ROOT)

# Exclude test/inactive vendors
SKIP_VENDOR_IDS = {8, 14, 20}  # test, vendor (placeholder), food-store (inactive)

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


# ── SQL Parser (reused from import_blog) ──────────────────────────────────────

def _unescape(s: str) -> str:
    s = s.replace("\\'", "'").replace("\\\\", "\\")
    s = s.replace("\\n", "\n").replace("\\r", "")
    return html.unescape(s)


def _get_insert_values(sql_text: str, table_name: str) -> str:
    marker = f"INSERT INTO `{table_name}` VALUES "
    for line in sql_text.splitlines():
        if line.startswith(marker):
            return line[len(marker):].rstrip(";")
    return ""


def _parse_sql_values(raw: str) -> list:
    rows = []
    i, n = 0, len(raw)
    while i < n:
        while i < n and raw[i] != '(':
            i += 1
        if i >= n:
            break
        i += 1
        fields = []
        while i < n and raw[i] != ')':
            while i < n and raw[i] in (' ', '\t', '\n', '\r'):
                i += 1
            if i >= n or raw[i] == ')':
                break
            if raw[i] == ',':
                i += 1
                continue
            if raw[i] == "'":
                i += 1
                buf = []
                while i < n:
                    c = raw[i]
                    if c == '\\' and i + 1 < n:
                        buf.append(raw[i:i+2])
                        i += 2
                    elif c == "'":
                        if i + 1 < n and raw[i+1] == "'":
                            buf.append("''")
                            i += 2
                        else:
                            i += 1
                            break
                    else:
                        buf.append(c)
                        i += 1
                fields.append("".join(buf))
            elif raw[i:i+4] == 'NULL':
                fields.append(None)
                i += 4
            else:
                j = i
                while i < n and raw[i] not in (',', ')', ' ', '\t', '\n'):
                    i += 1
                fields.append(raw[j:i])
        while i < n and raw[i] != ')':
            i += 1
        i += 1
        if fields:
            rows.append(fields)
    return rows


# ── SQL Parsing ───────────────────────────────────────────────────────────────

def parse_vendors_from_sql(sql_text: str) -> dict:
    """Return {vendor_id: {...}} with all data we can get from SQL."""
    # 1. oc9a_vendor SEO slugs
    slug_map = {}
    raw = _get_insert_values(sql_text, "oc9a_seo_url")
    if raw:
        for vid, slug in re.findall(r"'vendor_id=(\d+)','([^']+)'", raw):
            slug_map[int(vid)] = slug

    if not slug_map:
        return {}

    # 2. oc9a_vendor main table
    # cols: vendor_id, firstname, lastname, display_name, email, image, telephone,
    #       salt, password, fax, about, company, postcode, address_1, address_2,
    #       country_id, zone_id, city, map_url, facebook_url, google_url, status,
    #       product_status, approved, language_id, payment_method, paypal,
    #       bank_name ... commission, date_added, date_modified, vendor_id (dup)
    vendors = {}
    raw = _get_insert_values(sql_text, "oc9a_vendor")
    if raw:
        for row in _parse_sql_values(raw):
            if len(row) < 22:
                continue
            vid = int(row[0])
            vendors[vid] = {
                "display_name": _unescape(row[3] or ""),
                "email": row[4] or "",
                "image": row[5] or "",
                "telephone": row[6] or "",
                "about": _unescape(row[10] or ""),
                "address_1": _unescape(row[13] or ""),
                "city": _unescape(row[17] or ""),
                "map_url": row[18] or "",
                "facebook_url": row[19] or "",
                "status": int(row[21] or 1),
                "approved": int(row[23] or 1),
                "logo": row[36] if len(row) > 36 else "",
            }

    # 3. oc9a_vendor_description
    raw = _get_insert_values(sql_text, "oc9a_vendor_description")
    if raw:
        # cols: vendor_id, language_id, description, meta_keywords
        for row in _parse_sql_values(raw):
            if len(row) < 3:
                continue
            vid = int(row[0])
            if vid in vendors:
                vendors[vid]["description"] = _unescape(row[2] or "")

    # 4. Products: oc9a_vendor_to_product + oc9a_seo_url (product slugs)
    #    + oc9a_product_description
    product_slugs = {}
    raw = _get_insert_values(sql_text, "oc9a_seo_url")
    if raw:
        for pid, slug in re.findall(r"'product_id=(\d+)','([^']+)'", raw):
            product_slugs[int(pid)] = slug

    product_names = {}
    raw = _get_insert_values(sql_text, "oc9a_product_description")
    if raw:
        # cols: product_id, language_id, name, meta_title, meta_keywords, description
        for row in _parse_sql_values(raw):
            if len(row) < 3:
                continue
            pid = int(row[0])
            if pid not in product_names:  # keep first (language_id=1 is Russian)
                product_names[pid] = {
                    "name": _unescape(row[2] or ""),
                    "description": _unescape(row[5] or "") if len(row) > 5 else "",
                }

    product_prices = {}
    raw = _get_insert_values(sql_text, "oc9a_product")
    if raw:
        # cols: product_id, model, sku, upc, ean, jan, isbn, mpn, location,
        #       quantity, stock_status_id, image, manufacturer_id, shipping, price, ...
        for row in _parse_sql_values(raw):
            if len(row) < 15:
                continue
            pid = int(row[0])
            product_prices[pid] = {
                "image": row[11] or "",
                "price": row[14] or "0",
            }

    vendor_products = {}
    raw = _get_insert_values(sql_text, "oc9a_vendor_to_product")
    if raw:
        for vid, pid in re.findall(r"\((\d+),(\d+)\)", raw):
            vendor_products.setdefault(int(vid), []).append(int(pid))

    # Combine
    result = {}
    for vid, slug in slug_map.items():
        if vid in SKIP_VENDOR_IDS:
            continue
        v = vendors.get(vid, {})
        prods = []
        for pid in vendor_products.get(vid, []):
            if pid in product_slugs:
                p = product_prices.get(pid, {})
                pn = product_names.get(pid, {})
                prods.append({
                    "oc_id": pid,
                    "slug": product_slugs[pid],
                    "name": pn.get("name", ""),
                    "description": pn.get("description", ""),
                    "image": p.get("image", ""),
                    "price": p.get("price", "0"),
                })
        result[vid] = {
            "slug": slug,
            "display_name": v.get("display_name") or slug.replace("-", " ").title(),
            "telephone": v.get("telephone", ""),
            "about": v.get("about", ""),
            "description": v.get("description", ""),
            "address": v.get("address_1", ""),
            "city": v.get("city", "Нячанг"),
            "map_url": v.get("map_url", ""),
            "facebook_url": v.get("facebook_url", ""),
            "image": v.get("image", ""),
            "logo": v.get("logo", ""),
            "status": v.get("status", 1),
            "approved": v.get("approved", 1),
            "products": prods,
        }
    return result


# ── Image helper ──────────────────────────────────────────────────────────────

def copy_image(oc_path: str, upload_to: str) -> str:
    if not oc_path:
        return ""
    src = OC_IMAGE_ROOT / oc_path
    if not src.exists():
        return ""
    dst = MEDIA_ROOT / oc_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        shutil.copy2(src, dst)
    return oc_path


# ── Live scraping ─────────────────────────────────────────────────────────────

def fetch_url(url: str) -> str:
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (clikme-import/1.0)"}
    )
    with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as resp:
        return resp.read(524288).decode("utf-8", errors="replace")


def scrape_vendor_page(slug: str) -> dict:
    """Scrape vendor description and meta from live clikme.ru."""
    url = f"https://clikme.ru/{urllib.parse.quote(slug, safe='')}/"
    try:
        page_html = fetch_url(url)
    except Exception:
        return {}

    clean = re.sub(r"<script[^>]*>.*?</script>", "", page_html, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"<style[^>]*>.*?</style>", "", clean, flags=re.DOTALL | re.IGNORECASE)

    meta_desc = ""
    m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)["\']', page_html, re.IGNORECASE)
    if m:
        meta_desc = html.unescape(m.group(1))

    # Extract h1 as display_name fallback
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", clean, re.IGNORECASE | re.DOTALL)
    h1_text = re.sub(r"<[^>]+>", "", h1.group(1)).strip() if h1 else ""

    # Try to extract description div
    desc_match = re.search(
        r'<div[^>]*class="[^"]*(?:vendor-about|store-about|about-vendor|description)[^"]*"[^>]*>(.*?)</div>',
        clean, re.DOTALL | re.IGNORECASE
    )
    description = ""
    if desc_match:
        description = re.sub(r"<[^>]+>", " ", desc_match.group(1)).strip()
        description = re.sub(r"\s+", " ", description)

    return {
        "display_name_live": h1_text,
        "meta_description": meta_desc,
        "description_live": description,
    }


def scrape_product_page(slug: str) -> dict:
    """Scrape product name and description from live clikme.ru."""
    url = f"https://clikme.ru/{urllib.parse.quote(slug, safe='')}/"
    try:
        page_html = fetch_url(url)
    except Exception:
        return {}

    clean = re.sub(r"<script[^>]*>.*?</script>", "", page_html, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"<style[^>]*>.*?</style>", "", clean, flags=re.DOTALL | re.IGNORECASE)

    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", clean, re.IGNORECASE | re.DOTALL)
    name = re.sub(r"<[^>]+>", "", h1.group(1)).strip() if h1 else ""

    # Extract product description
    desc_match = re.search(
        r"</h\d>\s*(.*?)\s*(?:<div[^>]*(?:class=['\"][^'\"]*(?:price|cart|buy|add-to|quantity)[^'\"]*['\"])|$)",
        clean, re.DOTALL | re.IGNORECASE
    )
    desc = ""
    if desc_match:
        raw = desc_match.group(1).strip()
        if len(raw) > 20:
            desc = raw[:3000]

    meta_desc = ""
    m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)["\']', page_html, re.IGNORECASE)
    if m:
        meta_desc = html.unescape(m.group(1))

    return {"name": name, "description": desc, "meta_description": meta_desc}


# ── Command ───────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Импортировать вендоров из SQL + live clikme.ru"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--force", action="store_true",
                            help="Обновить существующих вендоров")
        parser.add_argument("--skip-products", action="store_true",
                            help="Не импортировать продукты")
        parser.add_argument("--skip-images", action="store_true",
                            help="Не копировать изображения")
        parser.add_argument("--skip-scraping", action="store_true",
                            help="Не скрейпить live сайт")
        parser.add_argument("--delay", type=float, default=0.4,
                            help="Задержка между запросами (сек)")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        force = options["force"]
        skip_products = options["skip_products"]
        skip_images = options["skip_images"]
        skip_scraping = options["skip_scraping"]
        delay = options["delay"]

        if not SQL_PATH.exists():
            raise CommandError(f"SQL файл не найден: {SQL_PATH}")

        self.stdout.write("📂 Парсим SQL…")
        sql_text = SQL_PATH.read_text(encoding="utf-8", errors="replace")
        vendors_data = parse_vendors_from_sql(sql_text)
        self.stdout.write(f"   Найдено вендоров: {len(vendors_data)}")

        v_created = v_updated = v_skip = 0
        p_created = p_updated = 0

        for vid, vdata in sorted(vendors_data.items()):
            slug = vdata["slug"]
            display_name = vdata["display_name"]

            exists = Vendor.objects.filter(slug=slug).first()
            if exists and not force:
                self.stdout.write(f"  ⏭  [{slug}] уже существует")
                v_skip += 1
                continue

            # Scrape live for additional data if needed
            live_data = {}
            if not skip_scraping:
                self.stdout.write(f"  🌐 [{vid}] {display_name[:40]}…")
                live_data = scrape_vendor_page(slug)
                time.sleep(delay)

            # Merge: SQL data takes priority, live fills gaps
            final_name = display_name or live_data.get("display_name_live", slug)
            description = (vdata.get("description") or
                           vdata.get("about") or
                           live_data.get("description_live", ""))
            meta_description = live_data.get("meta_description", "")[:490]

            # Copy image
            image_path = ""
            if not skip_images:
                image_path = (copy_image(vdata["image"], "catalog/vendor/") or
                              copy_image(vdata["logo"], "catalog/vendor/"))

            self.stdout.write(
                f"  {'📝' if not exists else '🔄'} v{vid} [{slug}] "
                f"{final_name[:50]}"
            )

            if not dry_run:
                if exists and force:
                    exists.display_name = final_name
                    exists.description = description
                    exists.meta_description = meta_description
                    exists.telephone = vdata.get("telephone", "")
                    exists.address = vdata.get("address", "")
                    exists.city = vdata.get("city", "")
                    exists.map_url = vdata.get("map_url", "")
                    exists.facebook_url = vdata.get("facebook_url", "")
                    if image_path:
                        exists.image = image_path
                    exists.save()
                    vendor_obj = exists
                    v_updated += 1
                else:
                    vendor_obj = Vendor.objects.create(
                        oc_id=vid,
                        slug=slug,
                        display_name=final_name,
                        description=description,
                        meta_description=meta_description,
                        telephone=vdata.get("telephone", ""),
                        address=vdata.get("address", ""),
                        city=vdata.get("city", ""),
                        map_url=vdata.get("map_url", ""),
                        facebook_url=vdata.get("facebook_url", ""),
                        image=image_path,
                        is_active=bool(vdata.get("status", 1)),
                        approved=bool(vdata.get("approved", 1)),
                    )
                    v_created += 1
            else:
                vendor_obj = None

            # Import products
            if skip_products or not vdata.get("products"):
                continue

            for pdata in vdata["products"]:
                pslug = pdata["slug"]
                p_exists = Product.objects.filter(slug=pslug).first()
                if p_exists and not force:
                    continue

                # Scrape product page for name + description
                prod_live = {}
                if not skip_scraping:
                    prod_live = scrape_product_page(pslug)
                    time.sleep(delay)

                prod_name = pdata.get("name") or prod_live.get("name") or pslug.replace("-", " ").title()
                prod_desc = pdata.get("description") or prod_live.get("description", "")
                prod_meta = prod_live.get("meta_description", "")[:490]

                price_str = pdata.get("price", "0") or "0"
                try:
                    price = float(price_str)
                except ValueError:
                    price = None

                # Copy product image
                prod_image = ""
                if not skip_images:
                    prod_image = copy_image(pdata.get("image", ""), "catalog/product/")

                self.stdout.write(
                    f"    📦 [{pslug}] {prod_name[:50]}"
                )

                if not dry_run and vendor_obj:
                    if p_exists and force:
                        p_exists.name = prod_name
                        p_exists.description = prod_desc
                        p_exists.meta_description = prod_meta
                        p_exists.price = price if price else None
                        if prod_image:
                            p_exists.image = prod_image
                        p_exists.save()
                        p_updated += 1
                    else:
                        Product.objects.create(
                            oc_id=pdata["oc_id"],
                            slug=pslug,
                            vendor=vendor_obj,
                            name=prod_name,
                            description=prod_desc,
                            meta_description=prod_meta,
                            price=price if price else None,
                            image=prod_image,
                        )
                        p_created += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Вендоры: создано={v_created}, обновлено={v_updated}, пропущено={v_skip}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"   Продукты: создано={p_created}, обновлено={p_updated}"
        ))
