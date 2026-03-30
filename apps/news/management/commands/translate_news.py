"""
Management command: translate_news
Переводит черновики новостей с иностранных языков на русский.

Приоритет переводчиков:
  1. DeepL Free API  (500k символов/месяц)
  2. Gemini 2.0 Flash (fallback — бесплатный tier Google AI)

Использование:
    python manage.py translate_news            # все непереведённые черновики
    python manage.py translate_news --id 5     # только конкретная запись
    python manage.py translate_news --limit 20 # не более 20 записей за раз
    python manage.py translate_news --dry-run  # только показать, без изменений
"""
import os
import re
import httpx
from django.core.management.base import BaseCommand
from apps.news.models import NewsItem
from apps.news.management.commands.fetch_news import _make_unique_slug

DEEPL_KEY = os.environ.get('DEEPL_API_KEY', '')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY', '')

DEEPL_URL = 'https://api-free.deepl.com/v2/translate'
GEMINI_URL = (
    'https://generativelanguage.googleapis.com/v1beta/models/'
    '{model}:generateContent?key={key}'
)
# Models tried in order until one responds with 200
GEMINI_MODELS = [
    'gemini-2.0-flash',
    'gemini-2.5-flash',
    'gemini-flash-lite-latest',
    'gemini-flash-latest',
]


# ── DeepL ─────────────────────────────────────────────────────────────────────

def _deepl_translate(text: str, target_lang: str = 'RU') -> str | None:
    """Переводит текст через DeepL Free API. Возвращает None при ошибке/лимите."""
    if not DEEPL_KEY or not text.strip():
        return None
    try:
        r = httpx.post(
            DEEPL_URL,
            headers={'Authorization': f'DeepL-Auth-Key {DEEPL_KEY}'},
            data={'text': text, 'target_lang': target_lang},
            timeout=20,
        )
        if r.status_code in (403, 456):  # invalid key or quota exceeded
            return None
        r.raise_for_status()
        return r.json()['translations'][0]['text']
    except Exception:
        return None


# ── Gemini ────────────────────────────────────────────────────────────────────

_GEMINI_PROMPT = (
    'Переведи следующий {format} с {src_lang} на русский язык. '
    'Сохрани HTML-теги без изменений. Верни только переведённый текст, без пояснений.\n\n{text}'
)


def _gemini_translate(text: str, src_lang: str = 'английского') -> tuple[str, str] | tuple[None, None]:
    """Переводит текст через Gemini. Пробует модели по порядку. Возвращает (текст, модель) или (None, None)."""
    if not GEMINI_KEY or not text.strip():
        return None, None
    fmt = 'HTML' if re.search(r'<[a-z]', text, re.I) else 'текст'
    prompt = _GEMINI_PROMPT.format(format=fmt, src_lang=src_lang, text=text[:20000])
    payload = {'contents': [{'parts': [{'text': prompt}]}]}
    for model in GEMINI_MODELS:
        try:
            r = httpx.post(
                GEMINI_URL.format(model=model, key=GEMINI_KEY),
                json=payload,
                timeout=60,
            )
            if r.status_code == 429:
                continue  # try next model
            r.raise_for_status()
            result = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            return result, model
        except Exception:
            continue
    return None, None


def _translate(text: str, src_lang: str) -> tuple[str, str]:
    """
    Переводит текст, возвращает (переведённый текст, модель).
    Пробует DeepL → Gemini.
    """
    if not text.strip():
        return text, ''

    # DeepL first
    result = _deepl_translate(text)
    if result:
        return result, 'deepl-free'

    # Gemini fallback
    lang_name = {
        'en': 'английского', 'vi': 'вьетнамского',
        'zh': 'китайского', 'ko': 'корейского',
        'ja': 'японского', 'fr': 'французского',
        'de': 'немецкого',
    }.get(src_lang[:2].lower(), 'иностранного')
    result, model = _gemini_translate(text, lang_name)
    if result:
        return result, model

    return text, ''  # перевод не удался — оставляем оригинал


# ── Command ───────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Переводит черновики новостей на русский язык (DeepL → Gemini).'

    def add_arguments(self, parser):
        parser.add_argument('--id', type=int, help='ID конкретной записи')
        parser.add_argument('--limit', type=int, default=50,
                            help='Максимум записей за один запуск (default: 50)')
        parser.add_argument('--dry-run', action='store_true',
                            help='Только показать, без сохранения')
        parser.add_argument('--force', action='store_true',
                            help='Переводить даже уже ai_processed=True')

    def handle(self, *args, **options):
        qs = NewsItem.objects.filter(status=NewsItem.DRAFT)
        if options['id']:
            qs = qs.filter(pk=options['id'])
        elif not options['force']:
            qs = qs.filter(ai_processed=False).exclude(
                source__source_language='ru'
            ).filter(source__needs_translation=True)

        qs = qs.select_related('source')[:options['limit']]
        total = len(qs)
        self.stdout.write(f'Записей для перевода: {total}')

        ok = 0
        for item in qs:
            src_lang = item.source.source_language if item.source else 'en'
            self.stdout.write(f'  [{item.pk}] {item.title[:70]}')

            # Не перезаписываем контент, отредактированный вручную
            if item.is_edited and not options['force']:
                self.stdout.write('    ⏭ пропуск (is_edited=True, используйте --force)')
                continue

            if options['dry_run']:
                self.stdout.write('    [dry-run] пропуск')
                continue

            model_used = ''

            # Переводим заголовок
            t_title, model_used = _translate(item.title, src_lang)

            # Переводим summary
            t_summary, _ = _translate(item.summary, src_lang)

            # Переводим body_md (Markdown — чище для перевода)
            t_body_md = item.body_md
            if item.body_md:
                translated, m = _translate(item.body_md, src_lang)
                if m:
                    t_body_md = translated
                    model_used = m
            elif item.body:
                # Fallback: если body_md пустой — переводим body (HTML)
                translated, m = _translate(item.body, src_lang)
                if m:
                    t_body_md = translated
                    model_used = m

            if not model_used:
                self.stdout.write('    ⚠ перевод не удался — пропуск')
                continue

            # Сохраняем оригиналы, записываем переводы
            item.title_original = item.title_original or item.title
            item.summary_original = item.summary_original or item.summary
            item.title = t_title
            item.summary = t_summary
            item.body_md = t_body_md  # save() автоматически рендерит → body
            item.ai_processed = True
            item.ai_model_used = model_used
            # Обновляем slug под новый заголовок
            new_slug = _make_unique_slug(t_title)
            item.slug = new_slug
            item.save()
            ok += 1
            self.stdout.write(f'    ✓ [{model_used}] {t_title[:70]}')

        self.stdout.write(self.style.SUCCESS(f'\nПереведено: {ok}/{total}'))
