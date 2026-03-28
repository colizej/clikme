from django.http import HttpResponse
from django.urls import path


def robots_txt(request):
    protocol = 'https' if request.is_secure() else 'http'
    host = request.get_host()
    sitemap_url = f"{protocol}://{host}/sitemap.xml"
    
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        f"Disallow: /django-admin/",
        "Disallow: /api/",
        "Disallow: /accounts/",
        "",
        f"Sitemap: {sitemap_url}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")


urlpatterns = [
    path("robots.txt", robots_txt),
]
