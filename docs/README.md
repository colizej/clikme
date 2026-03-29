# 📚 Документация ClikMe

> Навигация по документации проекта

---

## 🚀 Быстрый старт

| Ресурс | Описание |
|---------|----------|
| [README](./README.md) | Обзор проекта |
| [INFRASTRUCTURE](./INFRASTRUCTURE.md) | Сервер, VPS, деплой |
| [ARCHITECTURE](./ARCHITECTURE.md) | Архитектура приложения |

---

## 📋 Основная документация

### Разработка
| Документ | Описание |
|----------|----------|
| [CHANGELOG](./CHANGELOG.md) | История изменений |
| [ROADMAP](./ROADMAP.md) | Планы развития |
| [COMMANDS](./COMMANDS.md) | **Список всех команд** |

### Миграция
| Документ | Описание |
|----------|----------|
| [MIGRATION](./MIGRATION.md) | Миграция с OpenCart |
| [MIGRATION_REPORT](./MIGRATION_REPORT.md) | Отчёт о миграции |

### SEO и монетизация
| Документ | Описание |
|----------|----------|
| [SEO_STRATEGY](./SEO_STRATEGY.md) | SEO оптимизация |
| [ADS_SYSTEM](./ADS_SYSTEM.md) | Рекламная система |
| [MONETIZATION](./MONETIZATION.md) | Стратегия монетизации |

### Безопасность и инфраструктура
| Документ | Описание |
|----------|----------|
| [SECURITY](./SECURITY.md) | Безопасность |
| [INFRASTRUCTURE](./INFRASTRUCTURE.md) | Инфраструктура |
| [Caddyfile.snippet](./Caddyfile.snippet) | Конфиг Caddy |

---

## 🛠 Управление командами (Management Commands)

Подробная документация: [COMMANDS](./COMMANDS.md)

### Часто используемые команды

```bash
# Разработка
python manage.py runserver                    # Запуск сервера
python manage.py collectstatic --noinput       # Сбор статики

# Миграции
python manage.py migrate                     # Применить миграции
python manage.py makemigrations               # Создать миграцию

# Контент
python manage.py import_blog                 # Импорт статей из OpenCart
python manage.py import_vendors               # Импорт вендоров
python manage.py fetch_news                  # Получить новости

# Изображения
python manage.py convert_images_to_webp      # Конвертировать в WebP
python manage.py migrate_images              # Миграция изображений

# SEO
python manage.py sitemap_regenerate          # Пересоздать sitemap
```

---

## 📁 Структура проекта

```
clikme/
├── apps/
│   ├── blog/           # Статьи
│   ├── vendors/        # Вендоры и продукты
│   ├── news/           # Новости
│   ├── pages/          # Страницы
│   ├── newsletter/      # Рассылка
│   ├── ads/           # Реклама
│   └── users/         # Пользователи
├── config/              # Django settings
├── templates/           # Шаблоны
├── static/             # Статика
├── media/              # Загруженные файлы
├── docs/               # Эта документация
└── scripts/            # Скрипты
```

---

## 🔗 Быстрые ссылки

| Сервис | URL |
|--------|-----|
| Сайт | https://clikme.ru |
| Админка | /admin/ |
| Sitemap | /sitemap.xml |
| Robots.txt | /robots.txt |

---

*Обновлено: {% now "d.m.Y" %}*
