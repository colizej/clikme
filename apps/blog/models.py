from django.db import models
from django.utils import timezone
from apps.core.utils.image_utils import process_image_field


class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255, allow_unicode=True)
    description = models.TextField(blank=True)
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(max_length=500, blank=True)
    image = models.ImageField(upload_to='catalog/category/', blank=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'/{self.slug}/'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.image and self.image.name and not self.image.name.endswith('.webp'):
            process_image_field(self.image)


class Tag(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Article(models.Model):
    oc_id = models.IntegerField(null=True, blank=True, db_index=True)
    slug = models.SlugField(unique=True, max_length=255, db_index=True, allow_unicode=True)

    title = models.CharField(max_length=500)
    subtitle = models.CharField(max_length=500, blank=True)
    short_description = models.TextField(blank=True)

    # Markdown-источник (редактируется в админке)
    content_md = models.TextField(
        blank=True,
        verbose_name='Контент (Markdown)',
        help_text='Пишите здесь в Markdown. HTML в поле «content» генерируется автоматически.',
    )
    # Отрендеренный HTML (генерируется из content_md при сохранении)
    content = models.TextField(blank=True)

    image = models.ImageField(upload_to='catalog/', blank=True)
    image_alt = models.CharField(
        max_length=300, blank=True,
        verbose_name='Alt-текст изображения',
        help_text='Описание изображения для поисковиков и screen reader',
    )

    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(max_length=500, blank=True)
    meta_keywords = models.CharField(max_length=500, blank=True)

    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='articles'
    )
    tags = models.ManyToManyField(Tag, blank=True)
    author = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True
    )

    is_published = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    noindex = models.BooleanField(default=False)

    published_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views_count = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Статья'
        verbose_name_plural = 'Статьи'
        ordering = ['-published_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        if self.category:
            return f'/{self.category.slug}/{self.slug}/'
        return f'/{self.slug}/'

    def save(self, *args, **kwargs):
        self.render_content()
        super().save(*args, **kwargs)
        if self.image and self.image.name and not self.image.name.endswith('.webp'):
            process_image_field(self.image)
        if self.pk and hasattr(self, '_parsed_faqs'):
            self.faqs.filter(is_auto=True).delete()
            for i, (q, a) in enumerate(self._parsed_faqs):
                ArticleFAQ.objects.create(
                    article=self, question=q, answer=a,
                    order=i, is_auto=True,
                )

    def render_content(self):
        """Рендерит content_md → content, заменяя [imageN] на HTML и парся FAQ-блоки."""
        import re
        import markdown
        from django.utils.html import escape

        source = self.content_md or ''

        # ── 1. Заменить [imageN] ───────────────────────────────────────────
        image_map = {}
        if self.pk:
            try:
                image_map = {
                    img.number: img
                    for img in self.extra_images.select_related().all()
                }
            except Exception:
                pass

        def _replace(m):
            n = int(m.group(1))
            img_obj = image_map.get(n)
            if not img_obj or not img_obj.image:
                return f'<p class="text-red-500 text-sm">[image{n}: картинка не найдена]</p>'
            url  = img_obj.image.url
            alt  = escape(img_obj.alt or self.title or '')
            title_attr = f' title="{escape(img_obj.title)}"' if img_obj.title else ''
            classes = 'rounded-2xl w-full shadow-sm'
            html = (
                f'<figure>\n'
                f'<img src="{url}" alt="{alt}"{title_attr}'
                f' loading="lazy" decoding="async" class="{classes}">\n'
            )
            if img_obj.caption:
                html += f'<figcaption>{escape(img_obj.caption)}</figcaption>\n'
            html += '</figure>'
            return html

        source = re.sub(r'\[image(\d+)\]', _replace, source, flags=re.IGNORECASE)

        # ── 2. Пометить [toc] плейсхолдером (реальный TOC строим после рендера) ──
        TOC_PLACEHOLDER = '<div id="ck-toc-placeholder"></div>'
        has_toc = bool(re.search(r'\[toc\]', source, re.IGNORECASE))
        if has_toc:
            source = re.sub(r'\[toc\]', TOC_PLACEHOLDER, source, flags=re.IGNORECASE)

        # ── 3. Парсить FAQ-блоки ( #### Q : ... @@ ) ──────────────────────
        source, parsed_faqs = self._parse_faq_blocks(source)
        self._parsed_faqs = parsed_faqs

        html = markdown.markdown(
            source,
            extensions=['extra', 'toc', 'nl2br', 'sane_lists'],
            output_format='html',
        )

        # ── 4. Построить TOC по реальным id из отрендеренных H2 ────────────
        if has_toc:
            h2_matches = re.findall(
                r'<h2[^>]*\sid="([^"]+)"[^>]*>(.*?)</h2>',
                html, re.IGNORECASE | re.DOTALL,
            )
            if h2_matches:
                items_html = ''
                for i, (slug, title_html) in enumerate(h2_matches, 1):
                    title_text = re.sub(r'<[^>]+>', '', title_html).strip()
                    items_html += (
                        f'<li>'
                        f'<a href="#{slug}" class="ck-toc-link">'
                        f'<span class="ck-toc-num">{i}</span>'
                        f'<span>{title_text}</span>'
                        f'</a></li>\n'
                    )
                toc_html = (
                    f'<nav class="ck-toc" aria-label="Содержание">'
                    f'<p class="ck-toc-title">'
                    f'<svg class="w-4 h-4 inline-block mr-1.5 align-middle" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 10h16M4 14h10"/></svg>'
                    f'Содержание</p>'
                    f'<ol>{items_html}</ol>'
                    f'</nav>'
                )
            else:
                toc_html = ''
            html = html.replace(TOC_PLACEHOLDER, toc_html)

        # ── 5. Постобработка HTML ──────────────────────────────────────────
        # Разбить <p>текст<br>текст</p> на отдельные <p> (nl2br слипает абзацы)
        html = re.sub(r'<br\s*/?>\s*\n?', '</p>\n<p>', html)
        # Убрать пустые параграфы <p></p> и <p> </p>
        html = re.sub(r'<p>\s*</p>', '', html)        # Обернуть таблицы для горизонтальной прокрутки на мобильных
        html = re.sub(r'<table', '<div class="ck-table-wrap"><table', html)
        html = re.sub(r'</table>', '</table></div>', html)
        self.content = html

    def _parse_faq_blocks(self, source):
        """Парсит блоки FAQ из content_md и возвращает (modified_source, [(q, a), ...]).

        Синтаксис:
            #### Q : Вопрос?
            Ответ в markdown

            #### Q : Ещё вопрос?
            Ещё ответ
            @@
            Обычный текст продолжается...
        """
        import re
        import markdown as md
        from django.utils.html import escape

        lines = source.split('\n')
        result_lines = []
        all_faqs = []

        in_faq = False
        current_question = None
        current_answer_lines = []
        current_block = []

        for line in lines:
            q_match = re.match(r'^#{4}\s+Q\s*:\s*(.+)', line)
            if q_match:
                if current_question is not None:
                    current_block.append((current_question, '\n'.join(current_answer_lines).strip()))
                current_question = q_match.group(1).strip()
                current_answer_lines = []
                in_faq = True
            elif in_faq and line.strip() == '@@':
                if current_question is not None:
                    current_block.append((current_question, '\n'.join(current_answer_lines).strip()))
                result_lines.append(self._render_faq_html(current_block))
                all_faqs.extend(current_block)
                current_block = []
                current_question = None
                current_answer_lines = []
                in_faq = False
            elif in_faq:
                current_answer_lines.append(line)
            else:
                result_lines.append(line)

        # незакрытый блок
        if in_faq:
            if current_question is not None:
                current_block.append((current_question, '\n'.join(current_answer_lines).strip()))
            if current_block:
                result_lines.append(self._render_faq_html(current_block))
                all_faqs.extend(current_block)

        return '\n'.join(result_lines), all_faqs

    def _render_faq_html(self, faq_pairs):
        """Рендерит список (question, answer) в HTML-аккордеон."""
        import markdown as md
        from django.utils.html import escape

        items = []
        for question, answer in faq_pairs:
            answer_html = md.markdown(answer, extensions=['extra', 'nl2br']) if answer else ''
            q_esc = escape(question)
            items.append(
                f'<details class="ck-faq-item group">\n'
                f'<summary class="ck-faq-q">'
                f'<span class="flex-1">{q_esc}</span>'
                f'<svg class="ck-faq-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
                f'<path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/>'
                f'</svg>'
                f'</summary>\n'
                f'<div class="ck-faq-a">{answer_html}</div>\n'
                f'</details>'
            )

        items_html = '\n'.join(items)
        return (
            '<div class="ck-faq not-prose">\n'
            '<div class="ck-faq-header">'
            '<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">'
            '<path stroke-linecap="round" stroke-linejoin="round" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>'
            '</svg>'
            '<span>Часто задаваемые вопросы</span>'
            '</div>\n'
            f'{items_html}\n'
            '</div>'
        )


class ArticleFAQ(models.Model):
    """Вопросы и ответы для FAQ-схемы (schema.org/FAQPage)."""
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='faqs')
    question = models.CharField(max_length=500, verbose_name='Вопрос')
    answer = models.TextField(verbose_name='Ответ')
    order = models.PositiveSmallIntegerField(default=0, verbose_name='Порядок')
    is_auto = models.BooleanField(
        default=False,
        verbose_name='Авто (из контента)',
        help_text='True — создан из #### Q : ... @@ синтаксиса в content_md',
    )

    class Meta:
        ordering = ['order']
        verbose_name = 'FAQ-вопрос'
        verbose_name_plural = 'FAQ'

    def __str__(self):
        return self.question


