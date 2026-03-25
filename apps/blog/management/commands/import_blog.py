"""
Management command: import_blog
Импортирует статьи блога из дампа OpenCart SQL.

Что импортирует:
    - 72 статьи из oc9a_information (category_id=90 «blog-soveti-history»)
    - Заголовок, контент, мета-теги из oc9a_information_description
    - Slug из oc9a_seo_url
    - Изображения копирует из opencart/image/ → media/catalog/
    - Marketplace-статьи (ID 18,22,23,24,25,32) помечает noindex=True

Что НЕ импортирует:
    - Статические страницы (category_id=101) — для них будет import_pages
    - Продукты/вендоров — для них будет import_vendors

Использование:
    python manage.py import_blog
    python manage.py import_blog --dry-run
    python manage.py import_blog --force     # перезаписать существующие
    python manage.py import_blog --skip-images
"""

import html
import re
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import make_aware
from django.utils.dateparse import parse_datetime

from apps.blog.models import Article, Category


# ── Constants ─────────────────────────────────────────────────────────────────

SQL_PATH = Path(settings.BASE_DIR) / "opencart" / "u2971222_ocar341.sql"
OC_IMAGE_ROOT = Path(settings.BASE_DIR) / "opencart" / "image"
MEDIA_ROOT = Path(settings.MEDIA_ROOT)

BLOG_CATEGORY_ID = 90        # «blog-soveti-history»
PAGES_CATEGORY_ID = 101      # about_us / политика / условия — не импортируем

# Marketplace-документы — noindex
NOINDEX_IDS = {18, 22, 23, 24, 25, 32}


# ── SQL Parser ────────────────────────────────────────────────────────────────

def _unescape(s: str) -> str:
    """Decode HTML entities и SQL escape sequences."""
    s = s.replace("\\'", "'").replace("\\\\", "\\").replace("\\n", "\n").replace("\\r", "")
    return html.unescape(s)


def _get_insert_values(sql_text: str, table_name: str) -> str:
    """
    Возвращает строку VALUES (...) INSERT-выражения.
    В MySQL-дампе каждый INSERT целиком на одной строке → ищем по startswith.
    """
    marker = f"INSERT INTO `{table_name}` VALUES "
    for line in sql_text.splitlines():
        if line.startswith(marker):
            vals = line[len(marker):]
            return vals.rstrip(";")
    return ""


def _parse_sql_values(raw_values: str) -> list[list[str]]:
    """
    Надёжный парсер SQL VALUES строки вида:
    (val1, 'val2', 'val\\'3'), (val4, ...)
    Обрабатывает экранированные кавычки \\'  внутри строк.
    Возвращает список строк полей (числа — как строки).
    """
    rows = []
    i = 0
    n = len(raw_values)
    while i < n:
        # Ищем начало строки '('
        while i < n and raw_values[i] != '(':
            i += 1
        if i >= n:
            break
        i += 1  # skip '('
        fields = []
        while i < n and raw_values[i] != ')':
            # Skip whitespace/comma
            while i < n and raw_values[i] in (' ', '\t', '\n', '\r'):
                i += 1
            if i >= n:
                break
            if raw_values[i] == ',':
                i += 1
                continue
            if raw_values[i] == ')':
                break
            if raw_values[i] == "'":
                # String field — read until unescaped '
                i += 1
                buf = []
                while i < n:
                    c = raw_values[i]
                    if c == '\\' and i + 1 < n:
                        buf.append(raw_values[i:i+2])
                        i += 2
                    elif c == "'":
                        # Check for '' (escaped quote in MySQL)
                        if i + 1 < n and raw_values[i+1] == "'":
                            buf.append("''")
                            i += 2
                        else:
                            i += 1
                            break
                    else:
                        buf.append(c)
                        i += 1
                fields.append("".join(buf))
            elif raw_values[i] == 'N' and raw_values[i:i+4] == 'NULL':
                fields.append(None)
                i += 4
            else:
                # Number or unquoted value
                j = i
                while i < n and raw_values[i] not in (',', ')', ' ', '\t', '\n'):
                    i += 1
                fields.append(raw_values[j:i])
        # skip closing ')'
        while i < n and raw_values[i] != ')':
            i += 1
        i += 1  # skip ')'
        if fields:
            rows.append(fields)
    return rows


