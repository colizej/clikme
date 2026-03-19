# Инфраструктура — clikme.ru

## Сервер

| Параметр | Значение |
|---------|---------|
| Хостинг | EU VPS (Hetzner / DigitalOcean / Contabo) |
| ОС | Ubuntu 22.04 LTS |
| Python | 3.11+ |
| Web-сервер | **Caddy** (авто SSL, без certbot) |
| WSGI | **gunicorn** (3 workers) |
| БД | SQLite (WAL mode) |

---

## Структура директорий на сервере

```
/var/www/clikme/
├── django_project/
│   ├── venv/
│   ├── manage.py
│   ├── config/
│   ├── apps/
│   ├── templates/
│   ├── static/
│   │   └── css/style.css       ← собранный Tailwind (в git)
│   ├── staticfiles/            ← collectstatic output (не в git)
│   ├── media/                  ← загруженные файлы (не в git)
│   ├── db.sqlite3             ← база данных (не в git)
│   ├── db.sqlite3.bak         ← ручной бэкап
│   ├── requirements.txt
│   ├── tailwindcss            ← CLI-бинарь (не в git)
│   └── .env                   ← секреты (не в git)
└── Caddyfile
```

---

## Caddy

Caddy автоматически получает и продлевает SSL через Let's Encrypt.
Не нужен certbot, не нужна ручная настройка HTTPS.

**Установка:**
```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy
```

**`/etc/caddy/Caddyfile`:**
```
clikme.ru, www.clikme.ru {
    # www → non-www
    @www host www.clikme.ru
    redir @www https://clikme.ru{uri} permanent

    # Сжатие
    encode gzip zstd

    # Статика (длительный кэш)
    handle /static/* {
        root * /var/www/clikme/django_project
        file_server
        header Cache-Control "public, max-age=31536000, immutable"
    }

    handle /media/* {
        root * /var/www/clikme/django_project
        file_server
        header Cache-Control "public, max-age=604800"
    }

    # Django приложение
    handle {
        reverse_proxy localhost:8000
    }
}

# Staging-окружение
new.clikme.ru {
    reverse_proxy localhost:8001
}
```

```bash
sudo systemctl reload caddy
```

---

## gunicorn (systemd)

**`/etc/systemd/system/clikme.service`:**
```ini
[Unit]
Description=clikme.ru — Django Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/clikme/django_project
ExecStart=/var/www/clikme/django_project/venv/bin/gunicorn \
    --workers 3 \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/log/clikme/access.log \
    --error-logfile /var/log/clikme/error.log \
    --timeout 30 \
    config.wsgi:application
EnvironmentFile=/var/www/clikme/django_project/.env
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo mkdir -p /var/log/clikme
sudo chown www-data:www-data /var/log/clikme
sudo systemctl daemon-reload
sudo systemctl enable clikme
sudo systemctl start clikme
sudo systemctl status clikme
```

---

## Деплой (ручной)

```bash
cd /var/www/clikme/django_project
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --quiet
python manage.py migrate --run-syncdb
python manage.py collectstatic --no-input --clear
# Tailwind пересборка (если менялись шаблоны)
./tailwindcss -i static/css/input.css -o static/css/style.css --minify
sudo systemctl restart clikme
```

**Makefile (опционально):**
```makefile
deploy:
	git pull origin main
	source venv/bin/activate && pip install -r requirements.txt -q
	python manage.py migrate --run-syncdb
	python manage.py collectstatic --no-input --clear
	sudo systemctl restart clikme

status:
	sudo systemctl status clikme
```

---

## Staging-окружение (new.clikme.ru)

Отдельный gunicorn на порту 8001:

**`/etc/systemd/system/clikme-staging.service`:**
```ini
[Unit]
Description=clikme.ru — Staging

[Service]
User=www-data
WorkingDirectory=/var/www/clikme/django_project
ExecStart=/var/www/clikme/django_project/venv/bin/gunicorn \
    --workers 2 \
    --bind 127.0.0.1:8001 \
    config.wsgi:application
EnvironmentFile=/var/www/clikme/django_project/.env.staging
Restart=on-failure
```

`.env.staging` — отдельный файл с `DEBUG=True`, `MOLLIE_API_KEY=test_xxx`.

---

## SQLite — ручной бэкап

```bash
# Перед каждым деплоем (обязательно)
cd /var/www/clikme/django_project
cp db.sqlite3 "db.sqlite3.$(date +%Y%m%d)"

# Скачать бэкап на свой Mac
rsync -avz user@eu-server:/var/www/clikme/django_project/db.sqlite3 \
    ~/backups/clikme/db.sqlite3.$(date +%Y%m%d)

# Удалить старые бэкапы (оставить последние 7)
ls -t db.sqlite3.* | tail -n +8 | xargs rm -f
```

**SQLite WAL mode** — для лучшей параллельности чтения:
```python
# config/settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {'timeout': 20},
    }
}

# После создания БД — включить WAL mode (один раз)
# python manage.py shell -c "from django.db import connection; connection.cursor().execute('PRAGMA journal_mode=WAL')"
```

---

## Tailwind CLI на сервере

Tailwind CLI-бинарь скачивается один раз и не хранится в git:

```bash
# На сервере (Linux x86_64)
curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64
chmod +x tailwindcss-linux-x64
mv tailwindcss-linux-x64 tailwindcss

# На Mac (arm64)
curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-macos-arm64
chmod +x tailwindcss-macos-arm64
mv tailwindcss-macos-arm64 tailwindcss
```

Собранный `static/css/style.css` хранится в git → на сервере пересборка нужна только при изменении шаблонов.

---

## Мониторинг

| Инструмент | Что мониторит | Как |
|-----------|--------------|-----|
| Django logging | Ошибки 500, exceptions | `/var/log/clikme/error.log` |
| Caddy access log | HTTP запросы, статусы | `journalctl -u caddy -f` |
| **UptimeRobot** | Uptime сайта (бесплатно) | Alert на email при падении |
| Google Search Console | Индексация, crawl errors | Еженедельно |
| Яндекс.Вебмастер | РФ-аудитория | Еженедельно |

**Django logging config (settings.py):**
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs/django.log',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'ERROR',
    },
}
```

---

## Checklist первого запуска EU-сервера

- [ ] VPS создан, SSH-ключ добавлен
- [ ] Ubuntu обновлена: `apt update && apt upgrade -y`
- [ ] Caddy установлен
- [ ] Python 3.11+ установлен
- [ ] Создан пользователь `www-data` для gunicorn
- [ ] Репозиторий склонирован в `/var/www/clikme/`
- [ ] venv создан, зависимости установлены
- [ ] `.env` создан с реальными значениями
- [ ] `python manage.py migrate` выполнен
- [ ] `python manage.py collectstatic` выполнен
- [ ] `python manage.py createsuperuser` выполнен
- [ ] `python manage.py check --deploy` — 0 предупреждений
- [ ] systemd сервис `clikme.service` создан и запущен
- [ ] Caddyfile настроен, SSL получен автоматически
- [ ] Сайт открывается на `new.clikme.ru` по HTTPS
- [ ] UptimeRobot настроен на `new.clikme.ru`
