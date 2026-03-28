# Рекламная система — ads.app

> Дата: март 2026
> Статус: **В разработке**

---

## Цель

Система управления рекламными вставками на сайте ClikMe:
- Партнёрские баннеры, виджеты, текстовые ссылки
- Ротация объявлений по приоритету и таргетингу
- Отслеживание кликов и показов
- Интеграция с email-рассылкой

---

## Структура приложения

```
apps/
└── ads/
    ├── models.py         # Модели данных
    ├── admin.py          # Админка
    ├── views.py          # Обработка кликов
    ├── urls.py           # URL-маршруты
    ├── templatetags/
    │   └── ads_tags.py   # Теги для шаблонов
    ├── services.py       # Бизнес-логика
    └── migrations/
```

---

## Модели

### Partner (Партнёры)

| Поле | Тип | Описание |
|------|-----|---------|
| `id` | AutoField | PK |
| `name` | CharField | "Trip.com", "Aviasales" |
| `slug` | SlugField | `trip-com`, `aviasales` |
| `url` | URLField | Основной URL партнёра |
| `logo` | ImageField | Логотип (опционально) |
| `is_active` | BooleanField | Активен |
| `created_at` | DateTimeField | |
| `updated_at` | DateTimeField | |

### AdUnit (Рекламные单元)

| Поле | Тип | Описание |
|------|-----|---------|
| `id` | AutoField | PK |
| `partner` | FK → Partner | Обязательно |
| `name` | CharField | "Trip.com Widget - Hotels" |
| `ad_type` | CharField | `widget`, `banner`, `text` |

#### Для widget:
| Поле | Тип | Описание |
|------|-----|---------|
| `widget_code` | TextField | Полный iframe или script код |
| `widget_width` | IntegerField | Ширина виджета (320) |
| `widget_height` | IntegerField | Высота виджета (480) |

#### Для banner:
| Поле | Тип | Описание |
|------|-----|---------|
| `image` | ImageField | Изображение баннера |
| `link` | URLField | Ссылка на партнёра |

#### Для text:
| Поле | Тип | Описание |
|------|-----|---------|
| `text` | CharField | Анкор текст ссылки |
| `link` | URLField | Ссылка на партнёра |

#### Общие поля:
| Поле | Тип | Описание |
|------|-----|---------|
| `intro_text` | CharField | Подводка: "Лучшие отели Нячанга:" |
| `is_permanent` | BooleanField | Постоянный или временный |
| `start_date` | DateTimeField | Начало показа (null = сразу) |
| `end_date` | DateTimeField | Конец показа (null = бессрочно) |
| `priority` | IntegerField | 1-10, выше = чаще показывается |
| `target_categories` | M2M → Category | Какие категории показывать |
| `max_impressions` | IntegerField | Лимит показов (null = без лимита) |
| `impressions_count` | IntegerField | Сколько раз показан |
| `is_active` | BooleanField | Активен |
| `created_at` | DateTimeField | |
| `updated_at` | DateTimeField | |

### AdSlot (Слоты размещения)

| Поле | Тип | Описание |
|------|-----|---------|
| `id` | AutoField | PK |
| `slug` | SlugField | `article_middle`, `before_faq` |
| `name` | CharField | Человеческое название |
| `slot_type` | CharField | `widget_320x480`, `banner_728x90`, `text` |
| `fallback_text` | TextField | Текст если нет активных объявлений |
| `is_active` | BooleanField | |

**Предопределённые слоты:**
- `article_middle` — Середина статьи (widget 320x480)
- `before_faq` — Перед блоком FAQ (widget 320x480)
- `article_end` — Конец статьи (text или banner)
- `sidebar` — Боковая панель (banner 300x250)
- `newsletter` — В рассылке (inline)

### ArticleAdPlacement (Ручные размещения)

