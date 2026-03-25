# Архитектура Django-проекта — clikme.ru

**Стек:** Django 6.0.3, Python 3.14, SQLite, Tailwind CSS v4 (standalone CLI)

> **Статус:** Фаза 1 завершена — 72 статьи, 39 вендоров, 224 продукта, 4 страницы,
> 71 SEO-редирект. Платформа готова к публикации (см. блокеры в ROADMAP.md).

## Структура проекта

```
clikme/
│
├── config/                     ← Настройки проекта
│   ├── settings.py             ← Все настройки, SITE_ID=1
│   ├── urls.py
│   └── wsgi.py
│
├── apps/
│   ├── blog/                   ← 72 статьи (импортированы из OpenCart)
│   │   └── management/commands/
│   │       ├── import_blog.py
│   │       └── setup_redirects.py
│   ├── vendors/                ← 39 вендоров + 224 продукта
│   │   └── management/commands/
│   │       ├── import_vendors.py
│   │       └── transliterate_slugs.py
│   ├── news/                   ← NewsSource/NewsItem (источники не настроены)
│   ├── pages/                  ← 4 статические страницы + setup_redirects command
│   ├── users/                  ← AbstractUser (user_type, points, telegram_id)
│   └── newsletter/             ← Subscriber модель + SubscribeView
│
├── templates/
│   ├── base.html
│   ├── blog/
│   │   ├── article_detail.html
│   │   ├── category_list.html
│   │   └── home.html
│   ├── vendors/
│   │   ├── vendor_detail.html
│   │   ├── product_detail.html
│   │   └── vendor_list.html
│   ├── news/
│   │   ├── news_list.html
│   │   └── news_detail.html
│   ├── pages/
│   │   └── page_detail.html
│   ├── components/             ← Переиспользуемые компоненты ({% include %})
│   │   └── cookie_banner.html  ← ✅ GDPR cookie consent (EU-сервер)
│   ├── 404.html
│   └── 500.html
│
├── static/
│   ├── css/
│   ├── js/
│   └── img/
│
├── media/                      ← 518 изображений из OpenCart (не в git)
│   └── catalog/
│
├── scripts/
│   ├── audit_slugs.py          ← паритет-чек URL OpenCart vs Django
│   └── fix_redirects.py        ← утилита починки редиректов
│
├── requirements.txt
├── manage.py
└── .env.example
```

---

## Модели данных

### apps/blog/models.py

```python
class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)
    description = models.TextField(blank=True)
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(max_length=500, blank=True)
    image = models.ImageField(upload_to='catalog/category/', blank=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Tag(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

class Article(models.Model):
    # Идентификатор
    oc_id = models.IntegerField(null=True, blank=True)  # ID из OpenCart (для дебага)
    slug = models.SlugField(unique=True, max_length=255) # ТОЧНЫЙ slug из oc_seo_url

    # Контент
    title = models.CharField(max_length=500)
    subtitle = models.CharField(max_length=500, blank=True)
    short_description = models.TextField(blank=True)
    content = models.TextField()                         # HTML из OpenCart
    image = models.ImageField(upload_to='catalog/', blank=True)

    # SEO (перенос напрямую из oc_information_description)
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(max_length=500, blank=True)
    meta_keywords = models.CharField(max_length=500, blank=True)

    # Связи
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    tags = models.ManyToManyField(Tag, blank=True)
    author = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)

    # Статус
    is_published = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    # Даты
    published_at = models.DateTimeField()      # из OpenCart date_available
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Метрики
    views_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-published_at']

    def get_absolute_url(self):
        if self.category:
            return f'/{self.category.slug}/{self.slug}/'
        return f'/{self.slug}/'
```

### apps/news/models.py