class ArticleImage(models.Model):
    """Дополнительные изображения статьи, вставляемые через [imageN]."""
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE,
        related_name='extra_images',
        verbose_name='Статья',
    )
    number = models.PositiveSmallIntegerField(
        verbose_name='Номер',
        help_text='Используйте [imageN] в контенте статьи (N = это число)',
    )
    image = models.ImageField(
        upload_to='catalog/article/',
        verbose_name='Изображение',
    )
    alt = models.CharField(
        max_length=300, blank=True,
        verbose_name='Alt-текст',
        help_text='Описание для SEO и screen-reader',
    )
    title = models.CharField(
        max_length=300, blank=True,
        verbose_name='Title',
        help_text='Всплывающая подсказка (title="...")',
    )
    caption = models.CharField(
        max_length=500, blank=True,
        verbose_name='Подпись',
        help_text='Подпись под изображением (figcaption)',
    )

    class Meta:
        verbose_name = 'Изображение'
        verbose_name_plural = 'Изображения'
        ordering = ['number']
        unique_together = [('article', 'number')]

    def __str__(self):
        return f'[image{self.number}] — {self.article.title}'

    def shortcode(self):
        return f'[image{self.number}]'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.image and self.image.name and not self.image.name.endswith('.webp'):
            process_image_field(self.image)

