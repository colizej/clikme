# Roadmap — clikme.ru

> Последнее обновление: март 2026

---

## Фаза 0 — Подготовка (март 2026) ✅

- [x] Анализ текущей OpenCart-структуры
- [x] Экспорт базы данных (u2971222_ocar341.sql)
- [x] Изучение URL-структуры и SEO-данных
- [x] Выбор стратегии миграции
- [x] Создание документации и roadmap
- [ ] Зафиксировать текущие позиции в Google Search Console (baseline)
- [ ] Настроить EU-сервер для разработки
- [ ] Настроить поддомен `new.clikme.ru` → EU-сервер

---

## Принципы разработки (соблюдать на всех фазах)

### Компоненты — переиспользование вместо копипаста

Каждый повторяющийся элемент UI выносится в отдельный шаблон-компонент
и подключается через `{% include %}`. Писать один раз — использовать везде.

**Структура компонентов:**
```
templates/
└── components/
    ├── article_card.html       ← карточка статьи (лента, поиск, похожие)
    ├── category_badge.html     ← бейдж категории
    ├── pagination.html         ← пагинация (везде одинаковая)
    ├── seo_meta.html           ← <title>, <meta>, canonical, OG-теги
    ├── breadcrumbs.html        ← хлебные крошки
    ├── subscribe_form.html     ← форма подписки на email
    ├── affiliate_block.html    ← партнёрский виджет (Trip.com и др.)
    ├── share_buttons.html      ← кнопки "поделиться"
    ├── news_card.html          ← карточка новости
    └── listing_card.html       ← карточка объявления (Фаза 2)
```

**Правило:** если один и тот же HTML появляется в двух местах — это компонент.

**Пример использования:**
```html
<!-- article_detail.html -->
{% include "components/seo_meta.html" with title=article.meta_title description=article.meta_description %}
{% include "components/breadcrumbs.html" with items=breadcrumbs %}
{% include "components/affiliate_block.html" with category=article.category %}
{% include "components/subscribe_form.html" %}
{% include "components/share_buttons.html" with url=article.get_absolute_url %}
```

**Templatetags** — для логики которую нельзя вынести в шаблон:
```
blog/templatetags/
├── blog_tags.py    ← {% latest_articles %}, {% related_articles %}
└── seo_tags.py     ← {% canonical_url %}, {% og_image %}
```

---

## Фаза 1 — Django MVP: Блог (апрель 2026)

**Цель:** Запустить Django-версию сайта с полным контентом блога.
SEO-позиции сохранены, URL идентичны.

### Django-приложения
- [ ] `blog` — статьи, категории, теги (~86 статей из OpenCart)
- [ ] `vendors` — магазины, рестораны, сервисы (~42 вендора + ~280 продуктов)
- [ ] `news` — лента новостей (парсинг источников + публикация на сайт + дубль в Telegram)
- [ ] `pages` — статичные страницы (о нас, контакты, виза)
- [ ] `users` — кастомный AbstractUser (основа для всего остального)
- [ ] `newsletter` — подписка на рассылку (с первого дня!)

### Технические задачи
- [ ] Настройка проекта (settings, SQLite)
- [ ] Django models — Article, Category, Tag, Vendor, Product, NewsSource, NewsItem
- [ ] **Скрипт parity check** — до миграции сохранить все URL оригинала; после — сравнивать
- [ ] Скрипт импорта из OpenCart SQL (`import_from_opencart` — статьи + вендоры + продукты)
- [ ] URL-паттерны: `/slug/`, `/cat/slug/`, vendor slug, product slug (без конфликтов)
- [ ] SEO: canonical, meta title/description, Open Graph, sitemap.xml
- [ ] robots.txt
- [ ] Перенос изображений (image/catalog/ → media/)
- [ ] Базовые шаблоны (base, article, vendor, product, home)
- [ ] Форма подписки на email в конце каждой статьи
- [ ] Конверсия изображений в WebP при импорте (`to_webp()` в import_from_opencart)
- [ ] 404 и 500 страницы с дизайном сайта
- [ ] Поиск `GET /search/?q=` — статьи + вендоры (Django icontains, Фаза 1)
- [ ] Политика конфиденциальности — перенести из OpenCart как страницу `pages`
- [ ] `python manage.py check --deploy` — 0 предупреждений перед деплоем
- [ ] Настройка Caddy + gunicorn на EU-сервере (Caddy — автоматический SSL)
- [ ] Переключение DNS clikme.ru → EU-сервер

