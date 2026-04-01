const API_VENDORS  = 'https://clikme.ru/api/bot/vendors/';
const API_ARTICLES = 'https://clikme.ru/api/bot/articles/';

// ── Переключение вкладок ──────────────────────────────────────────────────────
function switchTab(tabId) {
    document.querySelectorAll('.tab-button').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => { c.classList.remove('visible'); c.classList.add('hidden'); });
    document.getElementById(tabId).classList.add('active');
    const contentId = tabId === 'tab1' ? 'content1' : 'content2';
    document.getElementById(contentId).classList.remove('hidden');
    document.getElementById(contentId).classList.add('visible');
}

// ── Свайп на тег-баре ─────────────────────────────────────────────────────────
function initSwipe(selector) {
    const el = document.querySelector(selector);
    if (!el) return;
    let isDragging = false, startX, scrollLeft;
    el.addEventListener('mousedown',  e => { isDragging = true; startX = e.pageX - el.offsetLeft; scrollLeft = el.scrollLeft; });
    el.addEventListener('mouseleave', () => isDragging = false);
    el.addEventListener('mouseup',    () => isDragging = false);
    el.addEventListener('mousemove',  e => { if (!isDragging) return; e.preventDefault(); el.scrollLeft = scrollLeft - (e.pageX - el.offsetLeft - startX) * 2; });
    el.addEventListener('touchstart', e => { isDragging = true; startX = e.touches[0].pageX - el.offsetLeft; scrollLeft = el.scrollLeft; });
    el.addEventListener('touchend',   () => isDragging = false);
    el.addEventListener('touchmove',  e => { if (!isDragging) return; e.preventDefault(); el.scrollLeft = scrollLeft - (e.touches[0].pageX - el.offsetLeft - startX) * 2; });
}

// ── Поиск ─────────────────────────────────────────────────────────────────────
let allVendors  = [];
let allArticles = [];
let searchTimer = null;

function initSearch() {
    const input = document.getElementById('search-input');
    if (!input) return;
    input.addEventListener('input', () => {
        const q = input.value.trim();
        clearTimeout(searchTimer);
        if (!q) {
            renderVendors(allVendors);
            renderArticles(allArticles);
            return;
        }
        if (q.length < 2) return;
        searchTimer = setTimeout(() => {
            fetch(`https://clikme.ru/api/bot/search/?q=${encodeURIComponent(q)}`)
                .then(r => r.json())
                .then(results => {
                    if (!Array.isArray(results)) return;
                    const vendors  = results.filter(r => r.type === 'vendor');
                    const articles = results.filter(r => r.type === 'article' || r.type === 'news');
                    renderVendors(vendors.map(r => ({ name: r.title, url: r.url, description: '', logo_url: '', zone: '' })));
                    renderArticles(articles.map(r => ({ title: r.title, url: r.url, image_url: '', tag: '' })));
                })
                .catch(() => {
                    const ql = q.toLowerCase();
                    renderVendors(allVendors.filter(v => v.name.toLowerCase().includes(ql) || v.description.toLowerCase().includes(ql)));
                    renderArticles(allArticles.filter(a => a.title.toLowerCase().includes(ql)));
                });
        }, 400);
    });
}

// ── Утилиты ───────────────────────────────────────────────────────────────────
function truncate(text, max) { return text && text.length > max ? text.slice(0, max) + '…' : text || ''; }