```python
class NewsSource(models.Model):
    """Источник новостей: RSS-лента или HTML-сайт """
    name = models.CharField(max_length=255)
    url = models.URLField(unique=True)
    RSS = 'rss'
    HTML = 'html'
    SOURCE_TYPES = [(RSS, 'RSS-лента'), (HTML, 'HTML-страница')]
    source_type = models.CharField(max_length=10, choices=SOURCE_TYPES, default=RSS)

    # для HTML: CSS-селекторы полей (JSON: {"items": ".news-item", "title": "h2", ...})
    html_selectors = models.JSONField(default=dict, blank=True)

    source_language = models.CharField(max_length=10, default='ru')  # vi, en, ru и т..д.
    needs_translation = models.BooleanField(default=False)  # True → AI переводит на RU

    is_active = models.BooleanField(default=True)
    last_fetched_at = models.DateTimeField(null=True, blank=True)


class NewsItem(models.Model):
    source = models.ForeignKey(NewsSource, on_delete=models.SET_NULL,
                               null=True, related_name='items')
    source_url = models.URLField(unique=True)           # дедупликация по этому полю
    slug = models.SlugField(unique=True, max_length=255, blank=True)

    # Оригинальные данные (на языке источника)
    title_original = models.CharField(max_length=500, blank=True)
    summary_original = models.TextField(blank=True)

    # Финальные данные (после AI-обработки или напрямую)
    title = models.CharField(max_length=500)
    summary = models.TextField(blank=True)

    image_url = models.URLField(blank=True)
    image = models.ImageField(upload_to='news/', blank=True)

    # AI-обработка
    ai_processed = models.BooleanField(default=False)   # True = AI уже обработал
    ai_model_used = models.CharField(max_length=50, blank=True)  # 'gpt-4o-mini' и т..д.

    DRAFT = 'draft'
    PUBLISHED = 'published'
    REJECTED = 'rejected'
    STATUSES = [(DRAFT, 'Черновик'), (PUBLISHED, 'Опубликовано'), (REJECTED, 'Отклонено')]
    status = models.CharField(max_length=15, choices=STATUSES, default=DRAFT)

    telegram_message_id = models.CharField(max_length=50, blank=True)

    fetched_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-fetched_at']
```

---

### Архитектура fetch_news

```
apps/news/management/commands/
├── fetch_news.py          ← главная команда
├── publish_news.py        ← публикация из admin-action
apps/news/
├── fetchers/
│   ├── base.py            ← абстрактный класс BaseFetcher
│   ├── rss.py             ← RSS-парсер (feedparser)
│   └── html.py            ← HTML-парсер (BeautifulSoup4)
├── ai.py                  ← AI-обработка: перевод + рерайт + категоризация
├── telegram.py            ← публикация в Telegram (без доп. библиотек)
├── admin.py               ← кнопки "Опубликовать" / "Отклонить"
```

**Полный рабочий процесс:**
```
┌─────────────────────────┐
│ python manage.py fetch_news │
└───────────┬─────────────┘
           ↓
 для каждого NewsSource
           ↓
  RSS? → feedparser → статьи
  HTML? → httpx + BeautifulSoup4 → статьи
           ↓
  дедупликация по source_url
  (уже есть → пропустить)
           ↓
  source.needs_translation?
  ДА → ai.translate(title, summary, 'vi'|'en' → 'ru')
  НЕТ → записать как есть
           ↓
  ai.enrich() ← рерайт заголовка + сжать summary
           ␣
  status=draft, ждёт модерации

/admin/news/newsitem/ ← ты открываешь
  [Опубликовать] → сайт + Telegram
  [Отклонить]  → status=rejected
```

**AI-возможности (`apps/news/ai.py`):**

> У тебя есть подписка GitHub Copilot — это даёт доступ к **GitHub Models API**.
> Те же модели (GPT-4o-mini, GPT-4o), тот же формат запросов —
> меняется только `base_url` и ключ.

```python
# apps/news/ai.py
# API-совместим с OpenAI — меняется только endpoint + ключ
import json, urllib.request
from django.conf import settings

# .env:
# AI_PROVIDER=github          # или 'openai'
# GITHUB_TOKEN=ghp_xxx        # Personal Access Token (права: models:read)
# OPENAI_API_KEY=sk-xxx       # если AI_PROVIDER=openai

AI_ENDPOINTS = {
    'github': 'https://models.inference.ai.azure.com/chat/completions',
    'openai': 'https://api.openai.com/v1/chat/completions',
}

def _get_token():
    if settings.AI_PROVIDER == 'github':
        return settings.GITHUB_TOKEN
    return settings.OPENAI_API_KEY


def call_ai(messages, model='gpt-4o-mini'):
    """Универсальный вызов: GitHub Models или OpenAI в зависимости от AI_PROVIDER"""
    url = AI_ENDPOINTS[settings.AI_PROVIDER]
    payload = json.dumps({
        'model': model,
        'messages': messages,
        'max_tokens': 1000,
        'response_format': {'type': 'json_object'},
    }).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {_get_token()}',
        },
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())['choices'][0]['message']['content']


def translate_and_enrich(title_original, summary_original, source_lang='vi'):
    """Перевод + рерайт + summary одним запросом (экономия токенов)"""
    prompt = f"""Новость на языке: {source_lang}
Заголовок: {title_original}
Анонс: {summary_original}

Сделай в одном ответе:
1. Переведи на русский, сохраняя смысл
2. Сделай заголовок цеплящим и ёмким
3. summary 2–3 предложения для русскоязычных (туристы + экспаты)

Ответ в JSON: {{"title": "...", "summary": "..."}}"""

    result = call_ai([{'role': 'user', 'content': prompt}])
    return json.loads(result)
```

