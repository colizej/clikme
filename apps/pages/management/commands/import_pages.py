"""
Management command: import_pages
Импортирует 4 статических страницы из live clikme.ru в модель Page.

Страницы (из oc9a_information category_id=101):
  3  → /politika-konfidencialnosti/  Политика конфиденциальности
  5  → /terms/                        Условия использования
  6  → /delivery/                     Условия доставки
  7  → /pravila-ispolzovania/         Правила использования

Использование:
    python manage.py import_pages
    python manage.py import_pages --dry-run
    python manage.py import_pages --force
"""

import html
import re
import ssl
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from apps.pages.models import Page


# ── Constants ─────────────────────────────────────────────────────────────────

SQL_PATH = Path(settings.BASE_DIR) / "opencart" / "u2971222_ocar341.sql"

PAGES = [
    {"oc_id": 3,  "slug": "politika-konfidencialnosti", "sort_order": 10},
    {"oc_id": 5,  "slug": "terms",                      "sort_order": 20},
    {"oc_id": 6,  "slug": "delivery",                   "sort_order": 30},
    {"oc_id": 7,  "slug": "pravila-ispolzovania",        "sort_order": 40},
]

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


# ── SQL helpers ───────────────────────────────────────────────────────────────

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


def parse_pages_from_sql(sql_text: str) -> dict:
    """Returns {oc_id: {title, content, meta_title, meta_description}} from SQL."""
    page_ids = {p["oc_id"] for p in PAGES}
    result = {}

    raw = _get_insert_values(sql_text, "oc9a_information_description")
    if raw:
        # cols: info_id, language_id, title, header, short_desc,
        #       description, tag, meta_title, meta_description, meta_keyword
        for row in _parse_sql_values(raw):
            if len(row) < 9:
                continue
            if row[1] != "1":
                continue
            oc_id = int(row[0])
            if oc_id not in page_ids:
                continue
            result[oc_id] = {
                "title": _unescape(row[2] or ""),
                "content": _unescape(row[5] or ""),
                "meta_title": _unescape(row[7] or ""),
                "meta_description": _unescape(row[8] or ""),
            }
    return result


# ── Scraper ───────────────────────────────────────────────────────────────────

class PageContentScraper(HTMLParser):
    """Extracts article content and meta from OpenCart information page."""

    def __init__(self):
        super().__init__()
        self._in_h1 = False
        self._in_title = False
        self._h1_done = False
        self._skip_depth = 0
        self._content_depth = 0
        self._in_content = False
        self._content_parts = []
        self._h1_text = ""
        self.title = ""
        self.meta_description = ""
        self.meta_title = ""

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        cls = d.get("class", "") or ""

        if tag == "title":
            self._in_title = True
            return
        if tag == "meta":
            name = d.get("name", "").lower()
            if name == "description":
                self.meta_description = d.get("content", "")
            return
        if tag == "h1" and not self._h1_done:
            self._in_h1 = True
            return
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip_depth += 1
            return

        # Content starts after h1
        if not self._in_content and self._h1_done:
            if tag == "div" and any(c in cls for c in ("col-sm-12", "col-md-12", "entry", "content-page")):
                self._in_content = True
                self._content_depth = 1
                return

        if self._in_content and self._skip_depth == 0:
            self._content_depth += 1
            void_tags = {"br", "img", "hr", "input", "meta", "link", "area", "base", "source"}
            attrs_str = ""
            for k, v in attrs:
                if v is None:
                    attrs_str += f" {k}"
                else:
                    attrs_str += f' {k}="{v}"'
            if tag in void_tags:
                self._content_parts.append(f"<{tag}{attrs_str}>")
                self._content_depth -= 1
            else:
                self._content_parts.append(f"<{tag}{attrs_str}>")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
            return
        if tag == "h1" and self._in_h1:
            self._in_h1 = False
            self._h1_done = True
            return
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._in_content:
            void_tags = {"br", "img", "hr", "input", "meta", "link", "area", "base", "source"}
            if tag not in void_tags:
                self._content_depth -= 1
                if self._content_depth <= 0:
                    self._in_content = False
                    return
                self._content_parts.append(f"</{tag}>")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._in_h1:
            self._h1_text += data
        if self._in_content and self._skip_depth == 0:
            self._content_parts.append(data)

    def handle_entityref(self, name):
        if self._in_content:
            self._content_parts.append(f"&{name};")

    def handle_charref(self, name):
        if self._in_content:
            self._content_parts.append(f"&#{name};")

    @property
    def content(self):
        return "".join(self._content_parts).strip()

    @property
    def h1(self):
        return self._h1_text.strip()


def fetch_url(url: str) -> str:
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (clikme-import/1.0)"}
    )
    with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as resp:
        return resp.read(524288).decode("utf-8", errors="replace")


