from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap

urlpatterns = [
    path(f'{settings.ADMIN_URL}/', admin.site.urls),

    # Auth
    path('accounts/', include('django.contrib.auth.urls')),

    # Apps — специфические пути ПЕРЕД slug-диспатчером blog
    path('news/', include('apps.news.urls')),
    path('', include('apps.pages.urls')),
    path('', include('apps.newsletter.urls')),
    path('', include('apps.vendors.urls')),
    path('', include('apps.blog.urls')),  # slug_dispatch — последним

    # Robots
    path('robots.txt', include('apps.pages.robots')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
