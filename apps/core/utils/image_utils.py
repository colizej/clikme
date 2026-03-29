"""
Утилита для оптимизации изображений:
- Конвертация в WebP
- Сжатие
- Изменение размера при необходимости
"""

import os
from pathlib import Path
from PIL import Image
from django.conf import settings


def convert_to_webp(source_path: str, quality: int = 85, max_width: int = 1920) -> str:
    """
    Конвертирует изображение в WebP формат.
    
    Args:
        source_path: Путь к исходному файлу (относительный, напр. 'catalog/image.jpg')
        quality: Качество WebP (1-100)
        max_width: Максимальная ширина (изображения шире будут уменьшены)
    
    Returns:
        Путь к новому файлу (с .webp расширением)
    """
    media_root = settings.MEDIA_ROOT
    source_full = media_root / source_path
    
    if not source_full.exists():
        return source_path
    
    # Генерируем новый путь с .webp
    source_stem = Path(source_path).stem
    source_dir = Path(source_path).parent
    webp_path = source_dir / f"{source_stem}.webp"
    webp_full = media_root / webp_path
    
    # Открываем изображение
    with Image.open(source_full) as img:
        # Конвертируем RGBA в RGB если нужно (WebP не поддерживает альфа-канал в некоторых режимах)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Создаём белый фон для прозрачных изображений
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Уменьшаем если слишком большое
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
        # Сохраняем в WebP
        img.save(webp_full, 'WEBP', quality=quality, method=6)
    
    return str(webp_path)


def process_image_field(image_field) -> str:
    """
    Обрабатывает Django ImageField: конвертирует в WebP и возвращает новый путь.
    
    Args:
        image_field: Django ImageFieldFile
    
    Returns:
        Новый путь к файлу (WebP) или исходный путь если ошибка
    """
    if not image_field or not image_field.name:
        return None
    
    try:
        new_path = convert_to_webp(image_field.name)
        
        # Удаляем старый файл если он отличается
        if new_path != image_field.name:
            old_path = settings.MEDIA_ROOT / image_field.name
            if old_path.exists():
                old_path.unlink()
            
            # Обновляем поле
            image_field.name = new_path
        
        return new_path
    except Exception as e:
        print(f"Error processing image {image_field.name}: {e}")
        return image_field.name


def get_image_size(path: str) -> tuple:
    """Возвращает размеры изображения (width, height)"""
    try:
        full_path = settings.MEDIA_ROOT / path
        with Image.open(full_path) as img:
            return img.size
    except:
        return (0, 0)
