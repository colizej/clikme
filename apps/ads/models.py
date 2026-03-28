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
    """Позиции размещения рекламы"""
    
    PAGE_TYPES = [
        ('article', 'Статья'),
        ('news', 'Новость'),
        ('product', 'Продукт'),
    ]
    
    slug = models.SlugField("URL-слаг", max_length=100, unique=True)
    name = models.CharField("Название", max_length=255)
    description = models.TextField("Описание", blank=True)
    page_type = models.CharField("Тип страницы", max_length=20, choices=PAGE_TYPES, default='article')
    position = models.CharField(
        "Позиция",
        max_length=50,
        default='middle',
        help_text="before_h2, middle, before_faq, end (для статей) или top, middle, bottom"
    )
    fallback_text = models.TextField("Текст-заглушка", blank=True)
    is_active = models.BooleanField("Активен", default=True)
    order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        verbose_name = "Позиция"
        verbose_name_plural = "Позиции"
        ordering = ['page_type', 'order', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_page_type_display()} — {self.position})"


class AdUnit(models.Model):
    """Рекламные объявления"""
    
    TYPE_WIDGET = 'widget'
    TYPE_BANNER = 'banner'
    TYPE_HTML = 'html'
    TYPE_TEXT = 'text'
    
    TYPE_CHOICES = [
        (TYPE_WIDGET, 'Widget'),
        (TYPE_BANNER, 'Баннер (статичный)'),
        (TYPE_HTML, 'HTML/JS код'),
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
    
    slot = models.ForeignKey(
        AdSlot,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ad_units',
        verbose_name="Позиция"
    )
    
    # Widget fields
    widget_code = models.TextField("Код виджета (iframe/script)", blank=True)
    widget_width = models.PositiveIntegerField("Ширина виджета", null=True, blank=True)
    widget_height = models.PositiveIntegerField("Высота виджета", null=True, blank=True)
    
    # Banner fields
    image = models.ImageField("Изображение", upload_to='ads/banners/', blank=True)
    link = models.URLField("Ссылка", max_length=500, blank=True)
    
    # HTML/JS fields
    html_code = models.TextField("HTML/JS код", blank=True,
        help_text="Код для динамических баннеров (Google Ads, Yandex, и т.д.)")
    
    # Text link fields
    text = models.CharField("Текст ссылки", max_length=255, blank=True)
    
    # Common fields
    intro_text = models.CharField("Подводка", max_length=500, blank=True,
        help_text="Текст перед объявлением: 'Лучшие отели Нячанга:'")
    
    # Specific targeting (null = all pages of that type)
    target_article = models.ForeignKey(
        'blog.Article',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='targeted_ads',
        verbose_name="Конкретная статья"
    )
    target_news = models.ForeignKey(
        'news.NewsItem',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='targeted_ads',
        verbose_name="Конкретная новость"
    )
    
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
        
        if self.max_impressions and self.impressions_count >= self.max_impressions:
            return False
        
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
