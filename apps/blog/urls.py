from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('search/', views.SearchView.as_view(), name='search'),
    # /cat/slug/ — статья с категорией
    path('<slug:cat>/<slug:slug>/', views.ArticleDetailView.as_view(), name='article_detail'),
    # /slug/ — диспатчер: Article | Vendor | Product | Page
    path('<slug:slug>/', views.slug_dispatch, name='slug_dispatch'),
]