def parse_opencart_sql(sql_text: str) -> list[dict]:
    """Парсит SQL-дамп и возвращает список статей блога."""

    # 1. oc9a_information — основная таблица
    info_rows: dict[int, dict] = {}
    raw = _get_insert_values(sql_text, "oc9a_information")
    if raw:
        # cols: id, image, manufacturer_id, bottom, sort_order, status,
        #       viewed, date_available, date_end, date_added, date_modified
        for row in _parse_sql_values(raw):
            if len(row) < 11:
                continue
            oc_id = int(row[0])
            info_rows[oc_id] = {
                "image": row[1] or "",
                "status": int(row[5] or 0),
                "viewed": int(row[6] or 0),
                "date_added": row[9] or "",
                "date_modified": row[10] or "",
            }

    # 2. oc9a_information_description (language_id=1 = russian)
    desc_rows: dict[int, dict] = {}
    raw = _get_insert_values(sql_text, "oc9a_information_description")
    if raw:
        # cols: info_id, language_id, title, header, short_desc,
        #       description, tag, meta_title, meta_description, meta_keyword
        for row in _parse_sql_values(raw):
            if len(row) < 10:
                continue
            if row[1] != "1":   # language_id=1 only
                continue
            oc_id = int(row[0])
            desc_rows[oc_id] = {
                "title": _unescape(row[2] or ""),
                "header": _unescape(row[3] or ""),
                "short_description": _unescape(row[4] or ""),
                "content": _unescape(row[5] or ""),
                "tag": row[6] or "",
                "meta_title": _unescape(row[7] or ""),
                "meta_description": _unescape(row[8] or ""),
                "meta_keyword": _unescape(row[9] or ""),
            }

    # 3. oc9a_seo_url → information_id → slug
    slug_map: dict[int, str] = {}
    raw = _get_insert_values(sql_text, "oc9a_seo_url")
    if raw:
        for row in re.findall(
            r"\(\d+,\d+,\d+,'information_id=(\d+)','([^']*)'\ *\)", raw
        ):
            slug_map[int(row[0])] = row[1]

    # 4. oc9a_information_to_category → info_id → set(cat_ids)
    cat_map: dict[int, set] = {}
    raw = _get_insert_values(sql_text, "oc9a_information_to_category")
    if raw:
        for row in re.findall(r"\((\d+),(\d+),\d+\)", raw):
            info_id, cat_id = int(row[0]), int(row[1])
            cat_map.setdefault(info_id, set()).add(cat_id)

    # 5. Compose
    articles = []
    for oc_id, info in info_rows.items():
        cats = cat_map.get(oc_id, set())
        if BLOG_CATEGORY_ID not in cats:
            continue   # не блог
        slug = slug_map.get(oc_id)
        if not slug:
            continue   # нет slug → пропускаем
        desc = desc_rows.get(oc_id, {})
        articles.append(
            {
                "oc_id": oc_id,
                "slug": slug,
                "image": info["image"],
                "status": info["status"],
                "viewed": info["viewed"],
                "date_added": info["date_added"],
                "date_modified": info["date_modified"],
                **desc,
            }
        )

    articles.sort(key=lambda a: a["oc_id"])
    return articles


# ── Image helper ──────────────────────────────────────────────────────────────

def copy_image(oc_image_path: str) -> str:
    """
    Копирует изображение из opencart/image/{path} в media/{path}.
    Возвращает относительный путь для ImageField или '' если файл не найден.
    """
    if not oc_image_path:
        return ""
    src = OC_IMAGE_ROOT / oc_image_path
    if not src.exists():
        return ""
    dst = MEDIA_ROOT / oc_image_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        shutil.copy2(src, dst)
    return oc_image_path   # relative path for ImageField


