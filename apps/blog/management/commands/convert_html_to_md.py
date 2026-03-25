"""
Конвертирует HTML-контент статей в Markdown.

Использование:
    python manage.py convert_html_to_md             # конвертировать все (только если content_md пустой)
    python manage.py convert_html_to_md --force     # перезаписать даже если content_md уже есть
    python manage.py convert_html_to_md --dry-run   # показать предпросмотр без сохранения
    python manage.py convert_html_to_md --id 42     # конвертировать одну статью
"""
import html2text
from django.core.management.base import BaseCommand
from apps.blog.models import Article


def html_to_md(html: str) -> str:
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.ignore_tables = False
    h.body_width = 0          # не переносить строки
    h.unicode_snob = True     # Unicode вместо ASCII-аппроксимаций
    h.mark_code = True        # блоки кода в ```
    h.ul_item_mark = '-'      # маркер списка
    return h.handle(html).strip()


class Command(BaseCommand):
    help = 'Конвертирует HTML (content) → Markdown (content_md) для всех статей'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='Перезаписать content_md даже если уже заполнен')
        parser.add_argument('--dry-run', action='store_true',
                            help='Показать результат без сохранения')
        parser.add_argument('--id', type=int, dest='article_id',
                            help='Конвертировать только указанную статью по ID')

    def handle(self, *args, **options):
        force = options['force']
        dry_run = options['dry_run']
        article_id = options.get('article_id')

        qs = Article.objects.all()
        if article_id:
            qs = qs.filter(pk=article_id)
        if not force:
            qs = qs.filter(content_md='')

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.WARNING(
                'Нет статей для конвертации. '
                'Используйте --force чтобы перезаписать существующий content_md.'
            ))
            return

        self.stdout.write(f'Конвертирую {total} статей...')
        converted = 0
        errors = 0

        for article in qs.iterator():
            if not article.content:
                self.stdout.write(self.style.WARNING(f'  SKIP (нет HTML) — {article.title[:60]}'))
                continue
            try:
                md = html_to_md(article.content)
                if dry_run:
                    self.stdout.write(f'\n=== [{article.pk}] {article.title} ===')
                    self.stdout.write(md[:400] + ('...' if len(md) > 400 else ''))
                else:
                    # Обновляем content_md напрямую в БД (минуя save),
                    # потом вызываем save() чтобы перерендерить HTML из MD
                    article.content_md = md
                    article.save(update_fields=['content_md', 'content'])
                converted += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ERROR [{article.pk}] {article.title[:60]}: {e}'))
                errors += 1

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f'\nDRY-RUN: {converted} статей готовы к конвертации.'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'\nГотово: {converted} конвертировано, {errors} ошибок.'
            ))
