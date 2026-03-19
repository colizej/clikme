from django.views.generic import ListView, DetailView
from .models import Vendor, Product


class VendorListView(ListView):
    model = Vendor
    template_name = 'vendors/vendor_list.html'
    context_object_name = 'vendors'
    paginate_by = 24

    def get_queryset(self):
        return Vendor.objects.filter(is_active=True)


class VendorDetailView(DetailView):
    model = Vendor
    template_name = 'vendors/vendor_detail.html'
    context_object_name = 'vendor'

    def get_queryset(self):
        return Vendor.objects.filter(is_active=True)


class ProductDetailView(DetailView):
    model = Product
    template_name = 'vendors/product_detail.html'
    context_object_name = 'product'

    def get_queryset(self):
        return Product.objects.filter(is_active=True)
