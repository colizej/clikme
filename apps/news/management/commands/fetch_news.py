"""
Management command: fetch_news
Парсит RSS-ленты и HTML-страницы активных NewsSource, сохраняет новинки в NewsItem (статус draft).
Дубли определяются по уникальному полю source_url.

Использование:
    python manage.py fetch_news            # все активные источники
    python manage.py fetch_news --id 3     # конкретный источник по pk
    python manage.py fetch_news --dry-run  # только вывод, без сохранения

Для HTML-источников поле html_selectors должно содержать JSON вида:
    {
        "items":       "article",         # CSS-селектор блока одной новости
        "title":       "h2, h3, a",       # CSS-селектор заголовка внутри блока
        "link":        "a",               # CSS-селектор ссылки (берётся href)
        "link_filter": "/text/",          # (опц.) подстрока, которую должен содержать href
        "summary":     "p",              # (опц.) CSS-селектор описания
        "image":       "img",            # (опц.) CSS-селектор картинки (берётся src)
        "base_url":    "https://site.ru"  # (опц.) база для относительных ссылок
    }
"""
import os
import re
import uuid
import feedparser
import html2text
import httpx
from bs4 import BeautifulSoup
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from apps.news.models import NewsItem, NewsSource

# html2text converter: body_images=False убирает мусорные data: URI
_h2t = html2text.HTML2Text()
_h2t.ignore_links = False
_h2t.body_width = 0          # не переносить строки
_h2t.ignore_images = False
_h2t.images_as_html = False


def _html_to_md(html: str) -> str:
    """Конвертирует HTML → Markdown."""
    if not html:
        return ''
    return _h2t.handle(html).strip()


def _download_image(url: str) -> ContentFile | None:
    """Скачивает изображение по URL, конвертирует в WebP и возвращает (fname, ContentFile) или None."""
    import io
    from PIL import Image

    if not url or not url.startswith(('http://', 'https://')):
        return None
    try:
        r = httpx.get(url, timeout=15, follow_redirects=True, verify=False,
                      headers={'User-Agent': 'Mozilla/5.0 (compatible; ClikMeBot/1.0)'})
        if r.status_code != 200 or not r.headers.get('content-type', '').startswith('image'):
            return None
        # Конвертируем в WebP через Pillow
        img = Image.open(io.BytesIO(r.content))
        if img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')
        buf = io.BytesIO()
        img.save(buf, format='WEBP', quality=85, method=4)
        fname = f'{uuid.uuid4().hex}.webp'
        return fname, ContentFile(buf.getvalue())
    except Exception:
        pass
    return None


