import fcntl
import os
import tempfile

from django.apps import AppConfig

_lock_file = None  # держим ссылку чтобы GC не закрыл файл и не снял замок


class NewsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.news'

    def ready(self):
        if os.environ.get('RUN_MAIN') == 'true':
            # runserver — запускаем только в одном процессе
            _start_scheduler()
        else:
            # gunicorn и любой другой сервер — только один воркер через file lock
            _start_scheduler_locked()


def _is_gunicorn():
    import sys
    return 'gunicorn' in sys.modules


def _start_scheduler_locked():
    global _lock_file
    lock_path = os.path.join(tempfile.gettempdir(), 'clikme_scheduler.lock')
    try:
        _lock_file = open(lock_path, 'w')
        fcntl.flock(_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _start_scheduler()
    except (IOError, OSError):
        pass  # другой воркер уже держит замок


def _start_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    scheduler = BackgroundScheduler(timezone='UTC')
    scheduler.add_job(
        _publish_scheduled_news,
        trigger=IntervalTrigger(minutes=5),
        id='publish_scheduled_news',
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()


def _publish_scheduled_news():
    """Отправляет в Telegram новости, время публикации которых наступило."""
    import datetime
    from pathlib import Path
    from django.conf import settings

    log_dir = Path(settings.BASE_DIR) / 'logs'
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / 'publish_scheduled.log'

    def log(msg):
        ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        line = f'[{ts}] {msg}\n'
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(line)

    try:
        from django.utils import timezone
        from apps.news.models import NewsItem

        now = timezone.now()
        pending = list(NewsItem.objects.filter(
            status=NewsItem.PUBLISHED,
            published_at__lte=now,
            telegram_message_id='',
        ))

        if not pending:
            log('Нет новостей для публикации')
            return

        log(f'Найдено для публикации: {len(pending)}')
        for item in pending:
            try:
                from apps.news.telegram import send_news_item
                ok, result = send_news_item(item)
                if ok:
                    NewsItem.objects.filter(pk=item.pk).update(telegram_message_id=result)
                    log(f'✓ Опубликовано: {item.title[:60]}')
                else:
                    log(f'✗ Ошибка: {item.title[:60]} — {result}')
            except Exception as e:
                log(f'✗ Исключение: {item.title[:60]} — {e}')
    except Exception as e:
        log(f'Критическая ошибка: {e}')
