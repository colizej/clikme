"""
Management command: transliterate_slugs
Converts Cyrillic slugs to Latin transliteration for all content models
(Article, Vendor, Product, Page), then creates 301 redirects from old → new.

Usage:
    python manage.py transliterate_slugs --dry-run
    python manage.py transliterate_slugs
"""
import re
from urllib.parse import quote

from django.contrib.redirects.models import Redirect
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.blog.models import Article
from apps.pages.models import Page
from apps.vendors.models import Product, Vendor

# Russian → Latin transliteration table (passport/ICAO-style)
TRANSLIT_TABLE = str.maketrans({
    'а': 'a',  'б': 'b',  'в': 'v',  'г': 'g',  'д': 'd',
    'е': 'e',  'ё': 'yo', 'ж': 'zh', 'з': 'z',  'и': 'i',
    'й': 'y',  'к': 'k',  'л': 'l',  'м': 'm',  'н': 'n',
    'о': 'o',  'п': 'p',  'р': 'r',  'с': 's',  'т': 't',
    'у': 'u',  'ф': 'f',  'х': 'kh', 'ц': 'ts', 'ч': 'ch',
    'ш': 'sh', 'щ': 'sch','ъ': '',   'ы': 'y',  'ь': '',
    'э': 'e',  'ю': 'yu', 'я': 'ya',
    'А': 'A',  'Б': 'B',  'В': 'V',  'Г': 'G',  'Д': 'D',
    'Е': 'E',  'Ё': 'Yo', 'Ж': 'Zh', 'З': 'Z',  'И': 'I',
    'Й': 'Y',  'К': 'K',  'Л': 'L',  'М': 'M',  'Н': 'N',
    'О': 'O',  'П': 'P',  'Р': 'R',  'С': 'S',  'Т': 'T',
    'У': 'U',  'Ф': 'F',  'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch',
    'Ш': 'Sh', 'Щ': 'Sch','Ъ': '',   'Ы': 'Y',  'Ь': '',
    'Э': 'E',  'Ю': 'Yu', 'Я': 'Ya',
})


def has_cyrillic(s):
    return bool(re.search('[а-яёА-ЯЁ]', s))


def transliterate(text):
    """Transliterate Cyrillic text to Latin, then slugify."""
    latin = text.translate(TRANSLIT_TABLE)
    return slugify(latin)


def make_unique_slug(base_slug, model_class, exclude_pk=None):
    """Ensure the generated slug doesn't conflict with existing DB records."""
    slug = base_slug
    qs = model_class.objects.filter(slug=slug)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    counter = 1
    while qs.exists():
        slug = f'{base_slug}-{counter}'
        qs = model_class.objects.filter(slug=slug).exclude(pk=exclude_pk) if exclude_pk \
            else model_class.objects.filter(slug=slug)
        counter += 1
    return slug


class Command(BaseCommand):
    help = 'Transliterate Cyrillic slugs to Latin and create 301 redirects'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Show changes without writing to DB')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        site = Site.objects.get_current()

        models = [
            (Article, 'Article'),
            (Vendor, 'Vendor'),
            (Product, 'Product'),
            (Page, 'Page'),
        ]

        total_changed = 0

        for model_class, label in models:
            items = [obj for obj in model_class.objects.all() if has_cyrillic(obj.slug)]
            if not items:
                continue

            self.stdout.write(f'\n{label}: {len(items)} Cyrillic slugs')

            for obj in items:
                old_slug = obj.slug
                new_slug_base = transliterate(old_slug)

                if not new_slug_base:
                    self.stdout.write(self.style.WARNING(
                        f'  SKIP (empty after transliteration): {old_slug}'))
                    continue

                new_slug = make_unique_slug(new_slug_base, model_class, exclude_pk=obj.pk)
                old_path = f'/{old_slug}/'
                new_path = f'/{new_slug}/'
                # Percent-encode so it matches request.get_full_path()
                old_path_encoded = quote(old_path, safe='/')

                if dry_run:
                    conflict = ' [CONFLICT → renamed]' if new_slug != new_slug_base else ''
                    self.stdout.write(f'  {old_path} → {new_path}{conflict}')
                else:
                    obj.slug = new_slug
                    obj.save(update_fields=['slug'])

                    # update_or_create overrides any wrong redirect setup_redirects may have set
                    Redirect.objects.update_or_create(
                        site=site,
                        old_path=old_path_encoded,
                        defaults={'new_path': new_path},
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f'  {old_path_encoded} → {new_path}'))

                total_changed += 1

        label = '[DRY RUN] Would update' if dry_run else 'Updated'
        self.stdout.write(self.style.SUCCESS(
            f'\n{label}: {total_changed} slugs total'))
