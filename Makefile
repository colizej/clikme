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