def _fetch_og_image(article_url: str) -> str:
    """Забирает og:image (полноразмерное фото) со страницы статьи."""
    if not article_url or not article_url.startswith(('http://', 'https://')):
        return ''
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,*/*;q=0.9',
        'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
    }
    try:
        r = httpx.get(article_url, timeout=12, follow_redirects=True, verify=False,
                      headers=headers)
        if r.status_code != 200:
            return ''
        soup = BeautifulSoup(r.content, 'html.parser')
        for attr in ('og:image', 'twitter:image', 'og:image:secure_url'):
            tag = soup.find('meta', property=attr) or soup.find('meta', attrs={'name': attr})
            if tag:
                img = tag.get('content', '').strip()
                if img.startswith(('http://', 'https://')):
                    return img.replace('&amp;', '&')
    except Exception:
        pass
    return ''


_TRANSLIT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
}


def _transliterate(text: str) -> str:
    """Заменяет кириллицу латиницей."""
    return ''.join(_TRANSLIT.get(ch, ch) for ch in text.lower())


def _make_unique_slug(title: str) -> str:
    """Генерирует уникальный slug из заголовка (кириллица транслитерируется в латиницу)."""
    base = slugify(_transliterate(title))[:230]
    if not base:
        base = 'news'
    slug = base
    counter = 1
    while NewsItem.objects.filter(slug=slug).exists():
        slug = f'{base}-{counter}'
        counter += 1
    return slug


def _matches_keywords(text: str, keywords: list[str]) -> bool:
    """True если хотя бы одно ключевое слово встречается в тексте (без учёта регистра)."""
    lower = text.lower()
    return any(kw.lower() in lower for kw in keywords)


def _strip_html(html: str) -> str:
    """Удаляет HTML-теги из строки."""
    return re.sub(r'<[^>]+>', '', html or '').strip()


# Хвост вида «18.03.2026 20:41 (Читать 3 мин.)» в RSS-сводках 74.ru / Shkulev Media
_RSS_DATE_TAIL_RE = re.compile(
    r'\s*\d{1,2}[./]\d{1,2}[./]\d{2,4}[,\s]*(?:\d{1,2}:\d{2})?\s*'
    r'(?:\(Читать\s+\d+\s+мин\.?\))?\s*$',
    re.IGNORECASE,
)


def _clean_summary(summary: str, title: str) -> str:
    """Удаляет технические артефакты из RSS-сводки.

    74.ru кладёт в <description>: «Рубрика Заголовок ДД.ММ.ГГГГ ЧЧ:ММ (Читать N мин.)»
    После очистки, если оставшийся текст совпадает с заголовком — сводка бесполезна.
    """
    s = _RSS_DATE_TAIL_RE.sub('', summary).strip()
    # Если после очистки хвоста summary == title или является его подстрокой — выбрасываем
    if title and (s == title or s in title or title in s):
        return ''
    return s


class Command(BaseCommand):
    help = 'Парсит RSS-ленты активных источников и сохраняет новости как черновики'

    def add_arguments(self, parser):
        parser.add_argument(
            '--id', type=int, dest='source_id', default=None,
            help='Парсить только конкретный источник (pk NewsSource)'
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Только вывести найденные новости, не сохранять в БД'
        )
        parser.add_argument(
            '--backfill-images', action='store_true',
            help='Скачать картинки для записей, у которых нет локального image'
        )
        parser.add_argument(
            '--refetch-body', action='store_true',
            help='Перезакачать тело статьи для записей с пустым body (e.g. e1.ru → 74.ru)'
        )
        parser.add_argument(
            '--force', action='store_true',
            help='При --refetch-body: перезакачать body даже если оно не пустое'
        )
        parser.add_argument(
            '--source-id', type=int, dest='refetch_source_id', default=None,
            help='При --refetch-body: ограничить по source pk'
        )

    def handle(self, *args, **options):
        if options['backfill_images']:
            self._backfill_images()
            return

        if options['refetch_body']:
            self._refetch_bodies(source_id=options.get('refetch_source_id'), force=options.get('force', False))
            return

        source_id = options['source_id']
        dry_run = options['dry_run']

        qs = NewsSource.objects.filter(is_active=True)
        if source_id:
            qs = qs.filter(pk=source_id)

        if not qs.exists():
            self.stdout.write(self.style.WARNING('Активных источников не найдено.'))
            return

        total_new = 0
        total_skip = 0
        total_filtered = 0

        for source in qs:
            self.stdout.write(f'\n📡 {source.name} — {source.url}')

            keywords = [k.strip() for k in source.keywords.split(',') if k.strip()]

            # ── RSS ──────────────────────────────────────────────────────────
            if source.source_type == NewsSource.RSS:
                new, skip, filtered = self._fetch_rss(source, keywords, dry_run)

            # ── HTML ─────────────────────────────────────────────────────────
            else:
                if not source.html_selectors:
                    self.stdout.write(self.style.WARNING('  ⚠ html_selectors не задан, пропущено.'))
                    continue
                new, skip, filtered = self._fetch_html(source, keywords, dry_run)

            total_new += new
            total_skip += skip
            total_filtered += filtered

            if not dry_run:
                source.last_fetched_at = timezone.now()
                source.save(update_fields=['last_fetched_at'])

            self.stdout.write(
                f'  ✅ новых: {new}  | пропущено (дубли): {skip} | отфильтровано: {filtered}'
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nГотово. Новых новостей: {total_new} | дублей: {total_skip} | отфильтровано: {total_filtered}'
            )
        )

    # ── Backfill: скачать картинки для старых записей ─────────────────────────

    def _backfill_images(self):
        """Скачивает картинки для всех NewsItem, у которых image пустое."""
        from html import unescape
        qs = NewsItem.objects.filter(image='').order_by('pk')
        total = qs.count()
        self.stdout.write(f'Записей без картинки: {total}')
        ok = fail = 0
        for item in qs:
            # 1. Исправляем сохранённый image_url (может содержать &amp;)
            raw_url = unescape(item.image_url or '')
            # 2. Если image_url пустой или нерабочий — пробуем og:image
            if not raw_url or not raw_url.startswith('http'):
                raw_url = _fetch_og_image(item.source_url)
            if raw_url != item.image_url:
                item.image_url = raw_url
                item.save(update_fields=['image_url'])
            if not raw_url:
                self.stdout.write(f'  [{item.pk}] нет URL — пропуск')
                fail += 1
                continue
            result = _download_image(raw_url)
            if result:
                fname, content = result
                item.image.save(fname, content, save=True)
                self.stdout.write(f'  [{item.pk}] ✓ {fname}')
                ok += 1
            else:
                # Последняя попытка: взять og:image заново
                og = _fetch_og_image(item.source_url)
                if og and og != raw_url:
                    result2 = _download_image(og)
                    if result2:
                        fname2, content2 = result2
                        item.image_url = og
                        item.image.save(fname2, content2, save=True)
                        self.stdout.write(f'  [{item.pk}] ✓ og:image {fname2}')
                        ok += 1
                        continue
                self.stdout.write(f'  [{item.pk}] ✗ не скачалось: {raw_url[:80]}')
                fail += 1
        self.stdout.write(self.style.SUCCESS(f'\nСкачано: {ok}  |  не удалось: {fail}'))

    # ── Refetch: перезагрузить тело для статей с пустым body ──────────────────

    def _refetch_bodies(self, source_id: int | None = None, force: bool = False):
        """Перезакачивает body (и при необходимости image) для NewsItem с пустым телом."""
        if force and source_id:
            qs = NewsItem.objects.filter(source_id=source_id).order_by('pk')
        else:
            qs = NewsItem.objects.filter(body='').order_by('pk')
            if source_id:
                qs = qs.filter(source_id=source_id)
        total = qs.count()
        self.stdout.write(f'Записей с пустым body: {total}')
        ok = fail = 0
        for item in qs:
            # Не перезаписываем контент, отредактированный вручную
            if item.is_edited:
                self.stdout.write(f'  [{item.pk}] ⏭ пропуск (is_edited=True): {item.title[:60]}')
                skip_edited = getattr(self, '_skip_edited', 0) + 1
                self._skip_edited = skip_edited
                continue

            body = self._fetch_article_body(item.source_url)
            if not body:
                self.stdout.write(f'  [{item.pk}] ✗ body не получено: {item.source_url[:80]}')
                fail += 1
                continue
            item.body = body
            item.body_md = _html_to_md(body)
            update_fields = ['body', 'body_md']

            # Если нет картинки — вытащить первый img из body
            if not item.image:
                m = re.search(r'<img[^>]+src=["\']((https?://)[^"\']+)["\']', body)
                if m:
                    image_url = m.group(1)
                    item.image_url = image_url
                    update_fields.append('image_url')
                    result = _download_image(image_url)
                    if result:
                        fname, content = result
                        item.image.save(fname, content, save=False)

            item.save(update_fields=update_fields)
            self.stdout.write(f'  [{item.pk}] ✓ body получено ({len(body)} chars): {item.title[:60]}')
            ok += 1
        self.stdout.write(self.style.SUCCESS(f'\nОбновлено: {ok}  |  не удалось: {fail}'))

    # ── RSS парсер ────────────────────────────────────────────────────────────

    _HEADERS = {
        'User-Agent': (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        ),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
    }

    def _fetch_rss(self, source: NewsSource, keywords: list[str], dry_run: bool):
        new = skip = filtered = 0
        try:
            # httpx handles SSL certificates correctly (uses certifi)
            resp = httpx.get(source.url, headers=self._HEADERS, timeout=15, follow_redirects=True)
            resp.raise_for_status()
            # Pass raw bytes so feedparser detects encoding from XML declaration / BOM
            feed = feedparser.parse(resp.content)
        except httpx.HTTPError as e:
            self.stdout.write(self.style.ERROR(f'  ❌ HTTP ошибка: {e}'))
            return 0, 0, 0
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ❌ Ошибка: {e}'))
            return 0, 0, 0

        if not feed.entries:
            self.stdout.write(self.style.ERROR(f'  ❌ Не удалось распарсить RSS (0 записей)'))
            return 0, 0, 0

        for entry in feed.entries:
            url = entry.get('link', '').strip()
            if not url:
                continue

            # Дедупликация
            if NewsItem.objects.filter(source_url=url).exists():
                skip += 1
                continue

            title = _strip_html(entry.get('title', '')).strip()
            summary = _clean_summary(
                _strip_html(entry.get('summary', '') or entry.get('description', '')).strip(),
                title,
            )

            if not title:
                continue

            # Фильтр по ключевым словам
            if keywords and not _matches_keywords(title + ' ' + summary, keywords):
                filtered += 1
                continue

            # ── Полный контент: сначала из RSS content:encoded ────────────────
            body = ''
            rss_content = entry.get('content')
            if rss_content:
                body = rss_content[0].get('value', '')

            # ── Turbo/Yandex контент (vietnews.ru и др.) ──────────────────────
            if not body:
                turbo = entry.get('turbo_content') or entry.get('turbo:content')
                if turbo:
                    body = turbo if isinstance(turbo, str) else ''

            # Очищаем тело, полученное из RSS (category links, date, reading time)
            if body:
                body = self._clean_rss_body(body, title)

            # ── Если RSS-тело — тизер/виджет (мало текста), скачиваем страницу ──
            if body:
                visible = re.sub(r'<[^>]+>', ' ', body)
                visible = re.sub(r'\s+', ' ', visible).strip()
                if len(visible) < 250:
                    body = ''

            # ── Если в RSS нет полного тела — скачиваем страницу статьи ───────
            if not body:
                body = self._fetch_article_body(url)

            # ── Изображение: enclosures/media из RSS (без доп. запроса) → тело → og:image ──
            image_url = ''
            # Сначала проверяем энклозуры и медиа прямо из RSS-данных
            rss_enc = entry.get('enclosures') or []
            rss_media = entry.get('media_content') or []
            for enc in rss_enc:
                if enc.get('type', '').startswith('image') and enc.get('href', '').startswith('http'):
                    image_url = enc['href']
                    break
            if not image_url:
                for mc in rss_media:
                    if mc.get('url', '').startswith('http'):
                        image_url = mc['url']
                        break
            # Второй уровень: первый <img> в теле статьи
            if not image_url and body:
                m = re.search(r'<img[^>]+src=["\']((https?://)[^"\']+)["\']', body)
                if m:
                    image_url = m.group(1)
            # Последний резерв: скачиваем og:image со страницы статьи
            if not image_url:
                image_url = _fetch_og_image(url)
            # Html-decode &amp; в URL
            image_url = image_url.replace('&amp;', '&') if image_url else ''

            if dry_run:
                self.stdout.write(f'  [dry-run] "{title}"')
                new += 1
                continue

            slug = _make_unique_slug(title)
            body_md = _html_to_md(body)
            try:
                item = NewsItem.objects.create(
                    source=source,
                    source_url=url,
                    slug=slug,
                    title=title,
                    title_original=title,
                    summary=summary,
                    summary_original=summary,
                    body=body,
                    body_md=body_md,
                    image_url=image_url,
                    status=NewsItem.DRAFT,
                )
            except Exception:
                skip += 1
                continue
            if image_url:
                result = _download_image(image_url)
                if result:
                    fname, content = result
                    item.image.save(fname, content, save=True)
            new += 1
            self.stdout.write(f'  + {title[:80]}')

        return new, skip, filtered

    # ── Скачать и вырезать тело статьи с оригинального сайта ─────────────────

    # Блоки, которые надо удалить из HTML перед сохранением
    _NOISE_SELECTORS = [
        'script', 'style', 'noscript', 'iframe',
        'header', 'footer', 'nav', 'aside',
        '.ad', '.ads', '.advertisement', '.banner',
        '.related', '.recommended', '.comments',
        '.social', '.share', '.subscribe',
        '[class*="sidebar"]', '[class*="widget"]',
        '[class*="popup"]', '[class*="modal"]',
        '[id*="sidebar"]', '[id*="banner"]',
        # VietnamPlus share toolbar
        '[class*="share"]', '[class*="toolbar"]', '[class*="social"]',
        '[class*="article__social"]', '[class*="article__tags"]',
        '[class*="article__related"]', '[class*="story__related"]',
        'ul.share', '.share-box', '.share-buttons',
        # Shkulev Media (74.ru / ngs22.ru / e1.ru) — ad blocks injected into article body
        '[data-creative]',
    ]

    # Кандидаты на «основной контент» (по убыванию приоритета)
    _ARTICLE_SELECTORS = [
        '#articleBody',               # Shkulev Media (74.ru / e1.ru)
        '[data-article-content]',     # Shkulev Media (74.ru / e1.ru)
        '.fck_detail',                # VNExpress (e.vnexpress.net, vnexpress.net)
        'div.article__body',          # VietnamPlus / TTXVN
        '[itemprop="articleBody"]',
        '.article-body', '.article__body', '.article-content',
        '.post-body', '.post-content', '.entry-content',
        '.news-body', '.news-content', '.news__body',
        '.content-body', '.text-body',
        'article',
        'main',
    ]

    def _clean_rss_body(self, html: str, title: str = '') -> str:
        """Очищает HTML-тело, полученное напрямую из RSS (turbo/content).

        Убирает: рубричные ссылки /category/, плавающие даты «ДД.ММ.ГГГГ ЧЧ:ММ»,
        «(Читать N мин.)», блоки «hidden», блоки «См. также», повтор заголовка.
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Удаляем ссылки на рубрики
        for a in soup.find_all('a', href=True):
            if any(p in a['href'] for p in ('/category/', '/rubric/', '/tag/', '/tags/', '/razdel/')):
                a.decompose()

        # Удаляем блоки «См. также» / «See also»
        for strong in soup.find_all('strong'):
            if re.search(r'также|see also|related|похожие', strong.get_text(), re.IGNORECASE):
                sibling = strong.find_next_sibling('ul')
                if sibling:
                    sibling.decompose()
                strong.decompose()

        # Удаляем скрытые layout-обёртки (class содержит "hidden")
        for el in soup.find_all(class_=lambda c: c and 'hidden' in c.split()):
            el.unwrap()

        result = str(soup)
        # Дата + время (ДД.ММ.ГГГГ ЧЧ:ММ)
        result = re.sub(r'\b\d{1,2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}\b', '', result)
        # «(Читать N мин.)»
        result = re.sub(r'\(Читать\s+\d+\s+мин\.?\)', '', result, flags=re.IGNORECASE)
        # Повтор заголовка как bare text (до первого <p>)
        if title:
            result = result.replace(title.strip(), '', 1)
        # Пустые параграфы
        result = re.sub(r'<p[^>]*>\s*</p>', '', result)
        return result.strip()

    def _fetch_article_body(self, url: str) -> str:
        """Скачивает страницу статьи и возвращает HTML основного контента."""
        # Shkulev Media: e1.ru защищён DDoS-Guard → используем 74.ru (тот же CMS, те же ID статей)
        if 'e1.ru' in url:
            url = re.sub(r'(?:www\.)?e1\.ru', '74.ru', url)
        try:
            resp = httpx.get(url, headers=self._HEADERS, timeout=20, follow_redirects=True)
            resp.raise_for_status()
        except Exception:
            return ''

        soup = BeautifulSoup(resp.content, 'html.parser')

        # Ищем основной блок контента
        article_el = None
        for sel in self._ARTICLE_SELECTORS:
            article_el = soup.select_one(sel)
            if article_el:
                break

        if not article_el:
            return ''

        # Удаляем мусор внутри найденного блока
        for noise in article_el.select(', '.join(self._NOISE_SELECTORS)):
            noise.decompose()

        # Удаляем ссылки на рубрики/категории (не содержательные)
        for a in article_el.find_all('a', href=True):
            if any(p in a['href'] for p in ('/category/', '/rubric/', '/tag/', '/tags/', '/razdel/')):
                a.decompose()

        # Оставляем только разрешённые теги
        allowed = {'p', 'h2', 'h3', 'h4', 'ul', 'ol', 'li',
                   'blockquote', 'strong', 'em', 'a', 'img', 'figure', 'figcaption'}
        for tag in article_el.find_all(True):
            if tag.name not in allowed:
                tag.unwrap()

        # Нормализуем <img>: оставляем src, добавляем lazy
        for img in article_el.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or ''
            # Пропускаем data: URI (SVG-иконки, плейсхолдеры) и относительные пути
            if not src or src.startswith('data:') or not src.startswith('http'):
                img.decompose()
                continue
            for attr in list(img.attrs):
                if attr != 'src':
                    del img.attrs[attr]
            img['src'] = src
            img['loading'] = 'lazy'
            img['class'] = 'w-full rounded-xl my-4'

        # Нормализуем <a>: только href (удаляем javascript: ссылки — соцкнопки)
        for a in article_el.find_all('a'):
            href = a.get('href', '')
            if href.strip().startswith('javascript:'):
                a.decompose()
                continue
            a.attrs = {'href': href, 'target': '_blank', 'rel': 'noopener nofollow'}

        html = str(article_el)
        # Убираем «Читать N мин.» и одиночные даты (ДД.ММ.ГГГГ ЧЧ:ММ)
        html = re.sub(r'\(Читать\s+\d+\s+мин\.?\)', '', html, flags=re.IGNORECASE)
        html = re.sub(r'\b\d{1,2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}\b', '', html)
        # Убираем пустые параграфы
        html = re.sub(r'<p>\s*</p>', '', html)
        return html.strip()

    # ── HTML парсер ───────────────────────────────────────────────────────────

    def _fetch_html(self, source: NewsSource, keywords: list[str], dry_run: bool):
        new = skip = filtered = 0
        sel = source.html_selectors  # type: dict

        item_sel    = sel.get('items', 'article')
        title_sel   = sel.get('title', 'h2, h3')
        link_sel    = sel.get('link', 'a')
        summary_sel = sel.get('summary', '')
        image_sel   = sel.get('image', '')
        link_filter = sel.get('link_filter', '')
        base_url    = sel.get('base_url', '').rstrip('/')

        try:
            resp = httpx.get(source.url, headers=self._HEADERS, timeout=15, follow_redirects=True)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            self.stdout.write(self.style.ERROR(f'  ❌ HTTP ошибка: {e}'))
            return 0, 0, 0

        soup = BeautifulSoup(resp.text, 'html.parser')
        items = soup.select(item_sel)

        if not items:
            self.stdout.write(self.style.WARNING(f'  ⚠ selector «{item_sel}» — 0 элементов.'))
            return 0, 0, 0

        for item in items:
            # ── ссылка ────────────────────────────────────────────────────────
            a_tag = item.select_one(link_sel)
            if not a_tag:
                continue
            href = a_tag.get('href', '').strip()
            if not href:
                continue
            if link_filter and link_filter not in href:
                continue
            if href.startswith('/'):
                href = base_url + href
            elif not href.startswith('http'):
                href = base_url + '/' + href

            # Дедупликация
            if NewsItem.objects.filter(source_url=href).exists():
                skip += 1
                continue

            # ── заголовок ─────────────────────────────────────────────────────
            title_tag = item.select_one(title_sel)
            title = (title_tag.get_text(' ', strip=True) if title_tag
                     else a_tag.get_text(' ', strip=True))
            title = title.strip()
            if not title:
                continue

            # ── описание ──────────────────────────────────────────────────────
            summary = ''
            if summary_sel:
                p = item.select_one(summary_sel)
                if p:
                    summary = p.get_text(' ', strip=True)

            # ── фильтр по ключевым словам ─────────────────────────────────────
            if keywords and not _matches_keywords(title + ' ' + summary, keywords):
                filtered += 1
                continue

            # ── изображение ───────────────────────────────────────────────────
            image_url = ''
            if image_sel:
                img = item.select_one(image_sel)
                if img:
                    image_url = img.get('src', '') or img.get('data-src', '')
                    if image_url and image_url.startswith('/'):
                        image_url = base_url + image_url

            if dry_run:
                self.stdout.write(f'  [dry-run] "{title}"')
                new += 1
                continue

            slug = _make_unique_slug(title)
            # Скачиваем полный текст статьи
            body = self._fetch_article_body(href)
            # Если body нашёл картинку — берём её как превью
            if not image_url and body:
                m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', body)
                if m:
                    image_url = m.group(1)
            body_md = _html_to_md(body)
            news_item = NewsItem.objects.create(
                source=source,
                source_url=href,
                slug=slug,
                title=title,
                title_original=title,
                summary=summary,
                summary_original=summary,
                body=body,
                body_md=body_md,
                image_url=image_url,
                status=NewsItem.DRAFT,
            )
            if image_url:
                result = _download_image(image_url)
                if result:
                    fname, content = result
                    news_item.image.save(fname, content, save=True)
            new += 1
            self.stdout.write(f'  + {title[:80]}')

        return new, skip, filtered
