from django.core.management.base import BaseCommand
from apps.pages.models import Page
import html2text


class Command(BaseCommand):
    help = 'Конвертирует HTML контент страниц в Markdown'

    def handle(self, *args, **options):
        h = html2text.HTML2Text()
        h.body_width = 0  # Не обрезать строки
        h.ignore_links = False
        h.ignore_images = False
        h.ignore_emphasis = False
        
        pages = Page.objects.all()
        count = 0
        
        for page in pages:
            if page.content and not page.content_md:
                md = h.handle(page.content)
                page.content_md = md.strip()
                page.save(update_fields=['content_md'])
                count += 1
                self.stdout.write(f'{page.slug}: конвертирован ({len(md)} символов)')
        
        self.stdout.write(
            self.style.SUCCESS(f'\nГотово! Конвертировано {count} страниц')
        )
