import re
from bs4 import BeautifulSoup
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


def _clean_article_body(html: str) -> str:
    """Remove duplicate hero image and trailing junk (source credit, tags, see-also) from scraped body."""
    if not html:
        return html
    soup = BeautifulSoup(html, 'html.parser')

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

    # 4. Walk top-level blocks; once we hit a hard trailer marker, cut it and everything after
    top_els = list(soup.find_all(['p', 'div', 'ul', 'ol', 'blockquote', 'h2', 'h3', 'h4', 'h5', 'section', 'aside']))
    cutting = False
    for el in top_els:
        if not el.parent:
            continue
        if cutting:
            el.decompose()
            continue
        text = el.get_text(separator=' ', strip=True).lower()
        if any(text.startswith(m) or (m in text[:80] and len(text) < 400) for m in _TRAILER_MARKERS):
            cutting = True
            el.decompose()

    # 5. Remove blockquotes that are purely link lists (see-also styled as quote)
    for bq in list(soup.find_all('blockquote')):
        if not bq.parent:
            continue
        links = bq.find_all('a')
        text = bq.get_text(strip=True)
        link_text = ' '.join(a.get_text(strip=True) for a in links)
        if links and text and len(link_text) / len(text) > 0.65:
            bq.decompose()

    # 6. Regex fallback: cut HTML at any remaining trailer marker tag
    result = str(soup)
    result = re.sub(
        r'(<[^>]+>[^<]*(?:тэги|тег|теги|tags|статьи по теме|источник)[^<]*<[^>]+>.*)',
        '',
        result,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return result


class NewsListView(ListView):
    model = NewsItem
    template_name = 'news/news_list.html'
    context_object_name = 'news_items'
    paginate_by = 20

    def get_queryset(self):
        return NewsItem.objects.filter(status=NewsItem.PUBLISHED)


class NewsDetailView(DetailView):
    model = NewsItem
    template_name = 'news/news_detail.html'
    context_object_name = 'news_item'

    def get_queryset(self):
        return NewsItem.objects.filter(status=NewsItem.PUBLISHED)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['clean_body'] = _clean_article_body(self.object.body)
        return ctx
