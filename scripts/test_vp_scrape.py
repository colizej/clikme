import django, os, httpx, sys
sys.path.insert(0, '/Users/colizej/Documents/webApp/clikme')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.chdir('/Users/colizej/Documents/webApp/clikme')
django.setup()
from apps.news.models import NewsItem
from bs4 import BeautifulSoup

item = NewsItem.objects.get(pk=115)
print('source_url:', item.source_url)

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36'}
r = httpx.get(item.source_url, timeout=15, follow_redirects=True, headers=headers)
print('status:', r.status_code)
soup = BeautifulSoup(r.content, 'html.parser')

selectors = [
    'div.article-detail__container', 'div.article-body', 'div.entry-content',
    '.detail--content', '.detail__content', 'div.article__body',
    'div.cms-body', 'div.article-content', 'div[class*="article"]',
]
for sel in selectors:
    found = soup.select_one(sel)
    if found:
        text = found.get_text(separator='\n', strip=True)
        if len(text) > 300:
            print(f'\n=== selector: {sel} ===')
            print(text[:1000])
            break
else:
    # Find the div with most text
    candidates = []
    for tag in soup.find_all(['div', 'article', 'section']):
        t = tag.get_text(separator=' ', strip=True)
        if len(t) > 400:
            candidates.append((len(t), tag.name, ' '.join(str(tag.get('class', ''))[:50].split()), t[:500]))
    candidates.sort(reverse=True)
    for length, name, cls, text in candidates[:5]:
        print(f'\n{name}.{cls} ({length}ch): {text[:300]}')
        print()
