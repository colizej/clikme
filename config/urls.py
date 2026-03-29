from django.contrib import admin
from django.urls import path, include, register_converter
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.views.generic import RedirectView

class TrailingSlashConverter:
    regex = r'/?'
    
    def to_python(self, value):
        return value.rstrip('/') if value.endswith('/') else value
    
    def to_url(self, value):
        return value

register_converter(TrailingSlashConverter, 'trailing_slash')

urlpatterns = [
    # Редиректы для миграции с OpenCart
    path('about_us/', RedirectView.as_view(url='/contacts/', permanent=True)),
    path('about_us', RedirectView.as_view(url='/contacts/', permanent=True)),
    path('delivery/', RedirectView.as_view(url='/contacts/', permanent=True)),
    path('delivery', RedirectView.as_view(url='/contacts/', permanent=True)),
    
    # Кириллические URL -> латиница
    path('%D0%BA%D0%B0%D0%BA-%D0%B0%D0%B4%D0%B0%D0%BF%D1%82%D0%B8%D1%80%D0%BE%D0%B2%D0%B0%D1%82%D1%8C%D1%81%D1%8F-%D0%BA-%D0%B6%D0%B8%D0%B7%D0%BD%D0%B8-%D0%B2%D0%BE-%D0%92%D1%8C%D0%B5%D1%82%D0%BD%D0%B0%D0%BC%D0%B5/', RedirectView.as_view(url='/kak-adaptirovatsya-k-zhizni-vo-vetname/', permanent=True)),
    path('%D0%BA%D0%B0%D0%BA-%D0%B0%D0%B4%D0%B0%D0%BF%D1%82%D0%B8%D1%80%D0%BE%D0%B2%D0%B0%D1%82%D1%8C%D1%81%D1%8F-%D0%BA-%D0%B6%D0%B8%D0%B7%D0%BD%D0%B8-%D0%B2%D0%BE-%D0%92%D1%8C%D0%B5%D1%82%D0%BD%D0%B0%D0%BC%D0%B5', RedirectView.as_view(url='/kak-adaptirovatsya-k-zhizni-vo-vetname/', permanent=True)),
    path('%D0%9A%D0%B0%D0%BA-%D0%B4%D0%BE%D0%B1%D1%80%D0%B0%D1%82%D1%8C%D1%81%D1%8F-%D0%B8%D0%B7-%D0%B0%D1%8D%D1%80%D0%BE%D0%BF%D0%BE%D1%80%D1%82%D0%B0-%D0%9A%D0%B0%D0%BC%D1%80%D0%B0%D0%BD%D1%8C-%D0%B4%D0%BE-%D0%9D%D1%8F%D1%87%D0%B0%D0%BD%D0%B3%D0%B0/', RedirectView.as_view(url='/kak-dobratsya-iz-aeroporta-kamran-do-nyachanga/', permanent=True)),
    path('%D0%9A%D0%B0%D0%BA-%D0%B4%D0%BE%D0%B1%D1%80%D0%B0%D1%82%D1%8C%D1%81%D1%8F-%D0%B8%D0%B7-%D0%B0%D1%8D%D1%80%D0%BE%D0%BF%D0%BE%D1%80%D1%82%D0%B0-%D0%9A%D0%B0%D0%BC%D1%80%D0%B0%D0%BD%D1%8C-%D0%B4%D0%BE-%D0%9D%D1%8F%D1%87%D0%B0%D0%BD%D0%B3%D0%B0', RedirectView.as_view(url='/kak-dobratsya-iz-aeroporta-kamran-do-nyachanga/', permanent=True)),
    path('%D0%BE%D0%B1%D0%BC%D0%B5%D0%BD-%D0%B2%D0%B0%D0%BB%D1%8E%D1%82%D1%8B-2025/', RedirectView.as_view(url='/obmen-valyuty-2025/', permanent=True)),
    path('%D0%BE%D0%B1%D0%BC%D0%B5%D0%BD-%D0%B2%D0%B0%D0%BB%D1%8E%D1%82%D1%8B-2025', RedirectView.as_view(url='/obmen-valyuty-2025/', permanent=True)),
    path('%D0%B2%D1%81%D0%B5-%D0%BE%D0%B1-%D0%B0%D1%80%D0%B5%D0%BD%D0%B4%D0%B5-%D1%82%D1%80%D0%B0%D0%BD%D1%81%D0%BF%D0%BE%D1%80%D1%82%D0%B0-%D0%B2%D0%BE-%D0%B2%D1%8C%D0%B5%D1%82%D0%BD%D0%B0%D0%BC%D0%B5/', RedirectView.as_view(url='/vse-ob-arende-transporta-vo-vetname/', permanent=True)),
    path('%D0%B2%D1%81%D0%B5-%D0%BE%D0%B1-%D0%B0%D1%80%D0%B5%D0%BD%D0%B4%D0%B5-%D1%82%D1%80%D0%B0%D0%BD%D1%81%D0%BF%D0%BE%D1%80%D1%82%D0%B0-%D0%B2%D0%BE-%D0%B2%D1%8C%D0%B5%D1%82%D0%BD%D0%B0%D0%BC%D0%B5', RedirectView.as_view(url='/vse-ob-arende-transporta-vo-vetname/', permanent=True)),
    path('%D0%BF%D0%BB%D1%8F%D0%B6%D0%B8-%D0%BD%D1%8F%D1%87%D0%B0%D0%BD%D0%B3%D0%B0-%D0%B1%D0%B5%D0%B7-%D0%B2%D0%BE%D0%BB%D0%BD/', RedirectView.as_view(url='/plyazhi-nyachanga-bez-voln-kak-dobratsya-interesnye-fakty/', permanent=True)),
    path('%D0%BF%D0%BB%D1%8F%D0%B6%D0%B8-%D0%BD%D1%8F%D1%87%D0%B0%D0%BD%D0%B3%D0%B0-%D0%B1%D0%B5%D0%B7-%D0%B2%D0%BE%D0%BB%D0%BD', RedirectView.as_view(url='/plyazhi-nyachanga-bez-voln-kak-dobratsya-interesnye-fakty/', permanent=True)),
    path('%D0%BD%D0%B0%D0%B9%D1%82%D0%B8-%D0%BA%D0%B2%D0%B0%D1%80%D1%82%D0%B8%D1%80%D1%8B-%D0%B2%D0%BE-%D0%92%D1%8C%D0%B5%D1%82%D0%BD%D0%B0%D0%BC%D0%B5/', RedirectView.as_view(url='/naiti-kvartiry-vietname-soveti-rekomendatsi/', permanent=True)),
    path('%D0%BD%D0%B0%D0%B9%D1%82%D0%B8-%D0%BA%D0%B2%D0%B0%D1%80%D1%82%D0%B8%D1%80%D1%8B-%D0%B2%D0%BE-%D0%92%D1%8C%D0%B5%D1%82%D0%BD%D0%B0%D0%BC%D0%B5', RedirectView.as_view(url='/naiti-kvartiry-vietname-soveti-rekomendatsi/', permanent=True)),
    path('%D0%BB%D1%83%D1%87%D1%88%D0%B8%D0%B5-%D0%B1%D1%83%D1%84%D0%B5%D1%82%D1%8B-%D0%BD%D1%8F%D1%87%D0%B0%D0%BD%D0%B3%D0%B0/', RedirectView.as_view(url='/luchshie-bufety-nyachanga-gde-poest/', permanent=True)),
    path('%D0%BB%D1%83%D1%87%D1%88%D0%B8%D0%B5-%D0%B1%D1%83%D1%84%D0%B5%D1%82%D1%8B-%D0%BD%D1%8F%D1%87%D0%B0%D0%BD%D0%B3%D0%B0', RedirectView.as_view(url='/luchshie-bufety-nyachanga-gde-poest/', permanent=True)),
    path('%D0%BC%D0%B5%D0%B4%D0%B8%D1%86%D0%B8%D0%BD%D0%B0-%D0%B2%D0%BE-%D0%92%D1%8C%D0%B5%D1%82%D0%BD%D0%B0%D0%BC%D0%B5/', RedirectView.as_view(url='/medicina-vietnam-nado-znat/', permanent=True)),
    path('%D0%BC%D0%B5%D0%B4%D0%B8%D1%86%D0%B8%D0%BD%D0%B0-%D0%B2%D0%BE-%D0%92%D1%8C%D0%B5%D1%82%D0%BD%D0%B0%D0%BC%D0%B5', RedirectView.as_view(url='/medicina-vietnam-nado-znat/', permanent=True)),
    path('%D0%BA%D0%B0%D0%BA-%D0%BD%D0%B0%D1%87%D0%B0%D1%82%D1%8C-%D1%80%D0%B0%D0%B1%D0%BE%D1%82%D0%B0%D1%82%D1%8C-%D0%B2%D0%BE-%D0%92%D1%8C%D0%B5%D1%82%D0%BD%D0%B0%D0%BC%D0%B5/', RedirectView.as_view(url='/kak-nachat-rabotat-vo-vietname/', permanent=True)),
    path('%D0%BA%D0%B0%D0%BA-%D0%BD%D0%B0%D1%87%D0%B0%D1%82%D1%8C-%D1%80%D0%B0%D0%B1%D0%BE%D1%82%D0%B0%D1%82%D1%8C-%D0%B2%D0%BE-%D0%92%D1%8C%D0%B5%D1%82%D0%BD%D0%B0%D0%BC%D0%B5', RedirectView.as_view(url='/kak-nachat-rabotat-vo-vietname/', permanent=True)),
    
    # OpenCart формат index.php
    path('index.php', RedirectView.as_view(url='/', permanent=True)),
    
    path(f'{settings.ADMIN_URL}/', admin.site.urls),

    # Auth
    path('accounts/', include('django.contrib.auth.urls')),

    # Apps — специфические пути ПЕРЕД slug-диспатчером blog
    path('news/', include('apps.news.urls')),
    path('', include('apps.pages.urls')),
    path('', include('apps.newsletter.urls')),
    path('', include('apps.vendors.urls')),
    path('', include('apps.ads.urls')),
    path('', include('apps.blog.urls')),  # slug_dispatch — последним

    # Robots
    path('robots.txt', include('apps.pages.robots')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
