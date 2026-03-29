"""
Конвертирует все изображения в блоге в WebP формат.

Использование:
    python manage.py convert_images_to_webp
    python manage.py convert_images_to_webp --dry-run
"""

import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.blog.models import Article, ArticleImage
from apps.vendors.models import Vendor, Product
from apps.news.models import NewsItem
from apps.core.utils.image_utils import convert_to_webp


class Command(BaseCommand):
    help = 'Конвертирует изображения в WebP формат'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет сделано без реальных изменений',
        )
        parser.add_argument(
            '--quality',
            type=int,
            default=85,
            help='Качество WebP (1-100, по умолчанию 85)',
        )
        parser.add_argument(
            '--max-width',
            type=int,
            default=1920,
            help='Максимальная ширина (по умолчанию 1920)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        quality = options['quality']
        max_width = options['max_width']

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN — изменения не будут применены\n'))

        total_converted = 0
        total_skipped = 0
        total_errors = 0

        # Articles
        self.stdout.write('\n📄 Статьи...')
        for article in Article.objects.filter(image__isnull=False).exclude(image=''):
            result = self._process_image(article, 'image', dry_run, quality, max_width)
            if result == 'converted':
                total_converted += 1
            elif result == 'skipped':
                total_skipped += 1
            elif result == 'error':
                total_errors += 1

        # Article Images (extra images)
        self.stdout.write('\n🖼 Дополнительные изображения статей...')
        for img in ArticleImage.objects.filter(image__isnull=False).exclude(image=''):
            result = self._process_image(img, 'image', dry_run, quality, max_width)
            if result == 'converted':
                total_converted += 1
            elif result == 'skipped':
                total_skipped += 1
            elif result == 'error':
                total_errors += 1

        # Vendors
        self.stdout.write('\n🏪 Компании...')
        for vendor in Vendor.objects.filter(image__isnull=False).exclude(image=''):
            result = self._process_image(vendor, 'image', dry_run, quality, max_width)
            if result == 'converted':
                total_converted += 1
            elif result == 'skipped':
                total_skipped += 1
            elif result == 'error':
                total_errors += 1

        # Products
        self.stdout.write('\n📦 Товары...')
        for product in Product.objects.filter(image__isnull=False).exclude(image=''):
            result = self._process_image(product, 'image', dry_run, quality, max_width)
            if result == 'converted':
                total_converted += 1
            elif result == 'skipped':
                total_skipped += 1
            elif result == 'error':
                total_errors += 1

        # News
        self.stdout.write('\n📰 Новости...')
        for news in NewsItem.objects.filter(image__isnull=False).exclude(image=''):
            result = self._process_image(news, 'image', dry_run, quality, max_width)
            if result == 'converted':
                total_converted += 1
            elif result == 'skipped':
                total_skipped += 1
            elif result == 'error':
                total_errors += 1

        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'\n✅ Конвертировано: {total_converted}'))
        self.stdout.write(f'⏭ Пропущено (.webp): {total_skipped}')
        if total_errors:
            self.stdout.write(self.style.ERROR(f'❌ Ошибок: {total_errors}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'❌ Ошибок: {total_errors}'))

    def _process_image(self, obj, field_name, dry_run, quality, max_width):
        """Обрабатывает одно изображение"""
        try:
            image_field = getattr(obj, field_name, None)
            if not image_field or not image_field.name:
                return 'skipped'

            # Пропускаем уже WebP
            if image_field.name.lower().endswith('.webp'):
                return 'skipped'

            # Проверяем существование файла
            full_path = settings.MEDIA_ROOT / image_field.name
            if not full_path.exists():
                return 'skipped'

            # Конвертируем
            if dry_run:
                self.stdout.write(f'  🔄 {image_field.name} → {Path(image_field.name).stem}.webp')
                return 'converted'
            else:
                new_path = convert_to_webp(image_field.name, quality, max_width)
                if new_path != image_field.name:
                    setattr(obj, field_name, new_path)
                    obj.save(update_fields=[field_name])
                    self.stdout.write(f'  ✅ {Path(image_field.name).name} → {Path(new_path).name}')
                    return 'converted'
                return 'skipped'

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ❌ Ошибка: {e}'))
            return 'error'
