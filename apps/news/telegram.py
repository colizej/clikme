"""
Отправка новостей в Telegram канал.

Использование:
    from apps.news.telegram import send_news_item
    ok, err = send_news_item(item)
"""
import os
import logging
import re
import html
import httpx

logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID', '')
SITE_URL = os.environ.get('SITE_URL', 'https://clikme.ru')

TG_API = 'https://api.telegram.org/bot{token}/{method}'

# Максимальная длина caption в Telegram — 1024 символа
_CAPTION_MAX = 1024


def _api(method: str, **kwargs) -> dict:
    """Выполняет POST-запрос к Telegram Bot API (JSON)."""
    url = TG_API.format(token=BOT_TOKEN, method=method)
    try:
        r = httpx.post(url, json=kwargs, timeout=15)
        return r.json()
    except Exception as exc:
        return {'ok': False, 'description': str(exc)}


def _api_upload(method: str, file_bytes: bytes, filename: str, file_field: str, **data) -> dict:
    """Отправляет multipart-запрос с бинарным файлом."""
    url = TG_API.format(token=BOT_TOKEN, method=method)
    try:
        r = httpx.post(
            url,
            data=data,
            files={file_field: (filename, file_bytes)},
            timeout=30,
        )
        return r.json()
    except Exception as exc:
        return {'ok': False, 'description': str(exc)}


def _fetch_image_bytes(item) -> tuple[bytes | None, str]:
    """
    Возвращает (bytes, filename) картинки.
    Сначала пробует локальный файл, затем скачивает по image_url.
    """
    # 1. Локальный файл (надёжнее всего)
    if item.image:
        try:
            with item.image.open('rb') as f:
                data = f.read()
            name = os.path.basename(item.image.name)
            return data, name or 'photo.jpg'
        except Exception as exc:
            logger.warning('Telegram: не удалось прочитать local image: %s', exc)

    # 2. Внешний URL — скачиваем сами
    if item.image_url:
        try:
            r = httpx.get(item.image_url, timeout=15, follow_redirects=True,
                          headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code == 200 and r.content:
                name = os.path.basename(item.image_url.split('?')[0]) or 'photo.jpg'
                return r.content, name
        except Exception as exc:
            logger.warning('Telegram: не удалось скачать image_url: %s', exc)

    return None, ''


def _build_caption(item) -> str:
    """Строит текст поста: заголовок + краткое описание + ссылка."""
    title = html.escape(item.title.strip())
    summary = html.escape((item.summary or '').strip())
    url = SITE_URL.rstrip('/') + item.get_absolute_url()

    parts = [f'<b>{title}</b>']
    if summary:
        # Обрезаем summary чтобы уложиться в лимит
        max_summary = _CAPTION_MAX - len(title) - len(url) - 30
        if len(summary) > max_summary:
            summary = summary[:max_summary].rsplit(' ', 1)[0] + '…'
        parts.append(summary)
    parts.append(f'\U0001F449 <a href="{url}">Читать на сайте</a>')

    return '\n\n'.join(parts)


def send_news_item(item) -> tuple[bool, str]:
    """
    Отправляет новость в канал.
    Возвращает (True, message_id) при успехе или (False, описание_ошибки).
    """
    if not BOT_TOKEN or not CHANNEL_ID:
        return False, 'TELEGRAM_BOT_TOKEN или TELEGRAM_CHANNEL_ID не настроены в .env'

    caption = _build_caption(item)

    # Пробуем отправить с картинкой через бинарный upload
    img_bytes, img_name = _fetch_image_bytes(item)
    if img_bytes:
        result = _api_upload(
            'sendPhoto',
            file_bytes=img_bytes,
            filename=img_name,
            file_field='photo',
            chat_id=CHANNEL_ID,
            caption=caption,
            parse_mode='HTML',
        )
        if result.get('ok'):
            msg_id = str(result['result']['message_id'])
            logger.info('Telegram: sendPhoto OK [%s] message_id=%s', item.pk, msg_id)
            return True, msg_id
        logger.warning('Telegram: sendPhoto failed (%s), falling back to sendMessage', result.get('description'))

    # Без картинки — текстовый пост
    result = _api(
        'sendMessage',
        chat_id=CHANNEL_ID,
        text=caption,
        parse_mode='HTML',
        disable_web_page_preview=False,
    )

    if result.get('ok'):
        msg_id = str(result['result']['message_id'])
        logger.info('Telegram: sendMessage OK [%s] message_id=%s', item.pk, msg_id)
        return True, msg_id
    else:
        err = result.get('description', 'неизвестная ошибка')
        logger.warning('Telegram: ошибка [%s]: %s', item.pk, err)
        return False, err
        err = result.get('description', 'неизвестная ошибка')
        logger.warning('Telegram: ошибка [%s]: %s', item.pk, err)
        return False, err