| Поле | Тип | Описание |
|------|-----|---------|
| `id` | AutoField | PK |
| `article` | FK → Article | Статья |
| `slot` | FK → AdSlot | Слот |
| `ad_unit` | FK → AdUnit, null | Конкретное объявление (null = авто) |
| `is_manual` | BooleanField | True = шорткод, False = авто |
| `is_active` | BooleanField | |

### AdClick (Клики)

| Поле | Тип | Описание |
|------|-----|---------|
| `id` | AutoField | PK |
| `ad_unit` | FK → AdUnit | Какое объявление |
| `article` | FK → Article, null | Откуда клик |
| `ip_address` | GenericIPAddressField | IP пользователя |
| `user_agent` | TextField | Браузер |
| `referer` | URLField | Откуда пришёл (null) |
| `created_at` | DateTimeField | |

---

## Логика работы

### 1. Выбор объявления для слота

```python
def get_ad_for_slot(slot: AdSlot, article: Article) -> AdUnit | None:
    """
    Алгоритм выбора объявления:
    1. Проверить ручные размещения для статьи
    2. Найти подходящие активные объявления
    3. Фильтр по датам (если временные)
    4. Фильтр по категориям (если есть таргетинг)
    5. Фильтр по лимитам показов
    6. Выбрать по приоритету + случайность
    """
    
    # 1. Ручные размещения
    manual = ArticleAdPlacement.objects.filter(
        article=article,
        slot=slot,
        is_manual=True,
        is_active=True
    ).select_related('ad_unit').first()
    
    if manual and manual.ad_unit and manual.ad_unit.is_active:
        return manual.ad_unit
    
    # 2. Поиск активных объявлений
    now = timezone.now()
    queryset = AdUnit.objects.filter(is_active=True)
    
    # 3. Фильтр по датам
    queryset = queryset.filter(
        Q(is_permanent=True) |
        Q(start_date__lte=now, end_date__gte=now)
    )
    
    # 4. Фильтр по слоту
    queryset = queryset.filter(slot_type=slot.slot_type)
    
    # 5. Фильтр по категориям
    if article.category:
        queryset = queryset.filter(
            Q(target_categories__isnull=True) |
            Q(target_categories=article.category)
        )
    
    # 6. Фильтр по лимитам
    queryset = queryset.filter(
        Q(max_impressions__isnull=True) |
        Q(impressions_count__lt=F('max_impressions'))
    )
    
    # 7. Ротация: берём топ-3 по приоритету, случайный из них
    top_units = list(queryset.order_by('-priority')[:3])
    
    if top_units:
        chosen = random.choice(top_units)
        # Увеличиваем счётчик показов
        AdUnit.objects.filter(pk=chosen.pk).update(
            impressions_count=F('impressions_count') + 1
        )
        return chosen
    
    return None
```

### 2. Рендер объявления в шаблоне

```django
{% load ads_tags %}

{% get_ad 'article_middle' article as ad %}
{% if ad %}
<div class="ad-slot ad-slot--{{ ad.ad_type }}">
    {% if ad.intro_text %}
    <p class="ad-intro">{{ ad.intro_text }}</p>
    {% endif %}
    
    {% if ad.ad_type == 'widget' %}
    <div class="ad-widget">{{ ad.widget_code|safe }}</div>
    {% elif ad.ad_type == 'banner' %}
    <a href="{% url 'ads:click' ad.id %}?next={{ ad.link|urlencode }}">
        <img src="{{ ad.image.url }}" alt="{{ ad.partner.name }}">
    </a>
    {% elif ad.ad_type == 'text' %}
    <a href="{% url 'ads:click' ad.id %}?next={{ ad.link|urlencode }}" class="ad-text-link">
        {{ ad.text }}
    </a>
    {% endif %}
</div>
{% endif %}
```

### 3. Обработка клика

```
URL: /ads/click/{ad_unit_id}/?next={encoded_url}&article={article_slug}

View: ads_click(request, ad_id)
    → Найти AdUnit
    → Создать AdClick запись
    → 302 редирект на ?next URL
```

