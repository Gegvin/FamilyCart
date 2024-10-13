from django.contrib import admin

from products.models import ProductCategory, Product, Cart, CartItem, CartInvitation

admin.site.register(ProductCategory)
admin.site.register(Product)

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name']
    filter_horizontal = ['users']

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity']
    list_filter = ['cart__name', 'product__name']
    search_fields = ['cart__name', 'product__name']

@admin.register(CartInvitation)
class CartInvitationAdmin(admin.ModelAdmin):
    list_display = ['cart', 'from_user', 'to_user', 'accepted', 'created_at']
    list_filter = ['accepted', 'created_at']
    search_fields = ['cart__name', 'from_user__username', 'to_user__username']