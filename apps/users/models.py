from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.core.utils.image_utils import process_image_field


class User(AbstractUser):
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True)
    telegram_id = models.CharField(max_length=50, blank=True)
    points = models.IntegerField(default=0)

    TOURIST = 'tourist'
    EXPAT = 'expat'
    BUSINESS = 'business'
    USER_TYPES = [(TOURIST, 'Турист'), (EXPAT, 'Экспат'), (BUSINESS, 'Бизнес')]
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default=TOURIST)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.avatar and self.avatar.name and not self.avatar.name.endswith('.webp'):
            process_image_field(self.avatar)
