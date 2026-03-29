# 🛠 Management Commands — Справка по командам

> Все команды запускаются через `python manage.py <command>`

---

## 📄 Блог (Blog)

### import_blog
Импорт статей из OpenCart SQL дампа.

```bash
python manage.py import_blog
python manage.py import_blog --dry-run        # Только показать
python manage.py import_blog --skip-images    # Без изображений
python manage.py import_vendors --skip-copy   # Без копирования файлов
```

### convert_html_to_md
Конвертация HTML контента в Markdown.

```bash
python manage.py convert_html_to_md
python manage.py convert_html_to_md --dry-run
```

### convert_pages_to_md
Конвертация HTML страниц в Markdown.

```bash
python manage.py convert_pages_to_md
```

---

## 🏪 Вендоры (Vendors)

### import_vendors
Импорт вендоров и продуктов из OpenCart.

```bash
python manage.py import_vendors
python manage.py import_vendors --dry-run
python manage.py import_vendors --skip-images
```

---

## 🖼 Изображения (Images)

### convert_images_to_webp
Конвертация всех изображений в WebP формат.

```bash
python manage.py convert_images_to_webp              # Конвертировать все
python manage.py convert_images_to_webp --dry-run    # Только показать
python manage.py convert_images_to_webp --quality=90 # Качество 90%
python manage.py convert_images_to_webp --max-width=1200 # Макс. ширина
```

**Параметры:**
| Параметр | По умолчанию | Описание |
|----------|-------------|---------|
| `--quality` | 85 | Качество WebP (1-100) |
| `--max-width` | 1920 | Максимальная ширина |

### migrate_images
Миграция изображений из OpenCart.

```bash
python manage.py migrate_images              # Копировать и переписать URL
python manage.py migrate_images --dry-run   # Только показать
python manage.py migrate_images --skip-copy  # Только переписать URL
python manage.py migrate_images --skip-rewrite # Только копировать
```

---

## 📰 Новости (News)

### fetch_news
Получение новостей из RSS источников.

```bash
python manage.py fetch_news
python manage.py fetch_news --limit=10  # Лимит
```

---

## 🔍 SEO

### audit_slugs
Аудит slug'ов и проверка URL.

```bash
python manage.py audit_slugs
```

---

## 🔧 Django стандартные

### Миграции базы данных
```bash
python manage.py migrate                    # Применить миграции
python manage.py makemigrations              # Создать миграцию
python manage.py makemigrations --dry-run   # Показать без создания
python manage.py migrate --plan             # Показать план миграций
```

### Статика
```bash
python manage.py collectstatic              # Собрать статику
python manage.py collectstatic --noinput    # Без вопросов
python manage.py collectstatic --clear       # Очистить перед сборкой
```

### Сервер
```bash
python manage.py runserver                  # Локальный сервер
python manage.py runserver 0.0.0.0:8000   # Доступный извне
```

### Суперпользователь
```bash
python manage.py createsuperuser           # Создать админа
python manage.py changepassword admin       # Изменить пароль
```

### Django shell
```bash
python manage.py shell                     # Интерактивная консоль
```

### Проверка
```bash
python manage.py check                    # Проверить ошибки
python manage.py check --deploy           # Проверка для продакшена
```

---

## 📊 Статистика

### show_urls
Показать все URL маршруты.

```bash
python manage.py show_urls
```

---

## 🧪 Тестирование

```bash
python manage.py test                      # Запустить тесты
python manage.py test apps.blog           # Тесты только для blog
```

---

## 📝 Требования

Для работы некоторых команд нужны пакеты:

```bash
pip install Pillow         # Для изображений
pip install html2text     # Для конвертации HTML → Markdown
```

---

*Обновлено: {% now "d.m.Y" %}*