**Лимиты GitHub Models** (бесплатно для Copilot-подписчиков):
| Модель | Запросов/день | Запросов/месяц |
|--------|--------------|---------------|
| gpt-4o-mini | 500 | 2000 |
| gpt-4o | 50 | 150 |

Для ручного `fetch_news` раз в день — море по колено.

**Как получить `GITHUB_TOKEN`:**
1. github.com → Settings → Developer settings → Personal access tokens
2. Сделать токен (Fine-grained) с правом `models:read`
3. Добавить в `.env`: `GITHUB_TOKEN=ghp_xxx`

**Параметры команды:**
```bash
python manage.py fetch_news                   # все источники
python manage.py fetch_news --source=12       # один источник
python manage.py fetch_news --no-ai           # без AI (экономия токенов)
```

**Telegram-публикация** (через `urllib.request`, без доп. библиотек):
```python
# apps/news/telegram.py
import json, urllib.request

def send_to_telegram(news_item, bot_token, channel_id):
    text = (
        f"• *{news_item.title}*\n\n"
        f"{news_item.summary[:300]}...\n\n"
        f"➡️ {news_item.get_absolute_url()}"
    )
    payload = json.dumps({
        'chat_id': channel_id,
        'text': text,
        'parse_mode': 'Markdown',
    }).encode()
    req = urllib.request.Request(
        f'https://api.telegram.org/bot{bot_token}/sendMessage',
        data=payload,
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())['result']['message_id']
```

---

### apps/vendors/models.py
    oc_id = models.IntegerField(null=True, blank=True)   # vendor_id из OpenCart
    slug = models.SlugField(unique=True, max_length=255) # из oc9a_seo_url

    display_name = models.CharField(max_length=500)
    description = models.TextField(blank=True)           # HTML из vendor_description
    meta_description = models.CharField(max_length=500, blank=True)
    meta_keywords = models.CharField(max_length=500, blank=True)

    telephone = models.CharField(max_length=30, blank=True)
    image = models.ImageField(upload_to='catalog/vendor/', blank=True)
    city = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    map_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)

    is_active = models.BooleanField(default=True)
    approved = models.BooleanField(default=True)

    def get_absolute_url(self):
        return f'/{self.slug}/'


