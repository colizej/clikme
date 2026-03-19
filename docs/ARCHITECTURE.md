# Архитектура Django-проекта — clikme.ru

## Структура проекта

```
django_project/
│
├── config/                     ← Настройки проекта
│   ├── settings.py             ← Все настройки в одном файле
│   ├── urls.py
│   └── wsgi.py
│
├── apps/
│   ├── blog/                   ← Фаза 1: Инфостатьи (~86 статей)
│   ├── vendors/                ← Фаза 1: Бизнес-каталог (~42 вендора, ~280 продуктов)
│   ├── news/                   ← Фаза 1: Новостная лента + Telegram
│   ├── pages/                  ← Фаза 1: Статичные страницы
│   ├── users/                  ← Фаза 1: Пользователи (AbstractUser)
│   ├── newsletter/             ← Фаза 1: Email-подписка
│   ├── directory/              ← Фаза 2: Каталог мест
│   ├── listings/               ← Фаза 2: Доска объявлений
│   ├── reviews/                ← Фаза 2: Отзывы
│   └── gamification/           ← Фаза 3: Баллы и бейджи
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
│   ├── components/             ← Переиспользуемые компоненты ({% include %})
│   │   ├── article_card.html   ← карточка статьи
│   │   ├── seo_meta.html       ← <title>, <meta>, canonical, OG-теги
│   │   ├── breadcrumbs.html    ← хлебные крошки
│   │   ├── pagination.html     ← пагинация
│   │   ├── subscribe_form.html ← форма email-подписки
│   │   ├── affiliate_block.html← партнёрский виджет
│   │   └── share_buttons.html  ← кнопки поделиться
│   └── ...
│
├── static/
│   ├── css/
│   ├── js/
│   └── img/
│
├── media/                      ← Загруженные файлы (не в git)
│   └── catalog/                ← Скопировано из OpenCart image/catalog/
│
├── requirements.txt            ← Один файл зависимостей
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
    """Источник новостей: RSS-лента или сайт для парсинга"""
    name = models.CharField(max_length=255)
    url = models.URLField(unique=True)
    RSS = 'rss'
    HTML = 'html'
    SOURCE_TYPES = [(RSS, 'RSS-лента'), (HTML, 'HTML-страница')]
    source_type = models.CharField(max_length=10, choices=SOURCE_TYPES, default=RSS)
    is_active = models.BooleanField(default=True)
    last_fetched_at = models.DateTimeField(null=True, blank=True)


class NewsItem(models.Model):
    source = models.ForeignKey(NewsSource, on_delete=models.SET_NULL,
                               null=True, related_name='items')
    source_url = models.URLField(unique=True)           # дедупликация по этому полю
    slug = models.SlugField(unique=True, max_length=255, blank=True)

    title = models.CharField(max_length=500)
    summary = models.TextField(blank=True)              # анонс/описание
    image_url = models.URLField(blank=True)             # урл картинки с источника
    image = models.ImageField(upload_to='news/', blank=True)  # скачанная локально

    DRAFT = 'draft'
    PUBLISHED = 'published'
    REJECTED = 'rejected'
    STATUSES = [(DRAFT, 'Черновик'), (PUBLISHED, 'Опубликовано'), (REJECTED, 'Отклонено')]
    status = models.CharField(max_length=15, choices=STATUSES, default=DRAFT)

    telegram_message_id = models.CharField(max_length=50, blank=True)  # ID сообщения после пуша

    fetched_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-fetched_at']
```

**Рабочий процесс:**
```
1. python manage.py fetch_news          ← сбор из всех источников → сохраняет в status=draft
2. Открываешь /admin/news/newsitem/ ← видишь черновики
3. В админе: кнопка "Опубликовать" → сайт + Telegram одновременно
4. "Отклонить" → новость со status=rejected, сайт не попадает
```

**Telegram-публикация:** через `urllib.request` (без доп. библиотек):
```python
# apps/news/telegram.py
import json
import urllib.request

def send_to_telegram(news_item, bot_token, channel_id):
    """Отправка новости в Telegram-канал"""
    text = f"""• *{news_item.title}*

{news_item.summary[:300]}...

Читать полностью: {news_item.get_absolute_url()}
Источник: {news_item.source_url}"""

    payload = json.dumps({
        'chat_id': channel_id,
        'text': text,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': False,
    }).encode()

    req = urllib.request.Request(
        f'https://api.telegram.org/bot{bot_token}/sendMessage',
        data=payload,
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read())
        return data['result']['message_id']
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

### Проблема конфликтов URL
Все сущности (статьи, вендоры, продукты) используют плоские slug-URL без префикса:
`/elki-restaurant/` — вендор, `/manti/` — продукт, `/vizaran-vetnam/` — статья.
Решение: единый `slug_dispatch` view — ищем в порядке **Article → Vendor → Product**.
Поскольку slug берётся точно из `oc9a_seo_url`, конфликтов нет (OpenCart сам обеспечивал уникальность).

```python
# config/urls.py
urlpatterns = [
    # Тип 1: /cat/slug/ — проверяем первым (однозначный URL)
    path('<slug:cat>/<slug:slug>/', ArticleDetailView.as_view()),

    # Тип 2: /slug/ — диспатчер по типу сущности
    path('<slug:slug>/', slug_dispatch),   # Article | Vendor | Product

    # Системные
    path('subscribe/', SubscribeView.as_view()),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}),
    path('robots.txt', RobotsView.as_view()),

    # Фаза 2
    path('places/', include('directory.urls')),
    path('listings/', include('listings.urls')),
]


# apps/blog/views.py
def slug_dispatch(request, slug):
    """Диспатчер: Article | Vendor | Product по slug"""
    article = Article.objects.filter(slug=slug, is_published=True).first()
    if article:
        return ArticleDetailView.as_view()(request, slug=slug)

    vendor = Vendor.objects.filter(slug=slug, is_active=True).first()
    if vendor:
        return VendorDetailView.as_view()(request, slug=slug)

    product = Product.objects.filter(slug=slug, is_active=True).first()
    if product:
        return ProductDetailView.as_view()(request, slug=slug)

    raise Http404
```

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

## Зависимости (requirements.txt)

### Принцип: только то, для чего нет решения из коробки Django

```
django>=5.0       # фреймворк
Pillow            # обработка изображений (django ImageField требует)
gunicorn          # WSGI-сервер для продакшна
whitenoise        # отдача статики без nginx-настроек
```

### БД — SQLite (встроена в Python)
Для сайта с 70-500 статьями и умеренным трафиком SQLite полностью достаточна.
При необходимости миграция на PostgreSQL — один параметр в settings.py.

### Что НЕ используем и почему
| Убрано | Почему |
|--------|--------|
| PostgreSQL | SQLite достаточно, меньше инфраструктуры |
| Redis | Нет очередей на старте, Django cache backend встроен |
| Celery | Email через Django smtp backend, задачи — позже |
| django-environ | os.environ достаточно для простых настроек |
| django-modeltranslation | Добавим когда реально понадобится |
| django-storages | Медиафайлы хранятся локально на сервере |
| sentry-sdk | Django logging достаточно на старте |
