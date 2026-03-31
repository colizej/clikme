import re
from datetime import timedelta
from bs4 import BeautifulSoup
from django.db.models import F, Count
from django.utils import timezone
from django.views.generic import ListView, DetailView
from .models import NewsItem

_TRAILER_MARKERS = (
    'источник:', 'источник —', 'источник -',
    'тэги:', 'тэги ', 'теги:', 'теги ', 'тег:', 'tags:', 'tags ',
    'статьи по теме', 'related articles',
)

_SEE_ALSO_MARKERS = (
    'см. также', 'смотрите также', 'статьи по теме', 'читайте также', 'по теме:',
)


def _clean_article_body(html: str, title: str = '') -> str:
    """Remove duplicate hero image and trailing junk (source credit, tags, see-also) from scraped body."""
    if not html:
        return html

    # 0. Strip Vue SSR hydration markers and all HTML comments
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)

    soup = BeautifulSoup(html, 'html.parser')

    # 0a. Remove share/social toolbars (e.g. VietnamPlus "Zalo Facebook Twitter...")
    for el in list(soup.find_all(class_=True)):
        cls = ' '.join(el.get('class', []))
        if any(k in cls.lower() for k in ('share', 'social', 'toolbar', 'related', 'tags')):
            el.decompose()

    # 0b. Remove javascript:void(0) share links (VietnamPlus Share toolbar)
    for a in list(soup.find_all('a', href=True)):
        if a['href'].strip().startswith('javascript:'):
            a.decompose()

    # 0c. Remove ad blocks injected into article body (Shkulev Media: 74.ru, ngs22.ru)
    for el in list(soup.find_all(attrs={'data-creative': True})):
        el.decompose()

    # 0b. Remove comment-count links (e.g. "4 комментария")
    for a in list(soup.find_all('a', href=True)):
        if 'comment' in a['href'].lower():
            a.decompose()

    # 0c. Remove social-share lists (ul/ol whose every <li> has no visible text)
    for lst in list(soup.find_all(['ul', 'ol'])):
        if not lst.parent:
            continue
        items = lst.find_all('li')
        if items and all(not li.get_text(strip=True) for li in items):
            lst.decompose()

    # 0d. Remove empty inline wrappers left by stripped comments
    for tag in list(soup.find_all(['span', 'div', 'li'])):
        if not tag.parent:
            continue
        if not tag.get_text(strip=True) and not tag.find(['img', 'figure', 'iframe']):
            tag.decompose()

    # 1. Remove the very first <figure> or <img> — duplicates the hero shown above
    first_media = soup.find(['figure', 'img'])
    if first_media:
        first_media.decompose()

    # 2. Remove "СМ. ТАКЖЕ" blocks anywhere — label element + following list
    for el in list(soup.find_all(['p', 'div', 'strong', 'b', 'h3', 'h4', 'span'])):
        if not el.parent:
            continue
        text = el.get_text(separator=' ', strip=True).lower()
        if any(m in text for m in _SEE_ALSO_MARKERS):
            nxt = el.find_next_sibling()
            if nxt and nxt.name in ('ul', 'ol'):
                nxt.decompose()
            el.decompose()

    # 3. Remove standalone see-also lists (ul/ol where all items are links)
    for lst in list(soup.find_all(['ul', 'ol'])):
        if not lst.parent:
            continue
        items = lst.find_all('li')
        if items and all(li.find('a') for li in items):
            lst.decompose()

    # 4. Walk top-level blocks from the END; cut trailing source/tag markers.
    #    Only remove an element if it is SHORT (≤120 visible chars) — real content
    #    paragraphs with inline 'Источник: Name' photo captions are much longer.
    top_els = list(soup.find_all(['p', 'div', 'ul', 'ol', 'blockquote', 'h2', 'h3', 'h4', 'h5', 'section', 'aside']))
    # Compute total visible length to detect trailer zone (last ~15%)
    total_visible = len(soup.get_text(strip=True))
    seen_chars = 0
    cutting = False
    for el in top_els:
        if not el.parent:
            continue
        if cutting:
            el.decompose()
            continue
        text = el.get_text(separator=' ', strip=True)
        text_lower = text.lower()
        text_len = len(text)
        is_short = text_len <= 120
        if is_short and any(text_lower.startswith(m) for m in _TRAILER_MARKERS):
            cutting = True
            el.decompose()
            continue
        seen_chars += text_len

    # 5. Remove blockquotes that are purely link lists (see-also styled as quote)
    for bq in list(soup.find_all('blockquote')):
        if not bq.parent:
            continue
        links = bq.find_all('a')
        text = bq.get_text(strip=True)
        link_text = ' '.join(a.get_text(strip=True) for a in links)
        if links and text and len(link_text) / len(text) > 0.65:
            bq.decompose()

    # 6. (Step 6 removed — regex-based 'источник' matching caused false positives
    #     on inline photo captions like 'Источник: Photographer Name')
    result = str(soup)

    # 7. If remaining visible text is basically just the title (< 80 chars or == title)
    #    the body is a teaser-only feed — return '' so template falls back to summary.
    if title:
        visible = re.sub(r'<[^>]+>', ' ', result).strip()
        visible = re.sub(r'\s+', ' ', visible)
        if len(visible) < 80 or visible.lower().strip() == title.lower().strip():
            return ''

    return result