// ── Компании ──────────────────────────────────────────────────────────────────
function renderVendors(data) {
    const container = document.querySelector('#content1 .restaurant-list');
    container.innerHTML = '';
    if (!data.length) {
        container.innerHTML = '<p class="text-center text-muted py-4">Ничего не найдено</p>';
        return;
    }
    data.forEach(v => {
        const col = document.createElement('div');
        col.className = `col-md-4 ${v.zone || 'central_zone'}`;
        col.innerHTML = `
            <div class="card restaurant-link border shadow-sm position-relative rounded mb-5" style="cursor:pointer" onclick="window.open('${v.url}','_blank')">
                <img src="${v.logo_url || 'https://via.placeholder.com/77'}" width="77" height="77"
                     class="rounded-3 position-absolute restaurant-logo" style="top:-20px;left:13px;object-fit:cover" alt="">
                <div class="card-body">
                    <div class="d-flex mb-2" style="min-height:72px;">
                        <div class="col-3 d-flex align-items-end">
                            <i class="bi bi-star-fill me-1 text-warning"></i><span class="small">5.0</span>
                        </div>
                        <div class="col-9">
                            <p class="card-text small ms-1">${truncate(v.description, 120)}</p>
                        </div>
                    </div>
                    <div class="d-flex justify-content-between align-items-center">
                        <h5 class="card-title mb-0">${v.name}</h5>
                        <i class="bi bi-arrow-right-circle-fill fs-4" style="color:#6CC4A7"></i>
                    </div>
                </div>
            </div>`;
        container.appendChild(col);
    });
}

function initVendors() {
    fetch(API_VENDORS)
        .then(r => r.json())
        .then(data => {
            allVendors = data;
            renderVendors(data);

            // Фильтр по зонам
            document.querySelectorAll('#tag-list-restaurant .tag-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    document.querySelectorAll('#tag-list-restaurant .tag-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    const tag = btn.getAttribute('data-tag');
                    renderVendors(tag === 'all' ? allVendors : allVendors.filter(v => v.zone === tag));
                });
            });
        })
        .catch(e => console.error('Vendors load error:', e));
}

// ── Статьи ────────────────────────────────────────────────────────────────────
function renderArticles(data) {
    const container = document.getElementById('masonryContainer');
    container.innerHTML = '';
    if (!data.length) {
        container.innerHTML = '<p class="text-center text-muted py-4">Ничего не найдено</p>';
        return;
    }
    data.forEach(a => {
        const col = document.createElement('div');
        col.className = 'col-sm-6 col-md-4';
        col.innerHTML = `
            <div class="card bg-transparent blog-link border-0 h-100" style="cursor:pointer" onclick="window.open('${a.url}','_blank')">
                <img src="${a.image_url || 'https://via.placeholder.com/300x180'}" class="card-img-top rounded-5" style="height:180px;object-fit:cover" alt="">
                <div class="card-body px-0">
                    <h5 class="h6 card-title mb-0 text-center">${a.title}</h5>
                </div>
            </div>`;
        container.appendChild(col);
    });
}

function initArticles() {
    fetch(API_ARTICLES)
        .then(r => r.json())
        .then(data => {
            allArticles = data;

            // Теги
            const tagList = document.getElementById('tag-list-blog');
            const allTags = [...new Set(data.flatMap(a => a.tag ? a.tag.split(',').map(t => t.trim()).filter(Boolean) : []))];

            const allBtn = document.createElement('button');
            allBtn.textContent = 'Все статьи';
            allBtn.setAttribute('data-tag', 'all');
            allBtn.className = 'tag-btn active';
            allBtn.addEventListener('click', () => { setActiveTag(tagList, 'all'); renderArticles(allArticles); });
            tagList.appendChild(allBtn);

            allTags.forEach(tag => {
                const btn = document.createElement('button');
                btn.textContent = tag;
                btn.setAttribute('data-tag', tag);
                btn.className = 'tag-btn';
                btn.addEventListener('click', () => {
                    setActiveTag(tagList, tag);
                    renderArticles(allArticles.filter(a => a.tag && a.tag.split(',').map(t => t.trim()).includes(tag)));
                });
                tagList.appendChild(btn);
            });

            renderArticles(data);
        })
        .catch(e => console.error('Articles load error:', e));
}

function setActiveTag(container, tag) {
    container.querySelectorAll('.tag-btn').forEach(b => {
        b.classList.toggle('active', b.getAttribute('data-tag') === tag);
    });
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initSwipe('.tag-container');
    initSearch();
    initVendors();
    initArticles();
});
