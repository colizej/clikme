from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.news.models import NewsItem


class Command(BaseCommand):
    help = 'Публикует запланированные новости в Telegram (запускать каждую минуту через cron)'

    def handle(self, *args, **options):
        now = timezone.now()

        # Новости с PUBLISHED статусом, время пришло, ещё не отправлены в Telegram
        pending = NewsItem.objects.filter(
            status=NewsItem.PUBLISHED,
            published_at__lte=now,
            telegram_message_id='',
        )

        count = 0
        for item in pending:
            try:
                from apps.news.telegram import send_news_item
                ok, result = send_news_item(item)
                if ok:
                    NewsItem.objects.filter(pk=item.pk).update(telegram_message_id=result)
                    count += 1
                    self.stdout.write(f'  ✓ Отправлено: {item.title[:60]}')
                else:
                    self.stdout.write(self.style.WARNING(f'  ✗ Ошибка: {item.title[:60]} — {result}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Исключение: {item.title[:60]} — {e}'))

        if count:
            self.stdout.write(self.style.SUCCESS(f'Опубликовано в Telegram: {count}'))
