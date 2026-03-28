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
    path('politika-konfidencialnosti/', RedirectView.as_view(url='/privacy/', permanent=True)),
    path('politika-konfidencialnosti', RedirectView.as_view(url='/privacy/', permanent=True)),
    
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
