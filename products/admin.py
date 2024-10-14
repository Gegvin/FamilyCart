from django.contrib import admin
from products.models import (
    ProductCategory, Product, Cart, CartItem, CartInvitation,
    Payment, PaymentConfirmation, Order, OrderItem, ProductVote
)

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

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['cart', 'initiated_by', 'completed', 'created_at']
    list_filter = ['completed', 'created_at']
    search_fields = ['cart__name', 'initiated_by__username']

@admin.register(PaymentConfirmation)
class PaymentConfirmationAdmin(admin.ModelAdmin):
    list_display = ['cart', 'user', 'confirmed', 'confirmed_at']
    list_filter = ['confirmed', 'confirmed_at']
    search_fields = ['cart__name', 'user__username']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at', 'total_cost', 'status']
    list_filter = ['status', 'created_at']
    search_fields = ['id', 'users__username']
    filter_horizontal = ['users']

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price']
    list_filter = ['order__id', 'product__name']
    search_fields = ['order__id', 'product__name']

@admin.register(ProductVote)
class ProductVoteAdmin(admin.ModelAdmin):
    list_display = ['cart_item', 'user', 'vote', 'voted_at']
    list_filter = ['vote', 'voted_at']
    search_fields = ['cart_item__product__name', 'user__username']