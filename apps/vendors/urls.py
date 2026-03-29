from django.urls import path
from . import views

app_name = 'vendors'

urlpatterns = [
    path('vendors/', views.VendorListView.as_view(), name='vendor_list'),
    path('<slug:slug>/', views.ProductOrVendorDetailView.as_view(), name='detail'),
]
