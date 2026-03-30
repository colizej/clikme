from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('search/', views.SearchView.as_view(), name='search'),
    path('search/api/', views.search_api, name='search_api'),
    # /cat/slug/ — статья с категорией (поддерживает кириллицу через <str:>)
    path('<str:cat>/<str:slug>/', views.ArticleDetailView.as_view(), name='article_detail'),
    # /slug/ — диспатчер: Article | Vendor | Product | Page (кириллица OK)
    path('<str:slug>/', views.slug_dispatch, name='slug_dispatch'),
]