def scrape_page(slug: str) -> dict:
    """Scrape a page from live clikme.ru. Returns dict with title/content/meta."""
    url = f"https://clikme.ru/{urllib.parse.quote(slug, safe='')}/"
    html_content = fetch_url(url)

    # Extract content between </h1> and next major div
    clean = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"<style[^>]*>.*?</style>", "", clean, flags=re.DOTALL | re.IGNORECASE)

    # Get meta description
    meta_desc = ""
    m = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', html_content, re.IGNORECASE)
    if not m:
        m = re.search(r'<meta\s+content="([^"]*)"\s+name="description"', html_content, re.IGNORECASE)
    if m:
        meta_desc = html.unescape(m.group(1))

    # Get title from <title> tag
    t = re.search(r"<title>([^<]+)</title>", html_content, re.IGNORECASE)
    page_title = html.unescape(t.group(1).strip()) if t else ""
    # Clean " — ClikMe" or " | ClikMe" suffix
    page_title = re.sub(r"\s*[|—–-]+\s*ClikMe.*$", "", page_title).strip()

    # Get h1
    h1 = re.search(r"<h1[^>]*>([^<]+)</h1>", html_content, re.IGNORECASE)
    h1_text = html.unescape(h1.group(1).strip()) if h1 else page_title

    # Extract body content after </h1>
    content_match = re.search(
        r"</h1>\s*(.*?)\s*(?=<div[^>]*(?:class=\"[^\"]*(?:share|social|footer|comment|pagination|related|sidebar)[^\"]*\"|id=\"(?:footer|sidebar|comments)\"))",
        clean, flags=re.DOTALL | re.IGNORECASE
    )
    if not content_match:
        # Fallback: grab everything between first </h1> and </article> or start of footer
        content_match = re.search(
            r"</h1>\s*(.*?)\s*(?:</article>|<footer|<div[^>]*id=\"footer\")",
            clean, flags=re.DOTALL | re.IGNORECASE
        )

    content = ""
    if content_match:
        content = content_match.group(1).strip()
        content = re.sub(r"\n{3,}", "\n\n", content).strip()

    return {
        "title": h1_text or page_title,
        "meta_title": page_title,
        "meta_description": meta_desc,
        "content": content,
    }


# ── Command ───────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Импортировать статические страницы из дампа OpenCart + live clikme.ru"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--force", action="store_true",
                            help="Перезаписать существующие страницы")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        force = options["force"]

        # Parse SQL for what we have
        if SQL_PATH.exists():
            self.stdout.write(f"📂 Читаем SQL дамп…")
            sql_text = SQL_PATH.read_text(encoding="utf-8", errors="replace")
            sql_data = parse_pages_from_sql(sql_text)
            self.stdout.write(f"   Найдено в SQL: {len(sql_data)} страниц")
        else:
            sql_data = {}

        created = updated = skipped = 0

        for page_def in PAGES:
            oc_id = page_def["oc_id"]
            slug = page_def["slug"]
            sort_order = page_def["sort_order"]

            exists = Page.objects.filter(slug=slug).first()
            if exists and not force:
                self.stdout.write(f"  ⏭  [{slug}] уже существует, пропускаем")
                skipped += 1
                continue

            # Try SQL first
            data = sql_data.get(oc_id, {})
            has_sql_content = bool(data.get("content") and len(data["content"]) > 100)

            if not has_sql_content:
                # Scrape from live
                self.stdout.write(f"  🌐 Скрейпим https://clikme.ru/{slug}/ …")
                try:
                    live_data = scrape_page(slug)
                    data = {**data, **{k: v for k, v in live_data.items() if v}}
                    time.sleep(0.3)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"     ⚠ Ошибка скрейпинга: {e}"))

            title = data.get("title") or slug.replace("-", " ").title()
            content = data.get("content", "")
            meta_title = data.get("meta_title", "")
            meta_description = data.get("meta_description", "")
            content_len = len(content)

            self.stdout.write(
                f"  {'📝' if not exists else '🔄'} [{slug}] "
                f"title={title[:60]} content={content_len}chars"
            )

            if dry_run:
                continue

            if exists and force:
                exists.title = title
                exists.content = content
                exists.meta_title = meta_title
                exists.meta_description = meta_description
                exists.sort_order = sort_order
                exists.save()
                updated += 1
            else:
                Page.objects.create(
                    slug=slug,
                    title=title,
                    content=content,
                    meta_title=meta_title,
                    meta_description=meta_description,
                    sort_order=sort_order,
                    is_published=True,
                    noindex=False,
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Готово: создано={created}, обновлено={updated}, пропущено={skipped}"
        ))
