from django.http import HttpResponse
from django.urls import path


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        f"Disallow: /{__import__('django.conf', fromlist=['settings']).settings.ADMIN_URL}/",
        "Disallow: /api/",
        "Disallow: /accounts/",
        "",
        "Sitemap: https://clikme.ru/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


urlpatterns = [
    path("", robots_txt),
]
