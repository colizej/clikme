"""Fix redirect entries: remove stale Unicode ones + fix wrong '/' destinations."""
import os
import sys
import re
from urllib.parse import quote, unquote

sys.path.insert(0, '/Users/colizej/Documents/webApp/clikme')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.contrib.redirects.models import Redirect
from django.contrib.sites.models import Site
from apps.blog.models import Article
from apps.vendors.models import Vendor, Product
from apps.pages.models import Page
from apps.vendors.management.commands.transliterate_slugs import transliterate, has_cyrillic

site = Site.objects.get_current()

# --- 1. Delete stale Unicode-path redirects (never matched at runtime) ---
unicode_deleted = 0
for r in list(Redirect.objects.filter(site=site)):
    if has_cyrillic(r.old_path):
        print(f"DELETE Unicode entry: {r.old_path!r} → {r.new_path!r}")
        r.delete()
        unicode_deleted += 1

print(f"\nDeleted {unicode_deleted} Unicode-path redirects")

# --- 2. Fix percent-encoded entries pointing to '/' that should point to content ---
fixed = still_wrong = 0
for r in list(Redirect.objects.filter(site=site, new_path='/')):
    decoded_slug = unquote(r.old_path).strip('/')
    if not has_cyrillic(decoded_slug):
        continue  # ASCII slug → '/': leave as is (about_us, search-information etc.)

    # Compute what the Latin slug would be via same transliteration
    latin_slug = transliterate(decoded_slug)
    if not latin_slug:
        print(f"  SKIP (empty transliteration): {decoded_slug!r}")
        continue

    # Look up in all content models
    new_dest = None
    for model_class in (Article, Product, Vendor, Page):
        obj = model_class.objects.filter(slug=latin_slug).first()
        if obj:
            new_dest = f'/{obj.slug}/'
            break

    if new_dest:
        print(f"FIX: {decoded_slug!r} → {new_dest!r}")
        r.new_path = new_dest
        r.save()
        fixed += 1
    else:
        print(f"  NO MATCH for latin slug '{latin_slug}' (from '{decoded_slug}')")
        still_wrong += 1

print(f"\nFixed {fixed} | No match: {still_wrong}")

# --- Show redirect table summary ---
print("\n--- Redirect table summary ---")
total = Redirect.objects.filter(site=site).count()
to_vendors = Redirect.objects.filter(site=site, new_path='/vendors/').count()
to_home = Redirect.objects.filter(site=site, new_path='/').count()
to_content = total - to_vendors - to_home
print(f"  Total: {total}")
print(f"  → /vendors/: {to_vendors}")
print(f"  → /:         {to_home}")
print(f"  → /[content]: {to_content}")

print("\n--- CONTENT redirects sample ---")
for r in Redirect.objects.filter(site=site).exclude(new_path__in=['/', '/vendors/']).order_by('new_path')[:10]:
    print(f"  {unquote(r.old_path)} → {r.new_path}")

