from django.db import models
from apps.core.utils.image_utils import process_image_field


class WebPImageMixin(models.Model):
    """
    Mixin для автоматической конвертации изображений в WebP при сохранении.
    Перечислите поля изображений в __sub_image_fields__.
    """
    __sub_image_fields__ = []

    class Meta:
        abstract = True

    def _convert_images_to_webp(self):
        """Конвертирует все ImageField в WebP."""
        from django.conf import settings as django_settings

        for field_name in self.__sub_image_fields__:
            image_field = getattr(self, field_name, None)
            if image_field and image_field.name:
                try:
                    process_image_field(image_field)
                except Exception as e:
                    if django_settings.DEBUG:
                        print(f"[WebP] Error converting {field_name}: {e}")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._convert_images_to_webp()


class SingleImageMixin(WebPImageMixin):
    """Для моделей с одним ImageField — укажите имя поля в image_field_name."""
    image_field_name = 'image'

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        image_field = getattr(self, self.image_field_name, None)
        if image_field and image_field.name:
            try:
                process_image_field(image_field)
            except Exception:
                pass