### Метрики успеха Фазы 1
- Все ~86 статей и ~42 страницы вендоров доступны по оригинальным URL
- Parity check скрипт показывает 0 ошибок (404, title mismatch)
- Позиции в Google не ниже -2 позиций от baseline
- Email-форма работает, первые подписчики
- Раздел новостей работает: fetch → модерация → публикация → Telegram

---

## Фаза 2 — Рост: Каталог мест + Объявления (июнь 2026)

**Цель:** Монетизация экспатской аудитории.

### Django-приложения
- [ ] `directory` — каталог мест (рестораны, отели, экскурсии, сервисы)
  - Карточка места: фото, описание, адрес, часы, цены, ссылки
  - Рейтинг и отзывы
  - Платное размещение / "Премиум"-статус
- [ ] `listings` — доска объявлений
  - Категории: аренда, работа, продажа, услуги
  - Бесплатно: 1 активное объявление
  - Платно: поднятие, выделение, срочные
- [ ] `reviews` — отзывы пользователей к местам и статьям

### Монетизация
- Платные размещения бизнеса в каталоге (абонемент / разовое)
- Платные поднятия объявлений
- Увеличение affiliate-трафика через целевые статьи + каталог

---

## Фаза 3 — Сообщество + Автоматизация (сентябрь 2026)

**Цель:** Удержание аудитории, UGC, рост органики.

### Django-приложения
- [ ] `gamification` — баллы, бейджи, уровни
  - Баллы: написал отзыв (+10), статью (+50), привёл друга (+50)
  - Бейджи: "Гурман Нячанга", "Местный эксперт", "Первый шаг"
- [ ] `comments` — комментарии к статьям (django-contrib-comments или кастомные)
- [ ] Video-тип контента — статьи с YouTube embed + SEO-обёртка

### Автоматизация
- [ ] Telegram-бот интеграция (Django webhook → @NhaTrang_where_eat_bot)
  - Новая статья → пост в Telegram-канал
  - Новое объявление → пост в тематический чат
- [ ] Email-рассылки через Django SMTP backend (без Celery)
- [ ] Автопостинг в Telegram через webhook (стандартный urllib/requests)

---

## Фаза 4 — Масштабирование (2027)

**Цель:** Полноценная travel-платформа.

- [ ] Мультиязычность (en, vi) — `django-modeltranslation`
- [ ] Маркетплейс full — развитие `vendors` приложения из Фазы 1
  - Заказы, оплата, личный кабинет продавца
  - Рейтинги и отзывы на продукты
  - Актуально если Telegram ограничат в РФ
- [ ] Мобильная версия / PWA
- [ ] Переезд на reg.ru VPS (опционально)
- [ ] Подключение дополнительных партнёрок: Booking.com, Airalo, страховки

---

## Стек технологий

### Принцип: чистый Django, минимум сторонних библиотек

| Слой | Технология | Причина |
|------|-----------|--------|
| Backend | Django 5.x | Опыт разработчика |
| БД | **SQLite** | Встроена в Python, достаточно для проекта |
| Кэш | Django cache (файловый) | Встроен, Redis не нужен на старте |
| Очереди | — | Django email backend, без Celery |
| Frontend | **Tailwind CSS v4 CLI** + минимум JS | Utility-first, без Bootstrap-look, CLI без npm в prod |
| Медиа | Локально на сервере | Без S3/R2 на старте |
| Email | Django SMTP backend | Встроен, без сторонних сервисов |
| Деплой | gunicorn + Caddy + systemd | Caddy = авто SSL, проще nginx |
| Платежи | Mollie API (западные) + RU провайдер позже | Фаза 2 |
| Поиск | Django icontains → SQLite FTS5 | Фаза 1 → Фаза 2 |
| CI/CD | GitHub Actions | Автодеплой (опционально) |