```python
@require_GET
def ads_click(request, ad_id):
    try:
        ad_unit = get_object_or_404(AdUnit, pk=ad_id)
        
        # Логируем клик
        AdClick.objects.create(
            ad_unit=ad_unit,
            article_id=request.GET.get('article'),
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            referer=request.META.get('HTTP_REFERER', ''),
        )
        
        # Редирект
        next_url = request.GET.get('next', ad_unit.link)
        return redirect(next_url)
        
    except Exception:
        return redirect('/')
```

---

## Шорткоды в статьях

### Формат

```
[banner:slot_slug]
[banner:slot_slug|unit=ad_unit_id]
```

### Обработка

```python
from django.template import engines

def render_ad_shortcodes(content: str, article: Article) -> str:
    """Заменяет [banner:slot] на HTML объявления"""
    
    def replace_shortcode(match):
        params = match.group(1)
        parts = params.split('|')
        slot_slug = parts[0].strip()
        
        unit_id = None
        for part in parts[1:]:
            if part.startswith('unit='):
                unit_id = part.split('=')[1]
        
        ad = get_ad_for_slot_by_slug(slot_slug, article, unit_id)
        
        if ad:
            return render_ad_to_html(ad)
        return ''
    
    pattern = r'\[banner:([^\]]+)\]'
    return re.sub(pattern, replace_shortcode, content)
```

---

## Админка

### Partner Admin
```
Список:
├── Trip.com ✓
├── Aviasales ✓
└── Booking.com ✓

Детали:
├── name: Trip.com
├── slug: trip-com
├── url: https://www.trip.com
├── logo: [upload]
```

### AdUnit Admin
```
Список:
├── Trip.com Widget - Hotels ✓
├── Trip.com Widget - Tours ✓
├── Aviasales Banner 728x90 ✓
└── Booking Text Link ✓

Детали:
├── Partner: Trip.com
├── Name: Trip.com Widget - Hotels
├── Type: Widget
├── Widget Code: <iframe...>
├── Widget Size: 320 x 480
├── Intro Text: Лучшие отели Нячанга:
├── Slot Type: widget_320x480
├── Permanent: ✓
├── Priority: 8
├── Categories: [Отели, Пляжи]
├── Max Impressions: 10000
├── Impressions: 3421
├── Active: ✓
```

### Dashboard (Statistic)

```
┌─────────────────────────────────────┐
│  Ad Statistics                      │
├─────────────────────────────────────┤
│  Today      │  Week    │  Month    │
│  142 clicks │  892     │  3,421    │
├─────────────────────────────────────┤
│  Top Ads:                          │
│  1. Trip.com Widget - Hotels  2345 │
│  2. Aviasales Banner 728x90   876  │
│  3. Booking Text Link         200   │
└─────────────────────────────────────┘
```

---

## URL-маршруты

```python
# apps/ads/urls.py
urlpatterns = [
    path('ads/click/<int:ad_id>/', views.ads_click, name='click'),
]
```

---

## Типы партнёров

| Категория | Примеры |
|-----------|---------|
| **Travel** | Trip.com, Booking.com, Aviasales, GetYourGuide, Viator |
| **Банки/Финтех** | Карты, кредиты, криптобиржи (партнёрские программы) |
| **Маркетплейсы** | Amazon, AliExpress, Ozon |
| **Страхование** | travel insurance |
| **Другое** | VPN, хостинг, и т.д. |

### Предопределённые партнёры (примеры)

| Партнёр | Type | Widget/Banner |
|---------|------|---------------|
| Trip.com | Widget | Hotels, Tours, Flights |
| Aviasales | Widget/Banner | Поиск авиабилетов |
| Booking.com | Widget/Banner | Поиск отелей |
| GetYourGuide | Widget | Экскурсии |
| Viator | Widget | Экскурсии |

---

## Интеграция с рассылкой

### Дополнительные поля в AdUnit

