# Стратегия миграции OpenCart → Django

## Принципы миграции

1. **Домен не меняется** — clikme.ru остаётся на reg.ru
2. **URL сохраняются точь-в-точь** — никаких новых slug-ов
3. **SEO-теги копируются дословно** — title, description, canonical
4. **Нулевой даунтайм** — переключение через DNS, старый сайт работает параллельно
5. **Откат за 5 минут** — если что-то пошло не так, меняем DNS обратно

---

## Структура данных OpenCart → Django

### Соответствие таблиц

| OpenCart (oc9a_) | Django модель | Поля |
|-----------------|--------------|------|
| `information` | `Article` | id, image, status, date_available, date_added |
| `information_description` | `Article` | title, short_description, description, meta_title, meta_description, meta_keyword, tag |
| `seo_url` | `Article.slug` | keyword (где query = 'information_id=X') |
| `category` | `Category` | id, image, status |
| `category_description` | `Category` | name, description, meta_title, meta_description |
| `information_to_category` | `Article.category` | связь many-to-many |

### Важно: префикс таблиц — `oc9a_` (не стандартный `oc_`)

---

## Скрипт импорта

Файл: `apps/blog/management/commands/import_from_opencart.py`

### Алгоритм

```
1. Загрузить SQL-дамп в локальную MySQL (или читать через стандартный sqlite3/re прямо из .sql файла)
2. Для каждой статьи из oc9a_information:
   a. Получить русский текст из oc9a_information_description (language_id=1 или 3)
   b. Получить slug из oc9a_seo_url WHERE query = 'information_id=X'
   c. Получить категорию из oc9a_information_to_category
   d. Очистить контент от ссылок на маркетплейс
   e. Создать Article в Django
3. Для каждой категории из oc9a_category WHERE information=1:
   a. Получить данные из oc9a_category_description
   b. Получить slug из oc9a_seo_url WHERE query = 'path=X'
   c. Создать Category в Django
```

### Очистка ссылок на маркетплейс

Ссылки которые нужно заменить в контенте статей:

```python
MARKETPLACE_PATTERNS = [
    # Маркетплейс → главная
    (r'href="https://clikme\.ru/index\.php\?route=vendor/[^"]*"', 'href="/"'),
    (r'href="https://clikme\.ru/index\.php\?route=extension/module/allproduct[^"]*"', 'href="/"'),
    # Статичные страницы маркетплейса → /
    (r'href="https://clikme\.ru/index\.php\?route=common/home"', 'href="/"'),
    (r'href="https://clikme\.ru/index\.php\?route=information/contact[^"]*"', 'href="/contacts/"'),
]
```

**Что НЕ трогать:**
- `href="https://clikme.ru/...slug..."` — ссылки на статьи (оставить)
- Trip.com iframe — оставить как есть, это монетизация
- YouTube iframe — оставить
- Внешние ссылки на другие сайты

---

## Статьи маркетплейса — что с ними делать

В базе есть ~10 статей-инструкций для партнёров маркетплейса:
- "Добавление товара на КликМи"
- "Обработка заказов на маркетплейсе"
- "Общий обзор личного кабинета"
и т.д.

**Решение:** импортировать, но закрыть от индексации:
```python
article.is_published = True   # страница существует, нет 404
article.noindex = True        # но в <head>: <meta name="robots" content="noindex">
```

Или сделать 301 редирект на тематическую статью.

---

## 301-редиректы для старых URL OpenCart

Добавить в nginx на старом хостинге (пока он ещё работает):

```nginx
# Страницы маркетплейса → главная
rewrite ^/index\.php\?route=vendor/allseller.*$ / permanent;
rewrite ^/index\.php\?route=vendor/vendor_profile.*$ / permanent;
rewrite ^/index\.php\?route=extension/module/allproduct.*$ / permanent;

# Поиск → главная
rewrite ^/index\.php\?route=product/search.*$ / permanent;

# Корзина и аккаунт (если вдруг проиндексировались)
rewrite ^/index\.php\?route=checkout.*$ / permanent;
rewrite ^/index\.php\?route=account.*$ / permanent;
```

---

## Чеклист переключения DNS

### За 1 неделю до переключения
- [ ] Django-сайт полностью готов на `new.clikme.ru`
- [ ] Все 70 статей проверены по URL-списку
- [ ] sitemap.xml генерируется корректно
- [ ] SSL работает на `new.clikme.ru`
- [ ] Скорость загрузки < 2 сек (PageSpeed > 85)

### День переключения
- [ ] Уменьшить TTL DNS до 300 сек (за сутки до)
- [ ] Сделать бэкап Django БД
- [ ] Поменять A-запись clikme.ru → IP EU-сервера
- [ ] Проверить через `dig clikme.ru` — должен показать новый IP
- [ ] Проверить 5-10 ключевых URL в браузере
- [ ] Отправить sitemap.xml в Google Search Console
- [ ] Отправить sitemap.xml в Яндекс.Вебмастер

### В течение 48 часов после переключения
- [ ] Мониторинг позиций (Google Search Console → Coverage)
- [ ] Проверить нет ли ошибок 404 в GSC
- [ ] Проверить скорость через PageSpeed Insights
- [ ] Старый сайт на reg.ru оставить жить ещё 2 месяца (301-редиректы работают)

---

## Перенос изображений

```bash
# Локально: скопировать image/catalog/ в media/catalog/
cp -r /path/to/opencart/image/catalog/ /path/to/django_project/media/catalog/

# На сервере: загрузить через rsync
rsync -avz media/catalog/ user@eu-server:/path/to/media/catalog/
```

Пути в статьях содержат: `https://clikme.ru/image/catalog/Blog Images/...`
В Django: заменить при импорте или настроить nginx alias для `/image/` → `/media/`.
