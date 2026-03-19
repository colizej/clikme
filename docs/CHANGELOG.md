# Журнал изменений — clikme.ru

Все значимые изменения проекта документируются здесь.
Формат: [Дата] — [Описание] — [Кто]

---

## [Март 2026] — Инициализация документации

- Принято решение о миграции OpenCart → Django
- Создана документация: README, ROADMAP, ARCHITECTURE, MIGRATION, SEO_STRATEGY, MONETIZATION
- Зафиксированы Architecture Decision Records (ADR)
- Проанализирована структура БД (u2971222_ocar341.sql):
  - Префикс таблиц: `oc9a_`
  - ~70 статей в `oc9a_information`
  - SEO slug-и в `oc9a_seo_url`
  - Два типа URL: `/slug/` и `/cat/slug/`
  - Trip.com виджеты встроены в HTML статей (сохранять при импорте)
- Идентифицированы статьи маркетплейса (~10 шт) — закрыть noindex после миграции
- Определён стек: Django 5 + PostgreSQL + Redis + Bootstrap 5 + HTMX

## Следующие записи добавлять по мере развития проекта...