| Поле | Описание |
|------|---------|
| `email_widget_code` | Код для email (адаптированный) |
| `email_image` | Изображение для email |
| `email_intro_text` | Текст для email |

### Логика для рассылки

```python
def get_ad_for_newsletter(slot: AdSlot, subscriber_profile=None) -> AdUnit:
    """Выбор объявления для email-рассылки"""
    
    queryset = AdUnit.objects.filter(is_active=True, slot_type=slot.slot_type)
    
    # Для email приоритетнее постоянные
    queryset = queryset.filter(is_permanent=True)
    
    # Ротация
    units = list(queryset.order_by('-priority')[:3])
    return random.choice(units) if units else None
```

### Шаблон email

```django
{% get_ad_for_newsletter 'newsletter' as ad %}
{% if ad %}
<tr>
    <td style="padding: 20px;">
        {% if ad.email_intro_text %}
        <p style="margin: 0 0 10px;">{{ ad.email_intro_text }}</p>
        {% endif %}
        
        {% if ad.ad_type == 'widget' and ad.email_widget_code %}
        {{ ad.email_widget_code|safe }}
        {% elif ad.ad_type == 'banner' and ad.email_image %}
        <img src="{{ ad.email_image.url }}" alt="{{ ad.partner.name }}">
        {% endif %}
    </td>
</tr>
{% endif %}
```

---

## TODO / Roadmap

### Фаза 1 — Базовая реализация
- [ ] Создать приложение `ads`
- [ ] Модели: Partner, AdUnit, AdSlot
- [ ] Админка с базовым CRUD
- [ ] Рендер виджета в шаблоне статьи
- [ ] Отслеживание кликов
- [ ] Слоты: article_middle, before_faq

### Фаза 2 — Ротация и таргетинг
- [ ] Логика выбора по приоритету
- [ ] Таргетинг по категориям
- [ ] Лимиты показов
- [ ] Временные объявления (start/end date)

### Фаза 3 — Ручные размещения
- [ ] Модель ArticleAdPlacement
- [ ] Шорткоды в статьях
- [ ] Парсинг и рендер шорткодов

### Фаза 4 — Статистика
- [ ] Dashboard с графиками
- [ ] Экспорт в CSV
- [ ] API для внешних систем

### Фаза 5 — Email интеграция
- [ ] Дополнительные поля для email
- [ ] Интеграция с рассылкой

---

## Вопросы для уточнения

1. **Система ставок (аукцион)** — ❌ Пока нет. Добавить в будущем при необходимости.
2. **AB-тестирование** — ❌ Пока нет. Добавить в будущем.
3. **Google AdSense как резерв** — ⚠️ Предусмотреть в архитектуре. Добавить отдельный AdNetwork модель и логику выбора.
4. **Кэширование** — ⚠️ Предусмотреть. Добавить в будущем (Redis, memcached).

---

## AdSense интеграция (будущее)

```python
class AdNetwork(models.Model):
    """Google AdSense, Яндекс.Директ и др."""
    name = CharField()  # "Google AdSense", "Яндекс.Директ"
    script_code = TextField()  # <script>...</script>
    slot_ids = JSONField()  # {"article_top": "123456", "article_bottom": "789012"}
    is_active = BooleanField()
```

### Логика выбора

```
Если есть активные AdUnit → показывать их
Иначе → показывать AdSense (если настроен)
```

### Кэширование (будущее)

```python
from django.core.cache import cache

def get_ad_for_slot_cached(slot, article):
    cache_key = f"ad:{slot.slug}:{article.category_id}:{datetime.date.today()}"
    
    ad = cache.get(cache_key)
    if ad is None:
        ad = get_ad_for_slot(slot, article)
        cache.set(cache_key, ad, timeout=300)  # 5 минут
    
    return ad
```

---

## Ссылки

- Trip.com Partner: https://www.trip.com/partners/
- Booking.com Affiliate: https://www.booking.com/affiliate-program.html
- Aviasales API: https://www.aviasales.ru/affiliate
