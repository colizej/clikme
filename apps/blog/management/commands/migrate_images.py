"""
Management command: migrate_images
Копирует изображения из opencart/image/catalog/ → media/catalog/
и переписывает абсолютные URL https://clikme.ru/image/... → /media/...
в content статей.

Использование:
    python manage.py migrate_images
    python manage.py migrate_images --dry-run
    python manage.py migrate_images --skip-copy   # только rewrite URLs
    python manage.py migrate_images --skip-rewrite # только copy
"""

import re
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.blog.models import Article


OC_IMAGE_ROOT = Path(settings.BASE_DIR) / "opencart" / "image"
MEDIA_ROOT = Path(settings.MEDIA_ROOT)

# Directories to copy entirely
COPY_DIRS = [
    "catalog/Blog Images",
    "catalog/multivendor",
    "catalog/Trip.com",
    "catalog/category",
]


class Command(BaseCommand):
    help = "Копировать изображения OpenCart → media/ и переписать URL в контенте"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--skip-copy", action="store_true",
                            help="Пропустить копирование файлов")
        parser.add_argument("--skip-rewrite", action="store_true",
                            help="Пропустить перезапись URL в контенте")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        skip_copy = options["skip_copy"]
        skip_rewrite = options["skip_rewrite"]

        # ── 1. Copy image directories ─────────────────────────────────────────
        if not skip_copy:
            self.stdout.write("📁 Копируем изображения…")
            total_copied = 0

            for rel_dir in COPY_DIRS:
                src_dir = OC_IMAGE_ROOT / rel_dir
                dst_dir = MEDIA_ROOT / rel_dir

                if not src_dir.exists():
                    self.stdout.write(f"  ⚠ Не найдено: {src_dir}")
                    continue

                files = list(src_dir.rglob("*"))
                img_files = [
                    f for f in files
                    if f.is_file() and f.suffix.lower() in
                    {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
                ]

                for src in img_files:
                    rel_path = src.relative_to(OC_IMAGE_ROOT)
                    dst = MEDIA_ROOT / rel_path
                    if dst.exists():
                        continue
                    if not dry_run:
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dst)
                    total_copied += 1

                self.stdout.write(f"  ✅ {rel_dir}: {len(img_files)} файлов")

            self.stdout.write(f"   Скопировано (новых): {total_copied}")

        # ── 2. Rewrite URLs in article content ────────────────────────────────
        if not skip_rewrite:
            self.stdout.write("\n🔗 Переписываем URL изображений в статьях…")

            # Pattern: https://clikme.ru/image/catalog/... → /media/catalog/...
            # Also handles http://
            pattern = re.compile(
                r'(https?://clikme\.ru)/image/',
                re.IGNORECASE
            )
            replacement = "/media/"

            articles_updated = 0
            total_replacements = 0

            for article in Article.objects.all():
                if not article.content:
                    continue
                new_content, n = pattern.subn(replacement, article.content)
                if n > 0:
                    total_replacements += n
                    articles_updated += 1
                    self.stdout.write(
                        f"  ✏  #{article.oc_id} [{article.slug[:40]}]: {n} замен"
                    )
                    if not dry_run:
                        article.content = new_content
                        article.save(update_fields=["content"])

            self.stdout.write(
                f"\n   Статей обновлено: {articles_updated}, "
                f"замен всего: {total_replacements}"
            )

        if dry_run:
            self.stdout.write(self.style.WARNING("\n⚠ DRY RUN — изменения не применены"))
        else:
            self.stdout.write(self.style.SUCCESS("\n✅ Готово"))
