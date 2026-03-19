from django.urls import path
from . import views

app_name = 'pages'

urlpatterns = [
    path('privacy/', views.PrivacyView.as_view(), name='privacy'),
    path('contacts/', views.ContactsView.as_view(), name='contacts'),
    path('sitemap.xml', views.SitemapView.as_view(), name='sitemap'),
]
