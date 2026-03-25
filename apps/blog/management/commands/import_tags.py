"""
Management command: import_tags
Импортирует теги и категорию блога из дампа OpenCart SQL.

Что делает:
    - Создаёт 9 тегов из поля tag в oc9a_information_description
    - Создаёт 1 категорию «Блог» (если нет)
    - Назначает теги всем статьям (по oc_id)
    - Назначает категорию «Блог» всем 72 статьям

Использование:
    python manage.py import_tags
    python manage.py import_tags --dry-run
"""

import html
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.blog.models import Article, Category, Tag


# ── Constants ─────────────────────────────────────────────────────────────────

SQL_PATH = Path(settings.BASE_DIR) / "opencart" / "u2971222_ocar341.sql"
BLOG_CATEGORY_ID = 90

# Ручные ASCII-слаги для русских тегов (slugify даст пустую строку без unicode)
TAG_SLUG_MAP = {
    "обзор":         "obzor",
    "где покушать":  "gde-pokushat",
    "что смотреть":  "chto-smotret",
    "гид":           "gid",
    "пляжи":         "plyazhi",
    "аренда":        "arenda",
    "медицина":      "medicina",
    "шопинг":        "shoping",
    "буфеты":        "bufety",
}


# ── SQL Parser (same as import_blog.py) ──────────────────────────────────────

def _unescape(s: str) -> str:
    s = s.replace("\\'", "'").replace("\\\\", "\\").replace("\\n", "\n").replace("\\r", "")
    return html.unescape(s)


def _get_insert_values(sql_text: str, table_name: str) -> str:
    marker = f"INSERT INTO `{table_name}` VALUES "
    for line in sql_text.splitlines():
        if line.startswith(marker):
            return line[len(marker):].rstrip(";")
    return ""


def _parse_sql_values(raw_values: str) -> list[list[str]]:
    rows = []
    i = 0
    n = len(raw_values)
    while i < n:
        while i < n and raw_values[i] != '(':
            i += 1
        if i >= n:
            break
        i += 1  # skip '('
        fields = []
        while i < n and raw_values[i] != ')':
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
                i += 1
                buf = []
                while i < n:
                    c = raw_values[i]
                    if c == '\\' and i + 1 < n:
                        buf.append(raw_values[i:i + 2])
                        i += 2
                    elif c == "'" :
                        if i + 1 < n and raw_values[i + 1] == "'":
                            buf.append("'")
                            i += 2
                        else:
                            i += 1
                            break
                    else:
                        buf.append(c)
                        i += 1
                fields.append(_unescape("".join(buf)))
            else:
                j = i
                while i < n and raw_values[i] not in (',', ')'):
                    i += 1
                val = raw_values[j:i].strip()
                fields.append(None if val == 'NULL' else val)
        rows.append(fields)
        while i < n and raw_values[i] != ')':
            i += 1
        i += 1  # skip ')'
    return rows


# ── Data extraction ───────────────────────────────────────────────────────────

def load_tags_from_sql(sql_text: str) -> dict[int, list[str]]:
    """
    Возвращает {oc_id: [tag1, tag2, ...]} для всех информационных статей.
    Поле tag (index 6) — строка с тегами через запятую.
    """
    raw = _get_insert_values(sql_text, "oc9a_information_description")
    if not raw:
        raise CommandError("oc9a_information_description не найдена в SQL")

    result: dict[int, list[str]] = {}
    for row in _parse_sql_values(raw):
        if len(row) < 7:
            continue
        try:
            info_id = int(row[0])
            lang_id = int(row[1])
        except (TypeError, ValueError):
            continue
        if lang_id != 1:   # 1 = Russian
            continue
        tag_field = (row[6] or "").strip()
        if tag_field:
            tags = [t.strip().lower() for t in tag_field.split(",") if t.strip()]
            result[info_id] = tags
    return result


def load_blog_oc_ids(sql_text: str) -> set[int]:
    """Возвращает set oc_id статей блога (category_id=90)."""
    raw = _get_insert_values(sql_text, "oc9a_information_to_category")
    if not raw:
        raise CommandError("oc9a_information_to_category не найдена в SQL")

    blog_ids: set[int] = set()
    # Pattern: (info_id, cat_id, store_id)
    for m in re.finditer(r'\((\d+),(\d+),\d+\)', raw):
        info_id, cat_id = int(m.group(1)), int(m.group(2))
        if cat_id == BLOG_CATEGORY_ID:
            blog_ids.add(info_id)
    return blog_ids


