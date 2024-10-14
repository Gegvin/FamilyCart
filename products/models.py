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
    budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    payment_confirmations = models.ManyToManyField(User, through='PaymentConfirmation', related_name='payment_confirmations')


    def __str__(self):
        return f"Корзина: {self.name}"

    def get_total_cost(self):
        return sum(item.get_cost() for item in self.items.all())
    def is_over_budget(self):
        if self.budget is None:
            return False
        return self.get_total_cost() > self.budget


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    paid_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='paid_cart_items')

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

class ProductVote(models.Model):
    VOTE_CHOICES = (
        ('FOR', 'За'),
        ('AGAINST', 'Против'),
    )
    cart_item = models.ForeignKey(CartItem, on_delete=models.CASCADE, related_name='votes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='product_votes')
    vote = models.CharField(max_length=7, choices=VOTE_CHOICES)
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart_item', 'user')  # Один пользователь может голосовать только один раз за товар

    def __str__(self):
        return f"{self.user.username} голосовал '{self.get_vote_display()}' за '{self.cart_item.product.name}'"

class PaymentConfirmation(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    confirmed = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('cart', 'user')

    def __str__(self):
        return f"{self.user.username} подтвердил оплату для корзины '{self.cart.name}'"


class Payment(models.Model):
    cart = models.OneToOneField(Cart, on_delete=models.CASCADE, related_name='payment')
    address = models.TextField(null=True, blank=True)
    initiated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='initiated_payments')
    confirmed_by = models.ManyToManyField(User, related_name='confirmed_payments', blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return f"Оплата для корзины '{self.cart.name}'"

class Order(models.Model):
    users = models.ManyToManyField(User, related_name='orders')
    created_at = models.DateTimeField(default=timezone.now)
    address = models.TextField()
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, default='Ожидает отправки')

    def __str__(self):
        return f"Заказ #{self.id} от {self.created_at.strftime('%Y-%m-%d')}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('Product', related_name='order_items', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Цена на момент покупки

    def get_cost(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.product.name} (x{self.quantity})"