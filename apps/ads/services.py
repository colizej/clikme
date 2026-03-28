import random
from django.db.models import F, Q
from django.utils import timezone
from .models import AdUnit, AdSlot


class AdService:
    """Сервис для работы с рекламными объявлениями"""
    
    @staticmethod
    def get_ad_for_slot(slot: AdSlot, article=None) -> AdUnit | None:
        """
        Получить объявление для слота.
        
        Алгоритм:
        1. Найти все активные объявления для слота
        2. Фильтр по датам (если временные)
        3. Фильтр по категориям статьи
        4. Фильтр по лимитам показов
        5. Выбрать по приоритету + случайность
        """
        if not slot or not slot.is_active:
            return None
        
        now = timezone.now()
        
        # Базовый queryset
        queryset = AdUnit.objects.filter(
            slot_type=slot.slot_type,
            is_active=True
        ).select_related('partner')
        
        # Фильтр по датам
        queryset = queryset.filter(
            Q(is_permanent=True) |
            Q(start_date__isnull=True, end_date__isnull=True) |
            Q(start_date__lte=now, end_date__gte=now)
        )
        
        # Фильтр по лимитам показов
        queryset = queryset.filter(
            Q(max_impressions__isnull=True) |
            Q(impressions_count__lt=F('max_impressions'))
        )
        
        # Фильтр по категориям статьи
        if article and article.category:
            # Сначала получаем все объявления
            all_ads = list(queryset)
            
            # Фильтруем в Python для ManyToMany
            filtered_ads = []
            for ad in all_ads:
                cats = list(ad.target_categories.all())
                # Показываем если:
                # - нет таргетинга (пустой ManyToMany)
                # - или совпадает с категорией статьи
                if not cats or article.category in cats:
                    filtered_ads.append(ad)
            
            queryset = AdUnit.objects.filter(pk__in=[ad.pk for ad in filtered_ads])
        else:
            # Если категория неизвестна — показываем только без таргетинга
            queryset = queryset.filter(target_categories__isnull=True)
        
        # Получаем уникальные объявления
        queryset = queryset.distinct()
        
        # Ротация: берём топ-3 по приоритету, случайный из них
        top_units = list(queryset.order_by('-priority')[:3])
        
        if top_units:
            chosen = random.choice(top_units)
            return chosen
        
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