class Product(models.Model):
    oc_id = models.IntegerField(null=True, blank=True)   # product_id из OpenCart
    slug = models.SlugField(unique=True, max_length=255) # из oc9a_seo_url
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE,
                               related_name='products', null=True)

    name = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='catalog/product/', blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    meta_description = models.CharField(max_length=500, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_absolute_url(self):
        return f'/{self.slug}/'
```

---

### apps/users/models.py

```python
# ВАЖНО: кастомный User заложить с самого начала!
# Менять потом — долго и болезненно
class User(AbstractUser):
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True)
    telegram_id = models.CharField(max_length=50, blank=True)

    # Геймификация (закладываем поля сейчас)
    points = models.IntegerField(default=0)

    # Тип пользователя
    TOURIST = 'tourist'
    EXPAT = 'expat'
    BUSINESS = 'business'
    USER_TYPES = [(TOURIST, 'Турист'), (EXPAT, 'Экспат'), (BUSINESS, 'Бизнес')]
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default=TOURIST)
```

---

### Авторизация и регистрация

**Фаза 1:** Сайт преимущественно для чтения. Регистрация есть, но не обязательна для доступа к контенту.

**Флоу регистрации:**
```
Форма регистрации → аккаунт создан → автовход → личный кабинет
```
*(Email-подтверждение — добавить после выбора SMTP-провайдера)*

**URL-адреса (Django contrib.auth + кастомные):**
```
/accounts/register/                    ← кастомная форма (имя, email, пароль)
/accounts/login/                       ← Django auth
/accounts/logout/
/accounts/password-reset/
/accounts/password-reset/done/
/accounts/password-reset/confirm/<uidb64>/<token>/
/profile/                              ← личный кабинет
```

**settings.py:**
```python
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
```

**Доступ к страницам:**
| Страница | Доступ |
|----------|--------|
| Статьи, вендоры, новости | Открыто |
| `/profile/` | `@login_required` |
| `/listings/create/` | `@login_required` (Фаза 2) |
| `/admin/...` | staff / superuser |

**TODO Фаза 3:** Вход через Telegram (webhook @NhaTrang_where_eat_bot).

---

### apps/listings/models.py (Фаза 2 — заложить структуру сейчас)

```python
class Listing(models.Model):
    RENT = 'rent'
    JOBS = 'jobs'
    SELL = 'sell'
    SERVICES = 'services'
    CATEGORIES = [(RENT, 'Аренда'), (JOBS, 'Работа'),
                  (SELL, 'Продажа'), (SERVICES, 'Услуги')]

    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORIES)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    author = models.ForeignKey('users.User', on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    is_premium = models.BooleanField(default=False)  # платное поднятие
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
```

---

## URL-архитектура

### Система редиректов (`django.contrib.redirects`)

`RedirectFallbackMiddleware` (последний в `MIDDLEWARE`) перехватывает 404
и ищет совпадение в таблице `django_redirect`. Пути хранятся **percent-encoded**
(не Unicode), т.к. `request.get_full_path()` возвращает percent-encoded URL.

```
django_redirect (71 записей):
  /%D0%B0%D1%80%D0%B5%D0%BD%D0%B4%D0%B0/  →  /vendors/      (кирилл. вендор)
  /%D0%BE%D0%B1%D0%BC%D0%B5%D0%BD-...../  →  /obmen-valyuty-2025/  (кирилл. статья)
  /obmen-valyuty-2025/                     →  200 OK (статья с Latin slug)
  /index.php?route=checkout/cart           →  /
  ... 35 OpenCart-категорий               →  /vendors/
```

**management commands:**
- `setup_redirects` — парсит `oc9a_seo_url` из SQL, создаёт редиректы для категорий и функциональных страниц
- `transliterate_slugs` — находит кириллические slug в Django DB, переводит в Latin, создаёт редирект со старого URL

### Проблема конфликтов URL
Все сущности (статьи, вендоры, продукты) используют плоские slug-URL без префикса:
`/elki-restaurant/` — вендор, `/manti/` — продукт, `/vizaran-vetnam/` — статья.
Решение: единый `slug_dispatch` view — ищем в порядке **Article → Vendor → Product → Page**.
Поскольку slug берётся точно из `oc9a_seo_url`, конфликтов нет (OpenCart сам обеспечивал уникальность).

```python
# config/urls.py
urlpatterns = [
    # Тип 1: /cat/slug/ — проверяем первым (однозначный URL)
    path('<slug:cat>/<slug:slug>/', ArticleDetailView.as_view()),

    # Тип 2: /slug/ — диспатчер по типу сущности
    path('<slug:slug>/', slug_dispatch),   # Article | Vendor | Product

    # Системные
    path('search/', SearchView.as_view(), name='search'),
    path('subscribe/', SubscribeView.as_view(), name='subscribe'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}),
    path('robots.txt', RobotsView.as_view()),

    # Фаза 2
    # path('places/', include('directory.urls')),
    # path('listings/', include('listings.urls')),
]


# apps/blog/views.py
def slug_dispatch(request, slug):
    """Диспатчер: Article | Vendor | Product | Page по slug"""
    article = Article.objects.filter(slug=slug, is_published=True).first()
    if article:
        return ArticleDetailView.as_view()(request, slug=slug)

    vendor = Vendor.objects.filter(slug=slug, is_active=True).first()
    if vendor:
        return VendorDetailView.as_view()(request, slug=slug)

    product = Product.objects.filter(slug=slug, is_active=True).first()
    if product:
        return ProductDetailView.as_view()(request, slug=slug)

    page = Page.objects.filter(slug=slug).first()
    if page:
        return PageDetailView.as_view()(request, slug=slug)

    raise Http404
```

---

## Поиск

### Фаза 1 — Django ORM `icontains` (без зависимостей)

```python
# config/urls.py
path('search/', SearchView.as_view(), name='search'),

