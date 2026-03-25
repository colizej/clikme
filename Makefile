PYTHON = venv/bin/python
PORT   = 8003
HOST   = 127.0.0.1

.PHONY: dev css watch kill migrate superuser check collect deploy-check deploy status

# ── Основная команда разработки ──────────────────────────────────────────────
dev: kill css
	$(PYTHON) manage.py runserver $(HOST):$(PORT)

# ── Tailwind: однократная сборка (minify) ─────────────────────────────────────
css:
	./tailwindcss -i static/css/input.css -o static/css/style.css --minify

# ── Tailwind: watch-режим (в отдельном терминале) ────────────────────────────
watch:
	./tailwindcss -i static/css/input.css -o static/css/style.css --watch

# ── Убить процесс на порту ────────────────────────────────────────────────────
kill:
	@-lsof -ti tcp:$(PORT) | xargs kill -9 2>/dev/null; true

# ── Django helpers ────────────────────────────────────────────────────────────
migrate:
	$(PYTHON) manage.py migrate

superuser:
	$(PYTHON) manage.py createsuperuser

check:
	$(PYTHON) manage.py check

# ── Deploy helpers ────────────────────────────────────────────────────────────
collect:
	$(PYTHON) manage.py collectstatic --noinput

deploy-check:
	$(PYTHON) manage.py check --deploy

# ── Ручной деплой (на сервере) ────────────────────────────────────────────────
deploy:
	git pull origin main
	. venv/bin/activate && pip install -r requirements.txt -q
	$(PYTHON) manage.py migrate --run-syncdb
	$(PYTHON) manage.py collectstatic --no-input --clear
	./tailwindcss -i static/css/input.css -o static/css/style.css --minify
	sudo systemctl restart clikme

status:
	sudo systemctl status clikme
