css:
	./tailwindcss -i static/css/input.css -o static/css/style.css --minify

dev:
	@echo "Stopping existing server..."
	@pkill -f "runserver 0.0.0.0:8003" 2>/dev/null || true
	@echo "Building Tailwind CSS..."
	./tailwindcss -i static/css/input.css -o static/css/style.css --minify
	@echo "Starting dev server on port 8003..."
	python3 manage.py runserver 0.0.0.0:8003

deploy:
	git pull origin main
	source venv/bin/activate && pip install -r requirements.txt -q
	python manage.py migrate --run-syncdb
	python manage.py collectstatic --no-input --clear
	sudo systemctl restart clikme

status:
	sudo systemctl status clikme

logs:
	sudo journalctl -u clikme -f