# apps/blog/views.py
from django.db.models import Q

class SearchView(ListView):
    template_name = 'search/results.html'
    context_object_name = 'articles'
    paginate_by = 20

    def get_queryset(self):
        q = self.request.GET.get('q', '').strip()
        if not q or len(q) < 3:
            return Article.objects.none()
        return Article.objects.filter(
            Q(title__icontains=q) |
            Q(short_description__icontains=q) |
            Q(meta_keywords__icontains=q),
            is_published=True
        ).order_by('-published_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = self.request.GET.get('q', '').strip()
        ctx['query'] = q
        if q and len(q) >= 3:
            ctx['vendors'] = Vendor.objects.filter(
                Q(display_name__icontains=q) | Q(description__icontains=q),
                is_active=True
            )[:5]
        return ctx
```

URL: `GET /search/?q=ресторан`

### Фаза 2 — SQLite FTS5 (полнотекстовый, встроен в Python)

```python
# apps/blog/search.py
from django.db import connection

def fts_search(query, limit=20):
    """SQLite FTS5 — в 10-20x быстрее icontains на большом объёме"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT article_id,
                   snippet(articles_fts, 0, '<mark>', '</mark>', '...', 32)
            FROM articles_fts
            WHERE articles_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, [query, limit])
        return cursor.fetchall()
```

*(FTS5-индекс создаётся отдельной миграцией при переходе к Фазе 2)*

---

## 404 и 500 страницы

Django автоматически использует `templates/404.html` и `templates/500.html` при `DEBUG=False`.

### templates/404.html

```html
{% extends "base.html" %}
{% block title %}Страница не найдена — КликМи{% endblock %}
{% block content %}
<div class="min-h-[60vh] flex flex-col items-center justify-center text-center px-4">
  <p class="text-8xl font-bold text-(--color-accent) mb-4">404</p>
  <h1 class="font-serif text-2xl mb-4">Страница не найдена</h1>
  <p class="text-gray-500 mb-8">
    Возможно, страница была удалена или вы ошиблись в адресе.
  </p>
  <a href="/" class="ck-btn-accent">← На главную</a>
  <div class="mt-10 max-w-md w-full">
    {% include "components/search_bar.html" %}
  </div>
</div>
{% endblock %}
```

### templates/500.html

```html
{% extends "base.html" %}
{% block title %}Ошибка сервера — КликМи{% endblock %}
{% block content %}
<div class="min-h-[60vh] flex flex-col items-center justify-center text-center px-4">
  <p class="text-8xl font-bold text-gray-300 mb-4">500</p>
  <h1 class="font-serif text-2xl mb-4">Что-то пошло не так</h1>
  <p class="text-gray-500 mb-8">
    Мы уже знаем о проблеме и работаем над её устранением.
  </p>
  <a href="/" class="ck-btn-accent">← На главную</a>
</div>
{% endblock %}
```

> **Важно:** `500.html` не должен обращаться к БД — сервер уже в нерабочем состоянии.
> Только статичный HTML + Tailwind CSS-классы.

---

## Parity Check — проверка идентичности URL с оригиналом

Стратегия: до миграции сохраняем baseline с оригинала, после — сравниваем Django-ответы.

```
apps/
└── blog/management/commands/
    ├── import_from_opencart.py   ← импорт всех данных
    ├── crawl_original.py         ← ШАГ 1: обход clikme.ru, сохранить baseline.json
    └── check_parity.py           ← ШАГ 2: сравнить ответы Django с baseline
```

### crawl_original.py — запускается один раз до миграции
```
python manage.py crawl_original --domain=clikme.ru --out=baseline.json
```
Проходит по sitemap.xml, для каждого URL сохраняет:
- HTTP status
- `<title>`
- `<h1>`
- `<meta name="description">`
- canonical URL

### check_parity.py — запускать после каждой фазы
```
python manage.py check_parity --baseline=baseline.json --target=http://localhost:8000
```
Вывод: HTML-отчёт со всеми расхождениями:
```
[OK]   /vizaran-prodlenie-prebyvaniya-vo-vetname
[OK]   /elki-restaurant-russian-cuisine
[FAIL] /manti  ← 404
[WARN] /pasta-bar-nyachang  ← title mismatch
---
Total: 342 URLs | OK: 339 | FAIL: 1 | WARN: 2
```

---

## Дизайн-система

### Концепция
Мобайльный минималистичный информационный сайт. Референсы:
- **Structura** (`framework-y.com/structura`) — тёмные фоны-секции, крупная типографика, геометричность
- **GO Travel** (`go/html/landing/travel.html`) — tile-карточки, сетки контента, компонентная структура

Реализация — **Tailwind CSS v4 (CLI)** — utility-first, полный контроль над дизайном, без Bootstrap-look.
Tailwind CLI собирает CSS при разработке, на сервере лежит один статический файл.

---

### 📱 Mobile-First — Главный приоритет

> **82% трафика с мобильных** (8 879 кликов vs 1 960 с ПК, Google Search Console март 2026)

Принцип: **сначала делаем мобайльную версию** — Tailwind это поддерживает по умолчанию.
Без префикса = мобайл → `sm:` = таблет → `lg:` = десктоп.

**Правила Mobile-First для этого проекта:**

| Элемент | Мобайл (<640px) | Десктоп (lg:) |
|---------|--------------|-------------|
| Навбар | Гамбургер-меню | Горизонтальные ссылки |
| Карточки статей | 1 колонка | 3 колонки |
| Статья | Шрифт 18px, паддинги 16px | Шрифт 17px, паддинги больше |
| Боковая панель | Нет (прячется вниз) | Есть |
| Таблицы в статье | `overflow-x-auto` + скролл | Обычно |
| Hero-заголовок | 2.2rem | 3.5rem |
| Кнопки/ссылки | min-height 44px (пальцем) | 36px |

**Обязательные вещи:**
```html
<!-- Обязательно в base.html -->
<meta name="viewport" content="width=device-width, initial-scale=1">

<!-- Изображения через srcset (мобайл не грузит desktop-размер) -->
<img src="cover.jpg"
     srcset="cover-400.jpg 400w, cover-800.jpg 800w, cover.jpg 1200w"
     sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
     loading="lazy" alt="...">

<!-- Формы: input type="text" → font-size не меньше 16px (иначе iOS зумирует) -->
<input class="text-base ..." type="text">
```

**Core Web Vitals — обязательные метрики (Google ранжирует по ним):**
| Метрика | Цель | Что делаем |
|---------|------|----------|
| LCP (Largest Contentful Paint) | < 2.5s | `loading="eager"` для обложки, WebP |
| CLS (Cumulative Layout Shift) | < 0.1 | `width`/`height` у всех `<img>` |
| INP (Interaction to Next Paint) | < 200ms | минимум JS |
| TTFB | < 800ms | whitenoise + django cache |

---

### Шрифты (Google Fonts)
```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap" rel="stylesheet">
```
| Роль | Шрифт | Применение |
|------|-------|------------|
| Основной текст | **Inter** 400/500 | Статьи, описания, UI |
| Заголовки H1–H2 | **Playfair Display** 600/700 | Названия статей, секций |
| UI-элементы | **Inter** 600 | Кнопки, навбар, метки |

Inter + Playfair Display — проверенная пара для кириллицы: читаемо, современно, с характером.

### Цветовая палитра
```css
:root {
  /* Основные */
  --color-bg:        #ffffff;
  --color-bg-dark:   #111214;   /* тёмные hero-секции как в Structura */
  --color-bg-soft:   #f7f7f5;   /* светло-серый фон карточек */
  --color-text:      #1a1a1a;
  --color-text-muted:#6b7280;

  /* Акцент — тёплый терракота (Вьетнам: море, солнце, специи) */
  --color-accent:    #e85d26;
  --color-accent-hover: #c94d1a;

  /* Границы */
  --color-border:    #e5e5e5;
}
```

### Структура страниц

**Главная:**
```
[Hero — тёмный фон, большой заголовок, фото Нячанга]
[Последние статьи — tile-карточки, 3 колонки]
[Новости — горизонтальная лента]
[Каталог бизнесов — топ-вендоры, карточки]
[CTA — подписка на рассылку]
```

**Статья:**
```
[Хлебные крошки]
[H1 — Playfair Display крупно]
[Мета: дата + категория]
[Фото-обложка]
[Контент — Inter, line-height 1.8]
[Партнёрский виджет Trip.com]
[Похожие статьи — 3 карточки]
[Форма подписки]
```

**Страница вендора:**
```
[Фото-обложка + название]
[Описание + контакты + карта]
[Товары/услуги — карточки-tile]
```

### Tailwind CSS — конфигурация

Tailwind CLI — без Node.js/npm в продакшне. Только локально при разработке:
```bash
# Установка CLI (один раз)
curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-macos-arm64
chmod +x tailwindcss-macos-arm64 && mv tailwindcss-macos-arm64 tailwindcss

# Сборка при разработке (watch)
./tailwindcss -i static/css/input.css -o static/css/style.css --watch

# Финальная сборка (minified)
./tailwindcss -i static/css/input.css -o static/css/style.css --minify
```

`static/css/input.css` — только директивы + кастомные компоненты:
```css
@import "tailwindcss";

@theme {
  /* Шрифты */
  --font-sans: 'Inter', sans-serif;
  --font-serif: 'Playfair Display', serif;

  /* Цветовая палитра */
  --color-bg-dark:  #111214;
  --color-bg-soft:  #f7f7f5;
  --color-accent:   #e85d26;
  --color-accent-hover: #c94d1a;
  --color-muted:    #6b7280;
}

/* Кастомные компоненты с префиксом .ck- */
@layer components {
  .ck-hero        { @apply bg-(--color-bg-dark) text-white py-24 px-6; }
  .ck-article-card{ @apply bg-white rounded-xl shadow-sm hover:shadow-md transition-shadow; }
  .ck-vendor-card { @apply bg-(--color-bg-soft) rounded-xl p-6; }
  .ck-news-item   { @apply border-b border-gray-100 py-3 flex gap-4 items-start; }
  .ck-section-dark{ @apply bg-(--color-bg-dark) text-white py-16; }
  .ck-btn-accent  { @apply bg-(--color-accent) hover:bg-(--color-accent-hover) text-white px-6 py-3 rounded-lg font-semibold transition-colors; }
}
```

**Файл `tailwindcss` в `.gitignore`** — каждый разработчик скачивает сам.
**`static/css/style.css`** (собранный) — в git, чтобы сервер не требовал сборки.

### Компоненты (Tailwind utility-classes)
Каждый Django-компонент (`templates/components/`) использует Tailwind-классы напрямую.

---

## apps/newsletter/models.py

Подписка не требует регистрации. Пользователь вводит только email.

```python
class Subscriber(models.Model):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    # GDPR: явное согласие на рассылку
    consent_given_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return self.email
```

**Уникальный token для отписки** — генерируется через `secrets.token_urlsafe()` и хранится взвешенным в hashed-виде или отдельным полем.

```
GET /unsubscribe/<token>/  ← один клик → is_active=False
```

**Email-провайдер:** на старте **Mailjet** (бесплатно до 200 писем/день), смена провайдера — только через `.env`.

```python
# settings.py
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'in-v3.mailjet.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ['MAILJET_API_KEY']
EMAIL_HOST_PASSWORD = os.environ['MAILJET_SECRET_KEY']
DEFAULT_FROM_EMAIL = 'КликМи <noreply@clikme.ru>'
```

---

## GDPR — Cookie Consent

> EU-сервер + европейская аудитория = обязательный cookie banner.

**Что требует GDPR для этого сайта:**
- Cookie consent перед загрузкой Google Analytics / Yandex.Metrika
- Ссылка на Политику конфиденциальности (clikme.ru/privacy/) — уже есть в OpenCart
- Явное согласие при подписке `consent_given_at = now()`
- Google Fonts — загружать через `<link>` или скачать локально (не отправлять IP в Google)

**Реализация (minimal vanilla JS, без платных сервисов):**

```html
<!-- templates/components/cookie_banner.html -->
{% if not request.COOKIES.ck_consent %}
<div id="cookie-banner"
     class="fixed bottom-0 left-0 right-0 bg-(--color-bg-dark) text-white p-4 z-50
            flex flex-col sm:flex-row items-center gap-4">
  <p class="text-sm flex-1">
    Мы используем cookie для аналитики.
    <a href="/privacy/" class="underline">Политика конфиденциальности</a>
  </p>
  <button id="cookie-accept" class="ck-btn-accent whitespace-nowrap">Принять</button>
  <button id="cookie-decline" class="text-gray-400 text-sm underline">Отказаться</button>
</div>
<script>
  document.getElementById('cookie-accept').onclick = function() {
    document.cookie = 'ck_consent=1;max-age=31536000;path=/;SameSite=Lax';
    document.getElementById('cookie-banner').remove();
    // Google Analytics / Metrika — инициализировать здесь
  };
  document.getElementById('cookie-decline').onclick = function() {
    document.getElementById('cookie-banner').remove();
  };
</script>
{% endif %}
```

Подключить в `base.html` перед `</body>`:
```html
{% include "components/cookie_banner.html" %}
```

Google Analytics и Yandex.Metrika — обернуть в `{% if request.COOKIES.ck_consent %}...{% endif %}`.

---

## SEO-чеклист на каждой странице

```html
<!-- base.html — обязательный минимум -->
<title>{{ page_title }}</title>
<meta name="description" content="{{ meta_description }}">
<link rel="canonical" href="{{ canonical_url }}">

<!-- Open Graph (для соцсетей и Telegram) -->
<meta property="og:title" content="{{ og_title }}">
<meta property="og:description" content="{{ og_description }}">
<meta property="og:image" content="{{ og_image }}">
<meta property="og:type" content="article">

<!-- JSON-LD для статьи -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{{ article.title }}",
  "datePublished": "{{ article.published_at|date:'c' }}",
  "dateModified": "{{ article.updated_at|date:'c' }}"
}
</script>
```

---

## Конверсия изображений в WebP

Conversation выполняется при импорте из OpenCart и может запускаться вручную.

### В скрипте импорта

```python
# apps/blog/management/commands/import_from_opencart.py
from PIL import Image
import io, os
from django.core.files.base import ContentFile

def to_webp(image_path, quality=85):
    """Открыть изображение и вернуть ContentFile в формате WebP"""
    try:
        img = Image.open(image_path).convert('RGB')
        buf = io.BytesIO()
        img.save(buf, 'WEBP', quality=quality, method=6)
        buf.seek(0)
        name = os.path.splitext(os.path.basename(image_path))[0] + '.webp'
        return ContentFile(buf.read(), name=name)
    except Exception:
        return None  # оставить оригинал если Pillow не смог
```

### Команда для конверсии уже загруженных изображений

```bash
python manage.py convert_to_webp           # все изображения
python manage.py convert_to_webp --app=blog    # только статьи
```

### Правила

| Тип изображения | WebP quality | Макс. ширина |
|-----------------|-------------|-------------|
| Обложка статьи (hero) | 85% | 1200px |
| Карточка (thumbnail) | 80% | 600px |
| Логотип / фото вендора | 85% | 400px |
| Аватар пользователя | 80% | 200px |

---

## Зависимости (requirements.txt)

### Принцип: только то, для чего нет решения из коробки Django

```
# Основа
django>=5.0          # фреймворк
Pillow               # ImageField (обязательно)
gunicorn             # WSGI-сервер
whitenoise           # статика без nginx-настроек

# Новости (news app)
feedparser           # парсинг RSS/Atom лент (pure Python, без зависимостей)
beautifulsoup4       # парсинг HTML-страниц источников
lxml                 # быстрый парсер для BeautifulSoup4
httpx                # HTTP-клиент (нужен для HTML-сайтов с защитой от urllib)

# Платежи (Фаза 2)
mollie-api-python    # Mollie API (западные платежи — объявления, премиум-профили)

# AI: используем GitHub Models API (входит в GitHub Copilot подписку)
# Формат запросов = OpenAI API — никаких доп. пакетов не нужен
# AI_PROVIDER=github и GITHUB_TOKEN — в .env
# Альтернатива: AI_PROVIDER=openai и OPENAI_API_KEY — тот же код
```

### БД — SQLite (встроена в Python)
Для сайта с 70-500 статьями и умеренным трафиком SQLite полностью достаточна.
При необходимости миграция на PostgreSQL — один параметр в settings.py.

### Что НЕ используем и почему
| Убрано | Почему |
|--------|--------|
| PostgreSQL | SQLite достаточно, меньше инфраструктуры |
| Redis | Нет очередей на старте, Django cache backend встроен |
| Celery | Запуск вручную через management command |
| `openai` пакет | urllib.request достаточно для ChatGPT API |
| `requests` | httpx заменяет полностью, + async на будущее |
| django-environ | os.environ достаточно |
| django-modeltranslation | Добавим когда реально понадобится |
| django-storages | Медиафайлы хранятся локально на сервере |
| sentry-sdk | Django logging достаточно на старте |
| `nginx` | Заменён Caddy (авто SSL, конфиг в 10 строк) |