def _clean_summary_tail(summary: str, body_html: str) -> str:
    """Remove related-article titles that got concatenated at the end of a summary.

    Some RSS feeds (e.g. VietnamPlus) include related article widgets in content:encoded.
    Their heading texts end up appended to the summary without separators.
    We extract heading texts from the body and use the first match as a cut point.
    """
    if not summary or not body_html:
        return summary
    soup = BeautifulSoup(body_html, 'html.parser')
    # Collect all heading / title texts from the body (related article widgets)
    heading_texts = []
    for tag in soup.find_all(['h1', 'h2', 'h3', 'h4']):
        t = tag.get_text(strip=True)
        if len(t) > 10:
            heading_texts.append(t)
    # Also collect link texts that look like article titles (longish links)
    for a in soup.find_all('a'):
        t = a.get_text(strip=True)
        if len(t) > 20:
            heading_texts.append(t)
    # Find the earliest cut position in summary
    cut_at = len(summary)
    for heading in heading_texts:
        pos = summary.find(heading)
        if pos != -1 and pos < cut_at:
            cut_at = pos
    return summary[:cut_at].strip()


class NewsListView(ListView):
    model = NewsItem
    template_name = 'news/news_list.html'
    context_object_name = 'news_items'
    paginate_by = 20

    def get_queryset(self):
        now = timezone.now()
        qs = NewsItem.objects.filter(
            status=NewsItem.PUBLISHED,
            published_at__lte=now,
        )
        tag = self.request.GET.get('tag', '').strip()
        if tag == 'new':
            qs = qs.filter(published_at__gte=now - timedelta(hours=48))
        elif tag:
            qs = qs.filter(tag=tag)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        now = timezone.now()
        ctx['all_tags'] = (
            NewsItem.objects
            .filter(status=NewsItem.PUBLISHED, published_at__lte=now)
            .exclude(tag='')
            .values('tag')
            .annotate(cnt=Count('id'))
            .order_by('-cnt')
        )
        new_cnt = NewsItem.objects.filter(
            status=NewsItem.PUBLISHED,
            published_at__gte=now - timedelta(hours=48),
            published_at__lte=now,
        ).count()
        ctx['new_cnt'] = new_cnt
        ctx['total_cnt'] = NewsItem.objects.filter(
            status=NewsItem.PUBLISHED, published_at__lte=now
        ).count()
        ctx['active_tag'] = self.request.GET.get('tag', '').strip()
        return ctx


class NewsDetailView(DetailView):
    model = NewsItem
    template_name = 'news/news_detail.html'
    context_object_name = 'news_item'

    def get_queryset(self):
        return NewsItem.objects.filter(
            status=NewsItem.PUBLISHED,
            published_at__lte=timezone.now(),
        )

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        NewsItem.objects.filter(pk=self.object.pk).update(views_count=F('views_count') + 1)
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        obj = self.object
        clean_body = _clean_article_body(obj.body, obj.title)
        ctx['clean_body'] = clean_body
        # When body is a teaser (empty after cleaning), also clean summary tail:
        # extract related-article headings from the body and truncate summary before them.
        if not clean_body and obj.summary and obj.body:
            ctx['clean_summary'] = _clean_summary_tail(obj.summary, obj.body)
        ctx['prev_news'] = (
            NewsItem.objects
            .filter(status=NewsItem.PUBLISHED, published_at__lt=obj.published_at)
            .order_by('-published_at')
            .first()
        )
        ctx['next_news'] = (
            NewsItem.objects
            .filter(status=NewsItem.PUBLISHED, published_at__gt=obj.published_at)
            .order_by('published_at')
            .first()
        )
        return ctx
