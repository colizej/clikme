PYTHON = venv/bin/python
PORT   = 8003
HOST   = 127.0.0.1

.PHONY: dev css watch kill migrate superuser check

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
