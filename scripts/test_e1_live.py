import django, os, httpx, re, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
sys.path.insert(0, '/Users/colizej/Documents/webApp/clikme')
os.chdir('/Users/colizej/Documents/webApp/clikme')
django.setup()
from apps.news.models import NewsItem
from bs4 import BeautifulSoup

item = NewsItem.objects.filter(source__name__icontains='E1').order_by('-published_at').first()
url = re.sub(r'(?:www\.)?e1\.ru', '74.ru', item.source_url)
print('URL:', url)

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36'}
r = httpx.get(url, timeout=20, follow_redirects=True, headers=headers)
print('status:', r.status_code)
soup = BeautifulSoup(r.content, 'html.parser')

# Check ads
ads = soup.find_all(attrs={'data-creative': True})
print(f'\ndata-creative ads: {len(ads)}')
for ad in ads[:4]:
    print(f'  {ad.name} data-creative={ad.get("data-creative")!r}')

# uiArticleBlockText blocks
blocks = soup.select('[class*="uiArticleBlockText"]')
print(f'\nuiArticleBlockText blocks: {len(blocks)}')
for b in blocks[:2]:
    print(f'  cls={b.get("class")} => {b.get_text(strip=True)[:120]}')

# articleBody
artbody = soup.select_one('#articleBody')
print(f'\n#articleBody found: {bool(artbody)}, len: {artbody and len(artbody.get_text(strip=True))}')

# combined text from uiArticleBlockText
if blocks:
    combined = ' '.join(b.get_text(separator=' ', strip=True) for b in blocks)
    combined = re.sub(r'\s+', ' ', combined).strip()
    print(f'\nCombined uiArticleBlockText text ({len(combined)} chars):')
    print(combined[:600])

# VietnamPlus - main-col
vp = NewsItem.objects.filter(source__name__icontains='VietnamPlus', status='published').order_by('-pk').first()
if vp:
    vp_url = vp.source_url
    print(f'\n\n=== VietnamPlus pk={vp.pk} ===')
    r2 = httpx.get(vp_url, timeout=15, follow_redirects=True, headers=headers)
    soup2 = BeautifulSoup(r2.content, 'html.parser')
    mc = soup2.select_one('.main-col.content-col, .main-col, [class*="main-col"]')
    print(f'main-col found: {bool(mc)}, len: {mc and len(mc.get_text(strip=True))}')
    if mc:
        print(mc.get_text(separator=' ', strip=True)[:400])
