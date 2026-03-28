from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Partner(models.Model):
    """Партнёры (рекламодатели)"""
    
    name = models.CharField("Название", max_length=255)
    slug = models.SlugField("URL-слаг", max_length=100, unique=True)
    url = models.URLField("URL партнёра", max_length=500)
    logo = models.ImageField("Логотип", upload_to='ads/partners/', blank=True)
    is_active = models.BooleanField("Активен", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Партнёр"
        verbose_name_plural = "Партнёры"
        ordering = ['name']

    def __str__(self):
        return self.name


class AdSlot(models.Model):
    """Слоты размещения рекламы"""
    
    SLOT_TYPES = [
        ('widget_320x480', 'Widget 320x480'),
        ('widget_300x600', 'Widget 300x600'),
        ('banner_728x90', 'Banner 728x90'),
        ('banner_300x250', 'Banner 300x250'),
        ('text', 'Текстовая ссылка'),
    ]
    
    slug = models.SlugField("URL-слаг", max_length=100, unique=True)
    name = models.CharField("Название", max_length=255)
    description = models.TextField("Описание", blank=True)
    slot_type = models.CharField("Тип слота", max_length=50, choices=SLOT_TYPES)
    fallback_text = models.TextField("Текст-заглушка", blank=True)
    is_active = models.BooleanField("Активен", default=True)
    order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        verbose_name = "Слот"
        verbose_name_plural = "Слоты"
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.name} ({self.slot_type})"


class AdUnit(models.Model):
    """Рекламные объявления"""
    
    TYPE_WIDGET = 'widget'
    TYPE_BANNER = 'banner'
    TYPE_TEXT = 'text'
    
    TYPE_CHOICES = [
        (TYPE_WIDGET, 'Widget'),
        (TYPE_BANNER, 'Баннер'),
        (TYPE_TEXT, 'Текстовая ссылка'),
    ]
    
    partner = models.ForeignKey(
        Partner,
        on_delete=models.CASCADE,
        related_name='ad_units',
        verbose_name="Партнёр"
    )
    name = models.CharField("Название", max_length=255)
    ad_type = models.CharField("Тип", max_length=20, choices=TYPE_CHOICES)
    
    # Widget fields
    widget_code = models.TextField("Код виджета (iframe/script)", blank=True)
    widget_width = models.PositiveIntegerField("Ширина виджета", null=True, blank=True)
    widget_height = models.PositiveIntegerField("Высота виджета", null=True, blank=True)
    
    # Banner fields
    image = models.ImageField("Изображение", upload_to='ads/banners/', blank=True)
    link = models.URLField("Ссылка", max_length=500, blank=True)
    
    # Text link fields
    text = models.CharField("Текст ссылки", max_length=255, blank=True)
    
    # Common fields
    intro_text = models.CharField("Подводка", max_length=500, blank=True,
        help_text="Текст перед объявлением: 'Лучшие отели Нячанга:'")
    slot_type = models.CharField("Тип слота", max_length=50, choices=AdSlot.SLOT_TYPES,
        help_text="К какому слоту подходит это объявление")
    
    # Period
    is_permanent = models.BooleanField("Постоянный", default=True)
    start_date = models.DateTimeField("Начало показа", null=True, blank=True)
    end_date = models.DateTimeField("Конец показа", null=True, blank=True)
    
    # Targeting
    target_categories = models.ManyToManyField(
        'blog.Category',
        blank=True,
        verbose_name="Категории статей",
        help_text="Показывать только в статьях этих категорий"
    )
    
    priority = models.PositiveIntegerField(
        "Приоритет", default=5,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="1-10. Чем выше, тем чаще показывается"
    )
    
    # Limits
    max_impressions = models.PositiveIntegerField(
        "Макс. показов", null=True, blank=True,
        help_text="Null = без лимита"
    )
    impressions_count = models.PositiveIntegerField("Показов", default=0)
    clicks_count = models.PositiveIntegerField("Кликов", default=0)
    
    is_active = models.BooleanField("Активен", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Рекламное объявление"
        verbose_name_plural = "Рекламные объявления"
        ordering = ['-priority', '-created_at']

    def __str__(self):
        return f"{self.partner.name} — {self.name}"
    
    def is_visible(self):
        """Проверяет, активно ли объявление в текущий момент"""
        if not self.is_active:
            return False
        
        now = timezone.now()
        
        # Проверка лимита показов
        if self.max_impressions and self.impressions_count >= self.max_impressions:
            return False
        
        # Проверка периода
        if not self.is_permanent:
            if self.start_date and now < self.start_date:
                return False
            if self.end_date and now > self.end_date:
                return False
        
        return True


class AdClick(models.Model):
    """Клики по рекламе"""
    
    ad_unit = models.ForeignKey(
        AdUnit,
        on_delete=models.CASCADE,
        related_name='clicks',
        verbose_name="Объявление"
    )
    article = models.ForeignKey(
        'blog.Article',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ad_clicks',
        verbose_name="Статья"
    )
    ip_address = models.GenericIPAddressField("IP", null=True, blank=True)
    user_agent = models.TextField("User Agent", blank=True)
    referer = models.URLField("Referer", max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Клик"
        verbose_name_plural = "Клики"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.ad_unit} — {self.created_at}"
