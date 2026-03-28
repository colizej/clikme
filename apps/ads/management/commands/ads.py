from django.core.management.base import BaseCommand
from apps.ads.models import Partner, AdUnit, AdSlot
from apps.ads.services import AdService


class Command(BaseCommand):
    help = 'Управление рекламными объявлениями'

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='action', help='Действие')
        
        # Список объявлений
        list_parser = subparsers.add_parser('list', help='Список объявлений')
        list_parser.add_argument('--active', action='store_true', help='Только активные')
        list_parser.add_argument('--partner', type=str, help='Фильтр по партнёру')
        
        # Статистика
        subparsers.add_parser('stats', help='Статистика')
        
        # Деактивация просроченных
        subparsers.add_parser('cleanup', help='Деактивировать просроченные')
        
        # Демо-данные Trip.com
        subparsers.add_parser('demo', help='Создать демо-данные Trip.com')
        
        # Создание слота
        slot_parser = subparsers.add_parser('create_slot', help='Создать слот')
        slot_parser.add_argument('slug', type=str, help='URL-слаг')
        slot_parser.add_argument('name', type=str, help='Название')
        slot_parser.add_argument('slot_type', type=str, help='Тип слота')
        
        # Создание объявления
        ad_parser = subparsers.add_parser('create_ad', help='Создать объявление')
        ad_parser.add_argument('partner_slug', type=str, help='Слаг партнёра')
        ad_parser.add_argument('name', type=str, help='Название')
        ad_parser.add_argument('ad_type', type=str, help='Тип (widget/banner/text)')
        ad_parser.add_argument('slot_type', type=str, help='Тип слота')
        ad_parser.add_argument('--widget-code', type=str, help='Код виджета')
        ad_parser.add_argument('--link', type=str, help='Ссылка')
        ad_parser.add_argument('--text', type=str, help='Текст ссылки')
        ad_parser.add_argument('--priority', type=int, default=5, help='Приоритет')
        ad_parser.add_argument('--intro', type=str, help='Подводка')

    def handle(self, *args, **options):
        action = options.get('action')
        
        if action == 'list':
            self.handle_list(options)
        elif action == 'stats':
            self.handle_stats()
        elif action == 'cleanup':
            self.handle_cleanup()
        elif action == 'create_slot':
            self.handle_create_slot(options)
        elif action == 'create_ad':
            self.handle_create_ad(options)
        elif action == 'demo':
            self.handle_demo()
        else:
            self.stdout.write(self.style.ERROR('Неизвестное действие'))
            self.stdout.write(self.style.INFO('Доступные действия: list, stats, cleanup, create_slot, create_ad'))

    def handle_list(self, options):
        queryset = AdUnit.objects.all().select_related('partner')
        
        if options.get('active'):
            queryset = queryset.filter(is_active=True)
        
        partner_slug = options.get('partner')
        if partner_slug:
            queryset = queryset.filter(partner__slug=partner_slug)
        
        self.stdout.write(self.style.SUCCESS(f'\nВсего объявлений: {queryset.count()}\n'))
        
        for ad in queryset:
            status = '✓' if ad.is_active else '✗'
            self.stdout.write(
                f'{status} [{ad.ad_type}] {ad.name} '
                f'(партнёр: {ad.partner.name}, '
                f'приоритет: {ad.priority}, '
                f'показы: {ad.impressions_count}, '
                f'клики: {ad.clicks_count})'
            )

    def handle_stats(self):
        stats = AdService.get_stats()
        
        self.stdout.write(self.style.SUCCESS('\n=== Статистика рекламы ===\n'))
        self.stdout.write(f"Всего объявлений: {stats['total_ads']}")
        self.stdout.write(f"Активных: {stats['active_ads']}")
        self.stdout.write(f"Всего показов: {stats['total_impressions']:,}")
        self.stdout.write(f"Всего кликов: {stats['total_clicks']:,}")
        
        if stats['total_impressions'] > 0:
            ctr = (stats['total_clicks'] / stats['total_impressions']) * 100
            self.stdout.write(f"CTR: {ctr:.2f}%")
        
        self.stdout.write(self.style.SUCCESS('\nПо партнёрам:'))
        for partner, data in stats['by_partner'].items():
            self.stdout.write(f"  {partner}: {data['count']} объявлений, {data['impressions']} показов, {data['clicks']} кликов")

    def handle_cleanup(self):
        deactivated = AdService.deactivate_expired()
        if deactivated:
            self.stdout.write(self.style.SUCCESS(f'Деактивировано объявлений: {deactivated}'))
        else:
            self.stdout.write('Нет просроченных объявлений')

    def handle_create_slot(self, options):
        try:
            slot = AdSlot.objects.create(
                slug=options['slug'],
                name=options['name'],
                slot_type=options['slot_type']
            )
            self.stdout.write(self.style.SUCCESS(f'Слот создан: {slot}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка: {e}'))

    def handle_create_ad(self, options):
        try:
            partner = Partner.objects.get(slug=options['partner_slug'])
            
            ad = AdUnit.objects.create(
                partner=partner,
                name=options['name'],
                ad_type=options['ad_type'],
                slot_type=options['slot_type'],
                priority=options.get('priority', 5),
                widget_code=options.get('widget_code', ''),
                link=options.get('link', ''),
                text=options.get('text', ''),
                intro_text=options.get('intro', ''),
            )
            self.stdout.write(self.style.SUCCESS(f'Объявление создано: {ad}'))
        except Partner.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Партнёр не найден: {options["partner_slug"]}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка: {e}'))

    def handle_demo(self):
        self.stdout.write(self.style.SUCCESS('\n=== Создание демо-данных Trip.com ===\n'))
        
        partner, created = Partner.objects.get_or_create(
            slug='trip-com',
            defaults={
                'name': 'Trip.com',
                'url': 'https://www.trip.com',
            }
        )
        if created:
            self.stdout.write(f'Партнёр создан: {partner}')
        else:
            self.stdout.write(f'Партнёр найден: {partner}')
        
        # Создаём позиции для статей
        article_positions = [
            ('article-before_h2', 'Перед H2', 'article', 'before_h2'),
            ('article-middle', 'Середина статьи', 'article', 'middle'),
            ('article-before_faq', 'Перед FAQ', 'article', 'before_faq'),
            ('article-end', 'Конец статьи', 'article', 'end'),
        ]
        
        # Создаём позиции для новостей
        news_positions = [
            ('news-top', 'Верх новости', 'news', 'top'),
            ('news-middle', 'Середина новости', 'news', 'middle'),
            ('news-bottom', 'Низ новости', 'news', 'bottom'),
        ]
        
        # Создаём позиции для продуктов
        product_positions = [
            ('product-top', 'Верх продукта', 'product', 'top'),
            ('product-bottom', 'Низ продукта', 'product', 'bottom'),
        ]
        
        all_positions = article_positions + news_positions + product_positions
        
        for slug, name, page_type, position in all_positions:
            slot, created = AdSlot.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': name,
                    'page_type': page_type,
                    'position': position,
                }
            )
            if created:
                self.stdout.write(f'Позиция создана: {slot}')
            else:
                self.stdout.write(f'Позиция найдена: {slot}')
        
        # Создаём объявления для разных позиций
        trip_widget_code = '<iframe border="0" src="https://ru.trip.com/partners/ad/S2654290?Allianceid=6229959&SID=192412375&trip_sub1=" style="width:320px;height:480px" frameborder="0" scrolling="no" style="border:none" id="S2654290"></iframe>'
        trip_banner_code = '<iframe border="0" src="https://ru.trip.com/partners/ad/S2654290?Allianceid=6229959&SID=192412375&trip_sub1=" style="width:300px;height:250px" frameborder="0" scrolling="no" style="border:none" id="S2654290"></iframe>'
        
        # Находим позицию для статей
        article_middle_slot = AdSlot.objects.get(slug='article-middle')
        
        ads_data = [
            ('Trip.com Widget 320x480', 'widget', article_middle_slot, 8, trip_widget_code, 'Проверено читателями:'),
        ]
        
        for name, ad_type, slot, priority, code, intro in ads_data:
            ad, created = AdUnit.objects.get_or_create(
                partner=partner,
                name=name,
                defaults={
                    'ad_type': ad_type,
                    'slot': slot,
                    'priority': priority,
                    'widget_code': code,
                    'intro_text': intro,
                }
            )
            if created:
                self.stdout.write(f'Объявление создано: {ad}')
            else:
                self.stdout.write(f'Объявление найдено: {ad}')
        
        self.stdout.write(self.style.SUCCESS('\nДемо-данные готовы!'))
        self.stdout.write('Позиции: article-middle, article-end и т.д.')
        self.stdout.write('Используйте {% ad_slot "article-middle" article %} в шаблоне.')
