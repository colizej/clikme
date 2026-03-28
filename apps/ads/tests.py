from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .models import Partner, AdSlot, AdUnit, AdClick, ArticleAdPlacement
from .services import AdService
from apps.blog.models import Category, Article


class PartnerModelTest(TestCase):
    """Тесты модели Partner"""
    
    def test_create_partner(self):
        partner = Partner.objects.create(
            name="Trip.com",
            slug="trip-com",
            url="https://www.trip.com"
        )
        self.assertEqual(partner.name, "Trip.com")
        self.assertEqual(str(partner), "Trip.com")
        self.assertTrue(partner.is_active)


class AdSlotModelTest(TestCase):
    """Тесты модели AdSlot"""
    
    def test_create_slot(self):
        slot = AdSlot.objects.create(
            slug="article_middle",
            name="Середина статьи",
            slot_type="widget_320x480"
        )
        self.assertEqual(slot.slug, "article_middle")
        self.assertEqual(str(slot), "Середина статьи (widget_320x480)")


class AdUnitModelTest(TestCase):
    """Тесты модели AdUnit"""
    
    def setUp(self):
        self.partner = Partner.objects.create(
            name="Trip.com",
            slug="trip-com",
            url="https://www.trip.com"
        )
    
    def test_create_widget_ad(self):
        ad = AdUnit.objects.create(
            partner=self.partner,
            name="Trip.com Widget",
            ad_type="widget",
            slot_type="widget_320x480",
            widget_code='<iframe src="https://trip.com"></iframe>'
        )
        self.assertEqual(ad.ad_type, "widget")
        self.assertTrue(ad.is_visible())
        self.assertEqual(str(ad), "Trip.com — Trip.com Widget")
    
    def test_is_visible_permanent_active(self):
        """Постоянный активный — виден"""
        ad = AdUnit.objects.create(
            partner=self.partner,
            name="Active Ad",
            ad_type="widget",
            slot_type="widget_320x480",
            is_permanent=True,
            is_active=True
        )
        self.assertTrue(ad.is_visible())
    
    def test_is_visible_inactive(self):
        """Неактивный — не виден"""
        ad = AdUnit.objects.create(
            partner=self.partner,
            name="Inactive Ad",
            ad_type="widget",
            slot_type="widget_320x480",
            is_active=False
        )
        self.assertFalse(ad.is_visible())
    
    def test_is_visible_expired(self):
        """Истёк срок — не виден"""
        ad = AdUnit.objects.create(
            partner=self.partner,
            name="Expired Ad",
            ad_type="widget",
            slot_type="widget_320x480",
            is_permanent=False,
            start_date=timezone.now() - timedelta(days=10),
            end_date=timezone.now() - timedelta(days=1)
        )
        self.assertFalse(ad.is_visible())
    
    def test_is_visible_max_impressions(self):
        """Достигнут лимит показов — не виден"""
        ad = AdUnit.objects.create(
            partner=self.partner,
            name="Limited Ad",
            ad_type="widget",
            slot_type="widget_320x480",
            max_impressions=100,
            impressions_count=100
        )
        self.assertFalse(ad.is_visible())