# ── Command ───────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Импортирует теги и категорию блога из дампа OpenCart SQL"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Только показать что будет сделано, без записи в БД"
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        if dry_run:
            self.stdout.write(self.style.WARNING("=== DRY RUN — БД не изменяется ===\n"))

        if not SQL_PATH.exists():
            raise CommandError(f"SQL дамп не найден: {SQL_PATH}")

        sql_text = SQL_PATH.read_text(encoding="utf-8", errors="replace")

        # ── 1. Загрузить данные из SQL ────────────────────────────────────────
        blog_oc_ids = load_blog_oc_ids(sql_text)
        self.stdout.write(f"Статьи блога в SQL: {len(blog_oc_ids)}")

        oc_tags_map = load_tags_from_sql(sql_text)

        # Собираем уникальные теги встречающиеся у блог-статей
        unique_tags: dict[str, int] = {}  # tag_name → count
        for oc_id in blog_oc_ids:
            for tag in oc_tags_map.get(oc_id, []):
                unique_tags[tag] = unique_tags.get(tag, 0) + 1

        self.stdout.write(f"Уникальных тегов: {len(unique_tags)}")
        for tag, cnt in sorted(unique_tags.items(), key=lambda x: -x[1]):
            self.stdout.write(f"  {tag!r:25s} — {cnt} статей")

        # ── 2. Создать категорию «Блог» ───────────────────────────────────────
        blog_category = None
        if dry_run:
            self.stdout.write("\n[dry-run] Создать/получить Category 'Блог'")
        else:
            blog_category, created = Category.objects.get_or_create(
                slug="blog",
                defaults={
                    "name": "Блог",
                    "description": "Статьи о Шри-Ланке: обзоры, гиды, советы",
                    "sort_order": 1,
                    "is_active": True,
                },
            )
            verb = "Создана" if created else "Уже существует"
            self.stdout.write(f"\n{verb} категория: {blog_category.name} (id={blog_category.pk})")

        # ── 3. Создать Tag объекты ────────────────────────────────────────────
        tag_objects: dict[str, Tag] = {}
        self.stdout.write("\nТеги:")
        for tag_name in unique_tags:
            slug = TAG_SLUG_MAP.get(tag_name)
            if not slug:
                slug = slugify(tag_name, allow_unicode=False) or tag_name.replace(" ", "-")
            if dry_run:
                self.stdout.write(f"  [dry-run] Tag(name={tag_name!r}, slug={slug!r})")
            else:
                obj, created = Tag.objects.get_or_create(
                    slug=slug,
                    defaults={"name": tag_name},
                )
                verb = "+" if created else "="
                self.stdout.write(f"  {verb} {tag_name!r} → slug={obj.slug}")
                tag_objects[tag_name] = obj

        # ── 4. Назначить теги и категорию статьям ────────────────────────────
        articles = Article.objects.filter(oc_id__isnull=False)
        self.stdout.write(f"\nСтатьи с oc_id в Django: {articles.count()}")

        tagged_count = 0
        no_tags_count = 0
        category_assigned = 0

        for article in articles:
            oc_id = article.oc_id
            tags_for_article = oc_tags_map.get(oc_id, [])
            changed = False

            if dry_run:
                if tags_for_article:
                    self.stdout.write(
                        f"  [dry-run] {article.slug}: теги={tags_for_article}"
                    )
            else:
                # Назначить категорию
                if blog_category and article.category_id != blog_category.pk:
                    article.category = blog_category
                    article.save(update_fields=["category"])
                    category_assigned += 1

                # Назначить теги
                if tags_for_article:
                    tag_objs = [
                        tag_objects[t] for t in tags_for_article if t in tag_objects
                    ]
                    if tag_objs:
                        article.tags.set(tag_objs)
                        tagged_count += 1
                    else:
                        no_tags_count += 1
                else:
                    no_tags_count += 1

        # ── Итог ─────────────────────────────────────────────────────────────
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS("\n[dry-run] Завершено — БД не изменена")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✓ Завершено:"
                    f"\n  Тегов в БД:          {Tag.objects.count()}"
                    f"\n  Статей с тегами:     {tagged_count}"
                    f"\n  Статей без тегов:    {no_tags_count}"
                    f"\n  Категория назначена: {category_assigned} статьям"
                )
            )
