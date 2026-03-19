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
│   ├── blog/                   ← Фаза 1: Статьи блога
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

```python
# config/urls.py
urlpatterns = [
    # Блог — два типа URL из OpenCart
    path('<slug:slug>/', ArticleDetailView.as_view()),           # /vizaran-prodlenie.../
    path('<slug:cat>/<slug:slug>/', ArticleDetailView.as_view()), # /blog-soveti-history/...

    # Категории
    path('category/<slug:slug>/', CategoryView.as_view()),

    # Подписка
    path('subscribe/', SubscribeView.as_view()),

    # Фаза 2
    path('places/', include('directory.urls')),
    path('listings/', include('listings.urls')),
]
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