# ── Command ───────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Импортировать статьи блога из дампа OpenCart SQL"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Показать что будет импортировано, но не сохранять",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Обновить уже существующие статьи (по oc_id)",
        )
        parser.add_argument(
            "--skip-images",
            action="store_true",
            help="Не копировать изображения",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        force = options["force"]
        skip_images = options["skip_images"]

        if not SQL_PATH.exists():
            raise CommandError(f"SQL файл не найден: {SQL_PATH}")

        self.stdout.write(f"📂 Читаем {SQL_PATH.name} …")
        sql_text = SQL_PATH.read_text(encoding="utf-8", errors="replace")

        self.stdout.write("🔍 Парсим SQL …")
        articles = parse_opencart_sql(sql_text)
        self.stdout.write(
            self.style.SUCCESS(f"   Найдено {len(articles)} статей в блоге (cat=90)")
        )

        if dry_run:
            self.stdout.write("\n[DRY RUN] Первые 5 статей:")
            for art in articles[:5]:
                self.stdout.write(
                    f"  #{art['oc_id']} /{art['slug']}/  title={art.get('title', '')[:50]}"
                )
            self.stdout.write(f"\n  … итого {len(articles)} статей")
            return

        # ── Создаём/получаем blog-категорию в Django ──────────────────────────
        # Категория нужна только для admin-группировки.
        # URL статей будет /{slug}/ (category=None), чтобы сохранить SEO.
        # ─────────────────────────────────────────────────────────────────────

        created_count = 0
        updated_count = 0
        skipped_count = 0
        image_missing = 0

        for art in articles:
            oc_id = art["oc_id"]
            existing = Article.objects.filter(oc_id=oc_id).first()

            if existing and not force:
                skipped_count += 1
                continue

            # Resolve image
            image_field = ""
            if not skip_images and art.get("image"):
                image_field = copy_image(art["image"])
                if not image_field:
                    image_missing += 1
                    self.stdout.write(
                        self.style.WARNING(f"   ⚠️  Файл не найден: {art['image']}")
                    )

            # Parse dates
            pub_dt = None
            if art.get("date_added"):
                try:
                    pub_dt = make_aware(parse_datetime(art["date_added"]))
                except Exception:
                    pass

            # Build Article dict
            defaults = {
                "slug": art["slug"],
                "title": art.get("title", "") or f"Статья #{oc_id}",
                "subtitle": art.get("header", ""),
                "short_description": art.get("short_description", ""),
                "content": art.get("content", ""),
                "meta_title": art.get("meta_title", "") or art.get("title", ""),
                "meta_description": art.get("meta_description", ""),
                "meta_keywords": art.get("meta_keyword", ""),
                "is_published": art["status"] == 1,
                "noindex": oc_id in NOINDEX_IDS,
                "views_count": art.get("viewed", 0),
                "category": None,  # URL = /{slug}/ — сохраняем оригинальные SEO-URL
            }
            if pub_dt:
                defaults["published_at"] = pub_dt
            if image_field:
                defaults["image"] = image_field

            if existing:
                for k, v in defaults.items():
                    setattr(existing, k, v)
                existing.save()
                updated_count += 1
                verb = "обновлена"
            else:
                Article.objects.create(oc_id=oc_id, **defaults)
                created_count += 1
                verb = "создана"

            self.stdout.write(
                f"  {'📝' if oc_id in NOINDEX_IDS else '✅'} #{oc_id} [{verb}] /{art['slug'][:55]}/"
            )

        # ── Summary ──────────────────────────────────────────────────────────
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(f"✅ Создано:   {created_count}"))
        if updated_count:
            self.stdout.write(self.style.WARNING(f"🔄 Обновлено: {updated_count}"))
        if skipped_count:
            self.stdout.write(f"⏭️  Пропущено: {skipped_count} (используйте --force для обновления)")
        if image_missing:
            self.stdout.write(self.style.WARNING(f"🖼️  Изображений не найдено: {image_missing}"))
        self.stdout.write(
            f"\n📊 Всего статей в БД: {Article.objects.count()}"
        )
        noindex_count = Article.objects.filter(noindex=True).count()
        if noindex_count:
            self.stdout.write(
                self.style.WARNING(f"📵 Noindex статей: {noindex_count} (marketplace docs)")
            )
