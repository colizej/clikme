import random
from django.db.models import F, Q
from django.utils import timezone
from .models import AdUnit, AdSlot


class AdService:
    """Сервис для работы с рекламными объявлениями"""
    
    @staticmethod
    def get_ad_for_slot(slot: AdSlot, article=None) -> AdUnit | None:
        """
        Получить объявление для позиции.
        
        Алгоритм:
        1. Найти все активные объявления для данной позиции (slot)
        2. Если есть конкретная статья — сначала проверить ad_targeted к ней
        3. Если есть конкретная новость — проверить ad_targeted к ней
        4. Если нет конкретного таргетинга — показать объявления без таргетинга
        5. Выбрать по приоритету + случайность
        """
        if not slot or not slot.is_active:
            return None
        
        now = timezone.now()
        
        base_queryset = AdUnit.objects.filter(
            slot=slot,
            is_active=True
        ).select_related('partner')
        
        base_queryset = base_queryset.filter(
            Q(is_permanent=True) |
            Q(start_date__isnull=True, end_date__isnull=True) |
            Q(start_date__lte=now, end_date__gte=now)
        )
        
        base_queryset = base_queryset.filter(
            Q(max_impressions__isnull=True) |
            Q(impressions_count__lt=F('max_impressions'))
        )
        
        queryset = base_queryset.distinct()
        
        if article:
            queryset = AdService._filter_by_article(queryset, article)
        else:
            queryset = queryset.filter(target_article__isnull=True)
        
        queryset = queryset.order_by('-priority')
        top_units = list(queryset[:3])
        
        if top_units:
            return random.choice(top_units)
        
        return None
    
    @staticmethod
    def _filter_by_article(queryset, article):
        """
        Фильтрация по статье с учётом приоритета:
        Конкретная статья > Все статьи
        """
        all_ads = list(queryset)
        
        specific_ads = [ad for ad in all_ads if ad.target_article_id == article.pk]
        if specific_ads:
            return AdUnit.objects.filter(pk__in=[ad.pk for ad in specific_ads])
        
        generic_ads = [ad for ad in all_ads if ad.target_article_id is None]
        if generic_ads:
            return AdUnit.objects.filter(pk__in=[ad.pk for ad in generic_ads])
        
        return AdUnit.objects.none()
    
    @staticmethod
    def get_ad_by_slug(slot_slug: str, page_type: str = 'article', article=None) -> AdUnit | None:
        """Получить объявление по slug позиции и типу страницы"""
        try:
            slot = AdSlot.objects.get(slug=slot_slug, page_type=page_type, is_active=True)
            return AdService.get_ad_for_slot(slot, article)
        except AdSlot.DoesNotExist:
            return None
    
    @staticmethod
    def increment_impression(ad_unit: AdUnit):
        """Увеличить счётчик показов"""
        AdUnit.objects.filter(pk=ad_unit.pk).update(
            impressions_count=F('impressions_count') + 1
        )
    
    @staticmethod
    def get_active_ads_for_partner(partner_id: int) -> list:
        """Получить все активные объявления партнёра"""
        return list(AdUnit.objects.filter(
            partner_id=partner_id,
            is_active=True
        ).order_by('-priority'))
    
    @staticmethod
    def deactivate_expired():
        """Деактивировать просроченные объявления"""
        now = timezone.now()
        return AdUnit.objects.filter(
            is_permanent=False,
            end_date__lt=now,
            is_active=True
        ).update(is_active=False)
    
    @staticmethod
    def get_stats() -> dict:
        """Получить статистику по объявлениям"""
        from django.db.models import Sum, Count
        
        stats = {
            'total_ads': AdUnit.objects.count(),
            'active_ads': AdUnit.objects.filter(is_active=True).count(),
            'total_impressions': AdUnit.objects.aggregate(
                total=Sum('impressions_count')
            )['total'] or 0,
            'total_clicks': AdUnit.objects.aggregate(
                total=Sum('clicks_count')
            )['total'] or 0,
            'by_type': {},
            'by_partner': {},
        }
        
        # По типам
        type_stats = AdUnit.objects.values('ad_type').annotate(
            count=Count('id'),
            impressions=Sum('impressions_count'),
            clicks=Sum('clicks_count')
        )
        for stat in type_stats:
            stats['by_type'][stat['ad_type']] = stat
        
        # По партнёрам
        partner_stats = AdUnit.objects.values(
            'partner__name'
        ).annotate(
            count=Count('id'),
            impressions=Sum('impressions_count'),
            clicks=Sum('clicks_count')
        )
        for stat in partner_stats:
            stats['by_partner'][stat['partner__name']] = stat
        
        return stats