class AdClickViewTest(TestCase):
    """Тесты представления клика"""
    
    def setUp(self):
        self.client = Client()
        self.partner = Partner.objects.create(
            name="Trip.com",
            slug="trip-com",
            url="https://www.trip.com"
        )
        self.ad = AdUnit.objects.create(
            partner=self.partner,
            name="Trip.com Widget",
            ad_type="widget",
            slot_type="widget_320x480",
            link="https://www.trip.com/hotels"
        )
    
    def test_click_redirects(self):
        """Клик редиректит на партнёра"""
        response = self.client.get(
            reverse('ads:click', args=[self.ad.id])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('trip.com', response.url)
    
    def test_click_creates_log(self):
        """Клик создаёт запись в логах"""
        initial_count = AdClick.objects.count()
        self.client.get(reverse('ads:click', args=[self.ad.id]))
        self.assertEqual(AdClick.objects.count(), initial_count + 1)
        
        click = AdClick.objects.latest('id')
        self.assertEqual(click.ad_unit, self.ad)
    
    def test_click_increments_counter(self):
        """Клик увеличивает счётчик"""
        initial_clicks = self.ad.clicks_count
        self.client.get(reverse('ads:click', args=[self.ad.id]))
        self.ad.refresh_from_db()
        self.assertEqual(self.ad.clicks_count, initial_clicks + 1)
    
    def test_click_with_article_id(self):
        """Клик с параметром статьи (slug, FK = null)"""
        # article_id принимается как slug, но FK ожидает integer
        # Поэтому article_id будет null если статья не существует
        self.client.get(
            reverse('ads:click', args=[self.ad.id]),
            {'article': 'test-article'}
        )
        click = AdClick.objects.latest('id')
        # Статья не найдена, поэтому article_id = None
        self.assertIsNone(click.article_id)
    
    def test_click_nonexistent_ad(self):
        """Клик по несуществующему объявлению"""
        response = self.client.get(
            reverse('ads:click', args=[99999])
        )
        self.assertEqual(response.status_code, 404)


class AdPixelViewTest(TestCase):
    """Тесты пикселя отслеживания"""
    
    def setUp(self):
        self.client = Client()
        self.partner = Partner.objects.create(
            name="Trip.com",
            slug="trip-com",
            url="https://www.trip.com"
        )
        self.ad = AdUnit.objects.create(
            partner=self.partner,
            name="Trip.com Widget",
            ad_type="widget",
            slot_type="widget_320x480"
        )
    
    def test_pixel_returns_gif(self):
        """Пиксель возвращает GIF"""
        response = self.client.get(
            reverse('ads:pixel', args=[self.ad.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/gif')


class AdServiceTest(TestCase):
    """Тесты сервиса AdService"""
    
    def setUp(self):
        self.partner = Partner.objects.create(
            name="Trip.com",
            slug="trip-com",
            url="https://www.trip.com"
        )
        self.slot = AdSlot.objects.create(
            slug="article_middle",
            name="Середина статьи",
            slot_type="widget_320x480"
        )
    
    def test_get_ad_for_slot_returns_ad(self):
        """Возвращает объявление если есть"""
        ad = AdUnit.objects.create(
            partner=self.partner,
            name="Test Ad",
            ad_type="widget",
            slot_type="widget_320x480",
            is_active=True
        )
        
        result = AdService.get_ad_for_slot(self.slot)
        self.assertEqual(result, ad)
    
    def test_get_ad_for_slot_returns_none_when_no_ads(self):
        """Возвращает None если нет объявлений"""
        result = AdService.get_ad_for_slot(self.slot)
        self.assertIsNone(result)
    
    def test_get_ad_for_slot_inactive_slot(self):
        """Возвращает None для неактивного слота"""
        self.slot.is_active = False
        self.slot.save()
        
        ad = AdUnit.objects.create(
            partner=self.partner,
            name="Test Ad",
            ad_type="widget",
            slot_type="widget_320x480"
        )
        
        result = AdService.get_ad_for_slot(self.slot)
        self.assertIsNone(result)
    
    def test_rotation_picks_from_top_priority(self):
        """Ротация выбирает из топ-3 по приоритету"""
        # Создаём 5 объявлений с разными приоритетами
        for i in range(5):
            AdUnit.objects.create(
                partner=self.partner,
                name=f"Ad {i}",
                ad_type="widget",
                slot_type="widget_320x480",
                priority=10 - i  # 10, 9, 8, 7, 6
            )
        
        # Вызываем много раз и проверяем что все из топ-3
        selected_priorities = set()
        for _ in range(20):
            ad = AdService.get_ad_for_slot(self.slot)
            if ad:
                selected_priorities.add(ad.priority)
        
        # Должны быть только приоритеты 10, 9, 8
        self.assertTrue(selected_priorities.issubset({10, 9, 8}))
    
    def test_increment_impression(self):
        """Увеличивает счётчик показов"""
        ad = AdUnit.objects.create(
            partner=self.partner,
            name="Test Ad",
            ad_type="widget",
            slot_type="widget_320x480",
            impressions_count=10
        )
        
        AdService.increment_impression(ad)
        
        ad.refresh_from_db()
        self.assertEqual(ad.impressions_count, 11)
    
    def test_deactivate_expired(self):
        """Деактивирует просроченные объявления"""
        ad = AdUnit.objects.create(
            partner=self.partner,
            name="Expired Ad",
            ad_type="widget",
            slot_type="widget_320x480",
            is_permanent=False,
            end_date=timezone.now() - timedelta(days=1),
            is_active=True
        )
        
        deactivated = AdService.deactivate_expired()
        self.assertEqual(deactivated, 1)
        
        ad.refresh_from_db()
        self.assertFalse(ad.is_active)
    
    def test_get_stats(self):
        """Возвращает статистику"""
        AdUnit.objects.create(
            partner=self.partner,
            name="Test Ad 1",
            ad_type="widget",
            slot_type="widget_320x480",
            impressions_count=100,
            clicks_count=5
        )
        AdUnit.objects.create(
            partner=self.partner,
            name="Test Ad 2",
            ad_type="banner",
            slot_type="banner_728x90",
            impressions_count=200,
            clicks_count=10
        )
        
        stats = AdService.get_stats()
        
        self.assertEqual(stats['total_ads'], 2)
        self.assertEqual(stats['total_impressions'], 300)
        self.assertEqual(stats['total_clicks'], 15)


class ArticleAdPlacementModelTest(TestCase):
    """Тесты модели ArticleAdPlacement"""
    
    def setUp(self):
        self.partner = Partner.objects.create(
            name="Test Partner",
            slug="test-partner",
            url="https://example.com"
        )
        self.slot = AdSlot.objects.create(
            slug="article_middle",
            name="Середина статьи",
            slot_type="widget_320x480"
        )
        self.ad = AdUnit.objects.create(
            partner=self.partner,
            name="Test Ad",
            ad_type="widget",
            slot_type="widget_320x480"
        )
        self.category = Category.objects.create(
            name="Test Category",
            slug="test-category"
        )
        self.article = Article.objects.create(
            title="Test Article",
            slug="test-article",
            content="Test content",
            category=self.category
        )
    
    def test_create_placement(self):
        """Создание размещения"""
        placement = ArticleAdPlacement.objects.create(
            article=self.article,
            slot=self.slot,
            ad_unit=self.ad,
            position="before_h2"
        )
        self.assertEqual(str(placement), f"{self.article} — {self.slot.name} (before_h2)")
        self.assertTrue(placement.is_active)
    
    def test_placement_without_ad_unit(self):
        """Размещение без конкретного объявления (автовыбор)"""
        placement = ArticleAdPlacement.objects.create(
            article=self.article,
            slot=self.slot,
            position="end"
        )
        self.assertIsNone(placement.ad_unit)
    
    def test_unique_constraint(self):
        """Уникальность article + slot + position"""
        ArticleAdPlacement.objects.create(
            article=self.article,
            slot=self.slot,
            position="before_h2"
        )
        with self.assertRaises(Exception):
            ArticleAdPlacement.objects.create(
                article=self.article,
                slot=self.slot,
                position="before_h2"
            )


class AdShortcodeTest(TestCase):
    """Тесты парсинга шорткодов"""
    
    def setUp(self):
        self.partner = Partner.objects.create(
            name="Test Partner",
            slug="test-partner",
            url="https://example.com"
        )
        self.slot = AdSlot.objects.create(
            slug="mid_slot",
            name="Середина",
            slot_type="banner_300x250",
            fallback_text="<div class='ad-placeholder'>Реклама</div>"
        )
        AdSlot.objects.create(
            slug="inactive_slot",
            name="Неактивный",
            slot_type="banner_300x250",
            is_active=False
        )
    
    def test_parse_single_shortcode(self):
        """Парсит один шорткод"""
        from .templatetags.ads_tags import parse_ad_shortcodes
        
        text = "Some text [ad:mid_slot] more text"
        result = parse_ad_shortcodes(text)
        
        self.assertNotIn('[ad:mid_slot]', result)
        self.assertIn('Some text', result)
    
    def test_parse_multiple_shortcodes(self):
        """Парсит несколько шорткодов"""
        from .templatetags.ads_tags import parse_ad_shortcodes
        
        text = "[ad:mid_slot] middle [ad:mid_slot] end"
        result = parse_ad_shortcodes(text)
        
        self.assertNotIn('[ad:', result)
        self.assertEqual(result.count('Some text'), 0)
    
    def test_inactive_slot_returns_empty(self):
        """Неактивный слот возвращает пустую строку"""
        from .templatetags.ads_tags import parse_ad_shortcodes
        
        text = "[ad:inactive_slot] test"
        result = parse_ad_shortcodes(text)
        
        self.assertEqual(result, ' test')
    
    def test_nonexistent_slot_returns_empty(self):
        """Несуществующий слот возвращает пустую строку"""
        from .templatetags.ads_tags import parse_ad_shortcodes
        
        text = "Text [ad:nonexistent] more"
        result = parse_ad_shortcodes(text)
        
        self.assertEqual(result, 'Text  more')
    
    def test_empty_text_returns_empty(self):
        """Пустой текст возвращается как есть"""
        from .templatetags.ads_tags import parse_ad_shortcodes
        
        self.assertEqual(parse_ad_shortcodes(''), '')
        self.assertIsNone(parse_ad_shortcodes(None))
