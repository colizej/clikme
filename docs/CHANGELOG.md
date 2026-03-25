# Журнал изменений — clikme.ru

Все значимые изменения проекта документируются здесь.
Формат: [Дата] — [Описание] — [Кто]

---

## [Март 2026] — Django MVP: полный перенос контента с OpenCart

### Принятые решения
- Миграция OpenCart → Django (стек: Django 6.0.3, Python 3.14, SQLite, Tailwind CSS v4 CLI)
- Отказ от e-commerce (3-4 заказа в год): каталог остаётся, корзина/оплата — нет
- Документация: README, ROADMAP, ARCHITECTURE, MIGRATION, SEO_STRATEGY, MONETIZATION, ADR

### Проект, структура, настройки
- Создан Django-проект, директория `apps/`, `config/settings.py`
- Кастомный `AbstractUser`: поля `user_type`, `points`, `telegram_id`
- `django.contrib.sites` + `django.contrib.redirects` + `SITE_ID = 1`
- `RedirectFallbackMiddleware` добавлен последним в `MIDDLEWARE`

### Импорт контента из OpenCart (`u2971222_ocar341.sql`, префикс `oc9a_`)
- **72 статьи** — `import_blog` (management command)
- **39 вендоров + 224 продукта** — `import_vendors` (management command)
- **4 статических страницы** (политика, условия, доставка, правила)
- **518 изображений** скопированы в `media/catalog/`

### SEO и редиректы
- `scripts/audit_slugs.py` — паритет-чек: 383 OpenCart URL vs Django DB
- `setup_redirects` management command — парсит `oc9a_seo_url`, создаёт 301-редиректы
- `transliterate_slugs` management command — 34 кириллических slug → Latin + redirect
- Итого **71 редирект**: 35 × категории→`/vendors/`, 34 × кирилл.→латин., 2 × функц.→`/`
- Все пути в БД хранятся percent-encoded (`/аренда/` → `/%D0%B0%D1%80%D0%B5%D0%BD%D0%B4%D0%B0/`)

### Шаблоны и фронтенд
- `base.html` + навигация (header desktop/mobile + footer): Статьи, Новости, Компании, Контакты
- Шаблоны: home, article_detail, vendor_detail, product_detail, vendor_list, news_list, news_detail, search, contacts, page_detail, 404, 500
- `templates/components/cookie_banner.html` — GDPR consent (EU-сервер)
- Поиск `GET /search/?q=` — icontains по статьям и вендорам

### SEO
- `sitemap.xml` — 117 URL (72 статьи + 39 вендоров + 4 страницы + 2 статичных)
- `robots.txt`
- canonical, meta title/description, Open Graph в шаблонах
- `slug_dispatch` view: `/<slug>/` → Article → Vendor → Product → Page (без конфликтов)

### Модели newsletter
- `Subscriber` модель, `SubscribeView` с rate limiting + honeypot
- **Форма ещё не добавлена в шаблоны** — следующий шаг

---

## [Март 2026] — Инициализация документации (начало месяца)

- Принято решение о миграции OpenCart → Django
- Создана документация: README, ROADMAP, ARCHITECTURE, MIGRATION, SEO_STRATEGY, MONETIZATION
- Зафиксированы Architecture Decision Records (ADR)
- Проанализирована структура БД (u2971222_ocar341.sql)
- Определён стек (уточнён в процессе): Django 6.0.3 + SQLite + Tailwind CSS v4 CLI

## Следующие записи добавлять по мере развития проекта...
