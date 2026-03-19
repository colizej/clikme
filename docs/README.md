# КликМи (clikme.ru) — Документация проекта

## О проекте

**clikme.ru** — русскоязычный информационный сайт о Вьетнаме (Нячанг и другие направления).
Практические гиды, советы и актуальная информация для туристов и экспатов.
Аудитория: туристы из России (~60%) + русскоязычные экспаты в Нячанге (~40%).

### Текущее состояние (март 2026)
- Платформа: **OpenCart 3.x + OptimBlog 3.1.0.1**
- Хостинг: reg.ru (shared PHP)
- ~70 информационных статей, позиции 1–10 по ключевым запросам
- Монетизация: Trip.com affiliate (~$100 за 6 мес.)
- Telegram-бот: `@NhaTrang_where_eat_bot`

### Цель
Переход на **Django (Python)** с сохранением SEO-позиций.
Постепенная эволюция: информационный сайт → тематическая медиа-платформа → полноценный travel-сервис с монетизацией.

---

## Структура репозитория

```
clikme/
├── docs/               ← Документация (этот раздел)
│   ├── README.md
│   ├── ROADMAP.md
│   ├── ARCHITECTURE.md
│   ├── MIGRATION.md
│   ├── SEO_STRATEGY.md
│   ├── MONETIZATION.md
│   └── decisions/      ← Архитектурные решения (ADR)
│
├── django_project/     ← Django-проект (создаётся в Фазе 1)
│
└── opencart/           ← Архив исходного OpenCart (не пушится в git)
```

---

## Быстрый старт

### Требования
- Python 3.11+
- SQLite (встроена в Python, ничего устанавливать не нужно)

### Запуск локально
```bash
cd django_project
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py import_from_opencart  # импорт 70 статей из SQL-дампа
python manage.py runserver
```

---

## Ключевые ссылки
- Сайт: https://clikme.ru
- Google Search Console: [добавить ссылку]
- GSC Property: https://clikme.ru/
- GA4 Property ID: 517655795
- Яндекс.Вебмастер: [добавить ссылку]
- Trip.com партнёрка: Alliance ID 6229959, SID 192412375
- Telegram-бот: @NhaTrang_where_eat_bot
