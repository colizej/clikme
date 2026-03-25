"""
Management command: setup_redirects
Reads oc9a_seo_url from OpenCart SQL dump and creates 301 redirects
for URL types that don't exist in Django (categories, missing info pages, etc.)

Usage:
    python manage.py setup_redirects
    python manage.py setup_redirects --dry-run
    python manage.py setup_redirects --clear
"""
import re
from pathlib import Path
from urllib.parse import quote

from django.contrib.redirects.models import Redirect
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand

from apps.blog.models import Article
from apps.pages.models import Page
from apps.vendors.models import Product, Vendor

SQL_FILE = Path(__file__).resolve().parents[4] / 'opencart' / 'u2971222_ocar341.sql'

# Categories → best redirect target
CATEGORY_TARGET = '/vendors/'

# Specific info pages that are missing from Django → redirect to homepage
MISSING_INFO_TARGET = '/'

# These vendor/product slugs are junk (test data) → 404 is fine, no redirect
SKIP_SLUGS = {'test', 'vendor', 'food-store', 'new-product', 'new-product14',
              'skidka-na-20-protsentov', 'skidka-na-10-massage'}


def parse_seo_urls(sql_path):
    text = sql_path.read_text(encoding='utf-8')
    match = re.search(r"INSERT INTO `oc9a_seo_url` VALUES (.*?);", text, re.DOTALL)
    if not match:
        return []
    block = match.group(1)
    return re.findall(r"\(\d+,\d+,\d+,'([^']+)','([^']+)'\)", block)


class Command(BaseCommand):
    help = 'Populate django.contrib.redirects from OpenCart seo_url table'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Show what would be created without writing to DB')
        parser.add_argument('--clear', action='store_true',
                            help='Delete all existing redirects before adding')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        site = Site.objects.get_current()

        if options['clear'] and not dry_run:
            deleted, _ = Redirect.objects.filter(site=site).delete()
            self.stdout.write(f'Deleted {deleted} existing redirects.')

        entries = parse_seo_urls(SQL_FILE)
        self.stdout.write(f'Parsed {len(entries)} entries from oc9a_seo_url')

        created = skipped = already = 0

        for key, raw_slug in entries:
            slug = raw_slug.strip('/')

            if slug in SKIP_SLUGS:
                skipped += 1
                continue

            old_path = f'/{slug}/'

            # --- Determine if this slug is already covered in Django ---
            if key.startswith('product_id='):
                if Product.objects.filter(slug=slug).exists():
                    continue  # already works
                new_path = '/'  # missing test products → homepage

            elif key.startswith('vendor_id='):
                if Vendor.objects.filter(slug=slug).exists():
                    continue  # already works
                new_path = CATEGORY_TARGET

            elif key.startswith('information_id='):
                if (Article.objects.filter(slug=slug).exists() or
                        Page.objects.filter(slug=slug).exists()):
                    continue  # already works
                new_path = MISSING_INFO_TARGET

            elif key.startswith('category_id='):
                new_path = CATEGORY_TARGET

            elif key == 'information/search':
                old_path = '/search-information/'
                new_path = '/'

            else:
                continue

            # --- Check if redirect already exists ---
            # Percent-encode non-ASCII for matching request.get_full_path()
            old_path_encoded = quote(old_path, safe='/')

            # Skip if redirect already exists (check both Unicode and encoded forms)
            if Redirect.objects.filter(
                site=site, old_path__in=[old_path, old_path_encoded]
            ).exists():
                already += 1
                continue

            if dry_run:
                self.stdout.write(f'  [DRY] {old_path_encoded} → {new_path}')
            else:
                Redirect.objects.create(site=site, old_path=old_path_encoded, new_path=new_path)
                self.stdout.write(self.style.SUCCESS(f'  + {old_path_encoded} → {new_path}'))
            created += 1

        label = '[DRY RUN] Would create' if dry_run else 'Created'
        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone. {label}: {created}, already existing: {already}, skipped junk: {skipped}'
            )
        )
