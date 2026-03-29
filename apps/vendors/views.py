from django.views.generic import ListView, DetailView
from django.shortcuts import get_object_or_404
from .models import Vendor, Product


class VendorListView(ListView):
    model = Vendor
    template_name = 'vendors/vendor_list.html'
    context_object_name = 'object_list'

    def get_queryset(self):
        return Vendor.objects.filter(is_active=True).order_by('display_name')


class ProductOrVendorDetailView(DetailView):
    """Universal view that handles both Products and Vendors by slug."""
    template_name = 'vendors/product_detail.html'
    context_object_name = 'product'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return self.render_to_response(self.get_context_data(object=self.object))

    def get_object(self):
        slug = self.kwargs.get('slug')
        # Try Product first
        product = Product.objects.filter(slug=slug, is_active=True).first()
        if product:
            self.template_name = 'vendors/product_detail.html'
            self.context_object_name = 'product'
            return product
        # Try Vendor
        vendor = get_object_or_404(Vendor, slug=slug, is_active=True)
        self.template_name = 'vendors/vendor_detail.html'
        self.context_object_name = 'vendor'
        return vendor


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
