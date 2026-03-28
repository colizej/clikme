from django.urls import path
from . import views

app_name = 'ads'

urlpatterns = [
    path('ads/click/<int:ad_id>/', views.ads_click, name='click'),
    path('ads/pixel/<int:ad_id>/', views.ads_pixel, name='pixel'),
]
