/**
 * Транслитерация кириллицы в латиницу для слагов в Django-админке.
 * Подключается через Media класса в admin.py.
 */
(function () {
    'use strict';

    const MAP = {
        'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'zh',
        'з':'z','и':'i','й':'j','к':'k','л':'l','м':'m','н':'n','о':'o',
        'п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'kh','ц':'ts',
        'ч':'ch','ш':'sh','щ':'sch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu',
        'я':'ya',
        'А':'A','Б':'B','В':'V','Г':'G','Д':'D','Е':'E','Ё':'Yo','Ж':'Zh',
        'З':'Z','И':'I','Й':'J','К':'K','Л':'L','М':'M','Н':'N','О':'O',
        'П':'P','Р':'R','С':'S','Т':'T','У':'U','Ф':'F','Х':'Kh','Ц':'Ts',
        'Ч':'Ch','Ш':'Sh','Щ':'Sch','Ъ':'','Ы':'Y','Ь':'','Э':'E','Ю':'Yu',
        'Я':'Ya',
    };

    function transliterate(text) {
        return text.split('').map(ch => MAP[ch] !== undefined ? MAP[ch] : ch).join('');
    }

    function toSlug(text) {
        return transliterate(text)
            .toLowerCase()
            .replace(/[^a-z0-9\-]/g, '-')
            .replace(/-+/g, '-')
            .replace(/^-|-$/g, '');
    }

    // Перехватываем prepopulated_fields Django после его инициализации
    function patchPrepopulated() {
        if (typeof window.prepopulate === 'undefined') return;

        const original = window.prepopulate;
        window.prepopulate = function (id, maxLength, dependencies) {
            original(id, maxLength, dependencies);

            const slugField = document.getElementById(id);
            if (!slugField) return;

            // Навешиваем свой обработчик поверх Django-шного
            dependencies.forEach(function (depId) {
                const depField = document.getElementById(depId);
                if (!depField) return;

                depField.addEventListener('input', function () {
                    // Только если слаг ещё не редактировался вручную
                    if (slugField.dataset.customized === '1') return;
                    slugField.value = toSlug(this.value).substring(0, maxLength);
                });
            });

            slugField.addEventListener('input', function () {
                this.dataset.customized = '1';
            });
        };
    }

    // Django грузит prepopulate.js асинхронно — ждём
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', patchPrepopulated);
    } else {
        patchPrepopulated();
    }
})();
