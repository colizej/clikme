# Безопасность — Production Checklist

Этот документ обязателен к выполнению перед первым деплоем на EU-сервер.

---

## Django Security Settings (settings.py)

```python
import os

# Обязательно в production
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
SECRET_KEY = os.environ['SECRET_KEY']        # минимум 50 случайных символов
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# HTTPS
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000               # 1 год
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookies
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True

# Безопасные заголовки
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
```

Проверить все настройки одной командой перед деплоем:
```bash
python manage.py check --deploy
```
Django выведет список всех проблем с безопасностью. Цель — **0 предупреждений**.

---

## Admin URL — не использовать стандартный /admin/

```python
# config/urls.py
urlpatterns = [
    path('manage-clikme-2026/', admin.site.urls),  # НЕ стандартный /admin/
    # остальные URL...
]
```

Стандартный `/admin/` — первое что перебирают боты-сканеры. Нестандартный URL убирает 99% автоматических атак. Значение URL хранить в `.env` как `ADMIN_URL`.

---

## Rate Limiting на формы

### Подписка на email (без доп. библиотек)

```python
# apps/newsletter/views.py
from django.core.cache import cache

def subscribe(request):
    if request.method == 'POST':
        # Ограничение: 1 попытка в 60 сек с одного IP
        ip = (request.META.get('HTTP_X_FORWARDED_FOR', '')
              .split(',')[0].strip()
              or request.META.get('REMOTE_ADDR', ''))
        cache_key = f'subscribe_{ip}'
        if cache.get(cache_key):
            return JsonResponse({'error': 'Слишком много запросов'}, status=429)
        cache.set(cache_key, 1, timeout=60)
        # ... остальная логика подписки
```

### Honeypot — защита от ботов

В каждую публичную форму добавить скрытое поле. Люди его не видят, боты заполняют.

```html
<!-- В HTML форме -->
<input type="text" name="website" value=""
       style="display:none" autocomplete="off" tabindex="-1">
```

```python
# В view — проверка honeypot (первой строкой)
if request.POST.get('website'):
    return HttpResponse(status=200)  # тихо игнорируем, не показываем ошибку
```

---

## CORS и CSRF

```python
# CSRF — включён по умолчанию в Django.
# Убедиться что все POST-формы содержат:
# {% csrf_token %}

# API endpoints (если появятся): добавить django-cors-headers при необходимости
# Для текущего проекта (server-rendered Django templates) CORS не нужен
```

---

## Безопасность Telegram webhook

```python
# apps/news/telegram.py — проверять что callback пришёл от Telegram
import hashlib, hmac

def verify_telegram_webhook(token, request_body, x_telegram_bot_api_secret_token):
    """Telegram позволяет задать secret_token при setWebhook"""
    expected = hmac.new(token.encode(), request_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, x_telegram_bot_api_secret_token)
```

---

## Безопасность Mollie webhook

```python
# apps/payments/views.py
# Mollie не подписывает webhook — защищаться через:
# 1. Всегда верифицировать статус платежа через API (не доверять данным из webhook request)
# 2. Проверить что payment ID существует в нашей БД

def webhook(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    payment_id = request.POST.get('id')
    if not payment_id:
        return HttpResponse(status=400)
    # ОБЯЗАТЕЛЬНО: получить актуальный статус через API, не из тела webhook
    payment = mollie_client.payments.get(payment_id)
    # ... проверить что этот payment_id мы ожидаем
```

---

## Переменные окружения (.env)

Полный список переменных — создать файл `.env` в `django_project/`, **никогда не коммитить**.

```env
# ==========================================
# ОБЯЗАТЕЛЬНЫЕ
# ==========================================
SECRET_KEY=ВставьСюда50+СлучайныхСимволов
DEBUG=False
ALLOWED_HOSTS=clikme.ru,www.clikme.ru

# Нестандартный URL для Django Admin
ADMIN_URL=manage-clikme-2026

# ==========================================
# AI / GitHub Models
# ==========================================
AI_PROVIDER=github
# Получить: github.com → Settings → Developer Settings → Personal access tokens
# Fine-grained token с правом models:read
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
# Альтернатива (если AI_PROVIDER=openai)
# OPENAI_API_KEY=sk-proj-xxx

# ==========================================
# TELEGRAM
# ==========================================
# @BotFather → /newbot → API Token
TELEGRAM_BOT_TOKEN=1234567890:ABCdefghijklmnopqrstuvwxyz
# ID канала (числовой) или @username
TELEGRAM_CHANNEL_ID=-1001234567890

# ==========================================
# ПЛАТЕЖИ — MOLLIE (западные)
# ==========================================
# test_xxx — для разработки/staging
# live_xxx — для production
MOLLIE_API_KEY=test_xxxxxxxxxxxxxxxxxxxx
# URL куда Mollie POST-ит уведомление о статусе платежа
MOLLIE_WEBHOOK_URL=https://clikme.ru/payments/webhook/

# ==========================================
# ПЛАТЕЖИ — РОССИЙСКИЕ (позже)
# ==========================================
# RUSSIAN_PAYMENT_API_KEY=...

# ==========================================
# TRIP.COM AFFILIATE
# ==========================================
TRIP_ALLIANCE_ID=6229959
TRIP_SID=192412375

# ==========================================
# EMAIL (заполнить после выбора провайдера)
# ==========================================
# EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# EMAIL_HOST=smtp.example.com
# EMAIL_PORT=587
# EMAIL_USE_TLS=True
# EMAIL_HOST_USER=noreply@clikme.ru
# EMAIL_HOST_PASSWORD=your-smtp-password
# DEFAULT_FROM_EMAIL=КликМи <noreply@clikme.ru>

# ==========================================
# БАЗА ДАННЫХ
# ==========================================
# SQLite по умолчанию — раскомментировать только при переходе на PostgreSQL
# DATABASE_URL=postgres://user:pass@localhost:5432/clikme
```

Создать `.env.example` — копию без реальных значений, эту версию коммитить в git:
```bash
cp .env .env.example
# Заменить реальные токены на плейсхолдеры перед коммитом
```

---

## Генерация SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

---

## Чеклист перед каждым деплоем

- [ ] `python manage.py check --deploy` — **0 предупреждений**
- [ ] `DEBUG=False` в `.env`
- [ ] `SECRET_KEY` — уникальный, не из документации
- [ ] `ALLOWED_HOSTS` содержит только реальные домены
- [ ] Бэкап БД: `cp db.sqlite3 db.sqlite3.bak`
- [ ] `git log --oneline -5` — нет токенов/паролей в последних коммитах
- [ ] HTTPS работает на `new.clikme.ru` перед переключением DNS

---

## Что НЕ хранить в git

Уже в `.gitignore`:
- `.env` — все секреты
- `*.sqlite3` — база данных
- `media/` — пользовательские файлы

Проверить перед первым пушем:
```bash
git ls-files | grep -E "\.env$|\.sqlite3$|media/"
```
Если что-то нашлось — немедленно удалить из истории через `git filter-repo`.
