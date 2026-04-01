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
        elif _is_gunicorn():
            # gunicorn — только один воркер через file lock
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
        trigger=IntervalTrigger(minutes=30),
        id='publish_scheduled_news',
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()


def _publish_scheduled_news():
    """Отправляет в Telegram новости, время публикации которых наступило."""
    try:
        from django.utils import timezone
        from apps.news.models import NewsItem

        now = timezone.now()
        pending = NewsItem.objects.filter(
            status=NewsItem.PUBLISHED,
            published_at__lte=now,
            telegram_message_id='',
        )
        for item in pending:
            try:
                from apps.news.telegram import send_news_item
                ok, result = send_news_item(item)
                if ok:
                    NewsItem.objects.filter(pk=item.pk).update(telegram_message_id=result)
            except Exception:
                pass
    except Exception:
        pass
