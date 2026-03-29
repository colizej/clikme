from django.db import models
from apps.core.utils.image_utils import process_image_field


class Vendor(models.Model):
    oc_id = models.IntegerField(null=True, blank=True, db_index=True)
    slug = models.SlugField(unique=True, max_length=255, db_index=True)

    display_name = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    description_md = models.TextField(
        blank=True,
        verbose_name='Описание (Markdown)',
        help_text='Редактируйте здесь. HTML в поле «description» генерируется автоматически при сохранении.',
    )
    meta_description = models.CharField(max_length=500, blank=True)
    meta_keywords = models.CharField(max_length=500, blank=True)

    telephone = models.CharField(max_length=30, blank=True)
    image = models.ImageField(upload_to='catalog/vendor/', blank=True)
    city = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    map_url = models.URLField(blank=True, max_length=600)
    telegram_url = models.URLField(blank=True)

    is_active = models.BooleanField(default=True)
    approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Вендор'
        verbose_name_plural = 'Вендоры'
        ordering = ['display_name']

    def __str__(self):
        return self.display_name

    def save(self, *args, **kwargs):
        if self.description_md:
            import markdown
            self.description = markdown.markdown(
                self.description_md,
                extensions=['extra', 'nl2br'],
            )
        super().save(*args, **kwargs)
        if self.image and self.image.name and not self.image.name.endswith('.webp'):
            process_image_field(self.image)
            Vendor.objects.filter(pk=self.pk).update(image=self.image.name)

    def get_absolute_url(self):
        return f'/{self.slug}/'


class Product(models.Model):
    oc_id = models.IntegerField(null=True, blank=True, db_index=True)
    slug = models.SlugField(unique=True, max_length=255, db_index=True)
    vendor = models.ForeignKey(
        Vendor, on_delete=models.CASCADE, related_name='products', null=True
    )

    name = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='catalog/product/', blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    meta_description = models.CharField(max_length=500, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.image and self.image.name and not self.image.name.endswith('.webp'):
            process_image_field(self.image)
            Product.objects.filter(pk=self.pk).update(image=self.image.name)

    def get_absolute_url(self):
        return f'/{self.slug}/'
