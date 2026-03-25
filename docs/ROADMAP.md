# Roadmap — clikme.ru

> Последнее обновление: 25 марта 2026

---

## ✅ Спринт март 2026 — ЗАВЕРШЁН

### 1. Страница `/delivery/` — убрать без вреда для SEO ✅
- [x] Удалить Page объект `/delivery/` из БД
- [x] Создать 301-редирект `/delivery/` → `/` через `django.contrib.redirects`

### 2. Битые редиректы вендоров (29 шт.) → `/vendors/` ✅
- [x] 72 редиректа — все валидны, ни один не ведёт в 404
- [x] 65 → `/vendors/`, 3 → `/`, 4 → конкретные страницы

### 3. Теги и категории статей ✅
- [x] 9 тегов созданы из OpenCart SQL: обзор, где покушать, что смотреть, гид, пляжи, аренда, медицина, шопинг, буфеты
- [x] 1 категория «Блог» создана (как на оригинальном сайте — плоская структура)
- [x] management command `import_tags` — назначил теги 58/72 статьям, категорию всем 72
- [ ] Шаблоны: показать теги на карточках и странице статьи `article_detail.html`
- [ ] Добавить фильтрацию по тегу на странице блога

### 4. Новости — ждём структуру от пользователя
- [ ] Пользователь предоставит структуру (источники, формат, категории)
- [ ] Настроить `NewsSource` записи в admin
- [ ] Протестировать `fetch_news` management command
- [ ] Добавить `fetch_news` в cron / GitHub Actions scheduled workflow

---

## Фаза 0 — Подготовка (март 2026) ✅

- [x] Анализ текущей OpenCart-структуры
- [x] Экспорт базы данных (u2971222_ocar341.sql)
- [x] Изучение URL-структуры и SEO-данных
- [x] Выбор стратегии миграции
- [x] Создание документации и roadmap
- [x] EU-сервер существует, несколько проектов работают
- [ ] Зафиксировать текущие позиции в Google Search Console (baseline CSV)
- [ ] Настроить GitHub Actions автодеплой (`.github/workflows/deploy.yml`)

---

## Принципы разработки (соблюдать на всех фазах)

### Компоненты — переиспользование вместо копипаста

Каждый повторяющийся элемент UI выносится в отдельный шаблон-компонент
и подключается через `{% include %}`. Писать один раз — использовать везде.

**Структура компонентов:**
```
templates/
└── components/
    ├── cookie_banner.html      ← ✅ GDPR cookie consent
    ├── subscribe_form.html     ← ⬜ форма подписки (view готов, шаблон нужен)
    ├── article_card.html       ← ⬜ карточка статьи (лента, поиск, похожие)
    ├── seo_meta.html           ← ⬜ <title>, <meta>, canonical, OG-теги
    ├── breadcrumbs.html        ← ⬜ хлебные крошки
    ├── affiliate_block.html    ← ⬜ партнёрский виджет (Trip.com и др.)
    └── share_buttons.html      ← ⬜ кнопки «поделиться»
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

## Фаза 1 — Django MVP: Зеркало сайта ✅ (март 2026)

**Цель:** Запустить полное зеркало clikme.ru на Django с новым дизайном.
Весь контент перенесён, SEO-позиции сохранены через 301-редиректы.

### Django-приложения
- [x] `blog` — **72 статьи** из OpenCart (все published, все с фото и Markdown)
- [x] `vendors` — **39 вендоров + 224 продукта** из OpenCart
- [x] `news` — модели NewsSource/NewsItem готовы; источники не настроены
- [x] `pages` — **4 статичные страницы** (политика, условия, доставка, правила)
- [x] `users` — кастомный AbstractUser (tourist/expat/business + points + telegram_id)
- [x] `newsletter` — `Subscriber` модель, `SubscribeView` с rate limiting + honeypot

### Технические задачи
- [x] Настройка проекта (Django 6.0.3, Python 3.14, SQLite, Tailwind CSS v4 CLI)
- [x] Models: Article, Category, Tag, Vendor, Product, NewsSource, NewsItem, **ArticleFAQ**
- [x] `scripts/audit_slugs.py` — паритет URL OpenCart vs Django
- [x] `import_blog` — импорт статей из SQL; `import_vendors` — вендоры + продукты
- [x] `slug_dispatch` в `apps/blog/views.py` — Article → Vendor → Product → Page
- [x] SEO: canonical, meta title/description, Open Graph в шаблонах
- [x] **Article JSON-LD** (ImageObject, keywords, articleSection, inLanguage, dateModified)
- [x] **BreadcrumbList JSON-LD** (3 уровня: home → category → article)
- [x] **FAQPage JSON-LD** — условный блок если есть `ArticleFAQ` записи
- [x] **Twitter Card** meta-теги в `article_detail.html`
- [x] `sitemap.xml` — 117 URLs
- [x] `robots.txt`
- [x] Медиа-файлы перенесены: 518 изображений → `media/`
- [x] Шаблоны: base, home, article_detail, vendor_detail, product_detail, vendor_list, news_list, news_detail, search, contacts, page_detail, 404, 500
- [x] Поиск `GET /search/?q=`
- [x] GDPR cookie consent banner (`templates/components/cookie_banner.html`)
- [x] 404 и 500 страницы
- [x] Навигация — desktop + **мобильный drawer** (выезжает справа, SVG-иконки, backdrop, Esc)
- [x] `django.contrib.redirects` — **71 редирект** (⚠️ 31 ведут в 404 — см. TODO #2)
- [x] `django.contrib.sites` — domain обновлён: `clikme.ru` ✅
- [x] **Markdown-редактор** в Django admin (EasyMDE, CDN)
- [x] `Article.content_md` — Markdown-источник; `Article.content` — рендерится автоматически
- [x] `Article.image_alt` — SEO alt-текст для изображений
- [x] `convert_html_to_md` — все 72 статьи конвертированы HTML → Markdown
- [x] Суперпользователь `admin` создан
- [x] `make collect` (133 файла), `make deploy-check`, `make deploy`, `make status`
- [x] `.github/workflows/deploy.yml` — GitHub Actions автодеплой
- [x] `docs/Caddyfile.snippet` — конфиг для Caddy

### 🔴 Остаток (см. TODO выше)
- [ ] `/delivery/` — 301 → `/` (Task #1)
- [ ] Битые редиректы вендоров — 31 шт. → `/vendors/` (Task #2)
- [ ] Теги и категории статей (Task #3)
- [ ] Новости — источники + fetch (Task #4)

### После публикации
- [ ] Зафиксировать позиции в Google Search Console (baseline)
- [ ] Настроить Caddy на сервере (`docs/Caddyfile.snippet`)
- [ ] **Переключение DNS clikme.ru → EU-сервер** (финальный шаг)
- [ ] Настроить Mailjet SMTP ключи в `.env`

### Метрики успеха Фазы 1
- [x] 72 статьи + 39 вендоров + 224 продукта + 4 страницы доступны по правильным URL
- [x] 71 редирект покрывает старые OpenCart URLs (⚠️ 31 нужно исправить)
- [ ] Позиции в Google не ниже -2 позиций от baseline (проверить +4 недели после деплоя)
- [ ] Newsletter форма работает, первые подписчики

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
| Backend | **Django 6.0.3** (Python 3.14) | Опыт разработчика |
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
