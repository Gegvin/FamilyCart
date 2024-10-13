from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver


class ProductCategory (models.Model):
    name = models.CharField(max_length=128, unique=True)
    description =  models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

class Product (models.Model):
    name = models.CharField(max_length=256)
    description = models.TextField()
    price = models.DecimalField(max_digits=6, decimal_places=2)
    quantity = models.PositiveIntegerField(default=0)
    available = models.BooleanField(default=True)
    image = models.ImageField(upload_to='products_images')
    category = models.ForeignKey(to=ProductCategory,on_delete=models.PROTECT)

    def __str__(self):
        return f"Продукт: {self.name} | Категория: {self.category.name}"

class Cart(models.Model):
    name = models.CharField(max_length=255, default='Общая корзина')
    users = models.ManyToManyField(User, related_name='carts')
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Корзина: {self.name}"

    def get_total_cost(self):
        return sum(item.get_cost() for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} в корзине '{self.cart.name}'"

    def get_cost(self):
        return self.product.price * self.quantity

class CartInvitation(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='invitations')
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_invitations')
    created_at = models.DateTimeField(default=timezone.now)
    accepted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('cart', 'to_user')

    def __str__(self):
        return f"Приглашение от {self.from_user.username} для {self.to_user.username} в корзину '{self.cart.name}'"

@receiver(post_save, sender=User)
def create_user_cart(sender, instance, created, **kwargs):
    if created:
        personal_cart = Cart.objects.create(
            name=f"Личная корзина {instance.username}"
        )
        personal_cart.users.add(instance)