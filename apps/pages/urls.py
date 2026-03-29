from django.urls import path
from . import views

app_name = 'pages'

urlpatterns = [
    path('privacy/', views.PageDetailView.as_view(), {'slug': 'politika-konfidencialnosti'}, name='privacy'),
    path('terms/', views.PageDetailView.as_view(), {'slug': 'terms'}, name='terms'),
    path('pravila/', views.PageDetailView.as_view(), {'slug': 'pravila-ispolzovania'}, name='rules'),
    path('contacts/', views.ContactsView.as_view(), name='contacts'),
    path('sitemap.xml', views.SitemapView.as_view(), name='sitemap'),
    path('<slug>/', views.PageDetailView.as_view(), name='detail'),
]
