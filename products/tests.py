# products/tests.py

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import (
    ProductCategory, Product, Cart, CartItem,
    Order, OrderItem, Payment, PaymentConfirmation, ProductVote
)
from .forms import CreateCartForm, PaymentAddressForm, ConfirmPaymentForm

class ProductCategoryModelTest(TestCase):

    def setUp(self):
        self.category = ProductCategory.objects.create(
            name='Electronics',
            description='Electronic devices and gadgets'
        )

    def test_category_creation(self):
        self.assertEqual(self.category.name, 'Electronics')
        self.assertEqual(self.category.description, 'Electronic devices and gadgets')
        self.assertTrue(isinstance(self.category, ProductCategory))
        self.assertEqual(str(self.category), 'Electronics')

class ProductModelTest(TestCase):

    def setUp(self):
        self.category = ProductCategory.objects.create(name='Books')
        self.product = Product.objects.create(
            name='Django for Beginners',
            description='An introductory book about Django',
            price=29.99,
            quantity=100,
            available=True,
            category=self.category
        )

    def test_product_creation(self):
        self.assertEqual(self.product.name, 'Django for Beginners')
        self.assertEqual(self.product.price, 29.99)
        self.assertEqual(self.product.quantity, 100)
        self.assertTrue(self.product.available)
        self.assertEqual(self.product.category.name, 'Books')
        self.assertTrue(isinstance(self.product, Product))
        self.assertEqual(str(self.product), f"Продукт: {self.product.name} | Категория: {self.category.name}")

class CartModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.cart = Cart.objects.create(name='Test Cart')
        self.cart.users.add(self.user)

    def test_cart_creation(self):
        self.assertEqual(self.cart.name, 'Test Cart')
        self.assertIn(self.user, self.cart.users.all())
        self.assertTrue(isinstance(self.cart, Cart))
        self.assertEqual(str(self.cart), f"Корзина: {self.cart.name}")

    def test_cart_total_cost(self):
        category = ProductCategory.objects.create(name='Electronics')
        product1 = Product.objects.create(
            name='Laptop',
            description='A powerful laptop',
            price=1000,
            quantity=10,
            available=True,
            category=category
        )
        product2 = Product.objects.create(
            name='Smartphone',
            description='A modern smartphone',
            price=500,
            quantity=20,
            available=True,
            category=category
        )
        CartItem.objects.create(cart=self.cart, product=product1, quantity=2)
        CartItem.objects.create(cart=self.cart, product=product2, quantity=3)
        total_cost = self.cart.get_total_cost()
        expected_cost = 2 * 1000 + 3 * 500
        self.assertEqual(total_cost, expected_cost)

class ViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.password = 'testpass'
        self.user = User.objects.create_user(username='testuser', password=self.password)
        self.category = ProductCategory.objects.create(name='Books')
        self.product = Product.objects.create(
            name='Django Testing',
            description='Learn how to test Django applications',
            price=50.00,
            quantity=10,
            available=True,
            category=self.category
        )
        self.cart = Cart.objects.create(name='Test Cart')
        self.cart.users.add(self.user)
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=2)

    def test_catalog_view(self):
        # Проверяем перенаправление неавторизованного пользователя
        response = self.client.get(reverse('products:catalog'))
        self.assertEqual(response.status_code, 302)  # Должен перенаправить на страницу входа

        # Входим в систему
        self.client.login(username='testuser', password=self.password)
        response = self.client.get(reverse('products:catalog'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products/catalog.html')

    def test_create_cart_view(self):
        self.client.login(username='testuser', password=self.password)
        response = self.client.get(reverse('products:create_cart'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products/create_cart.html')

        # Тестируем создание корзины через POST-запрос
        response = self.client.post(reverse('products:create_cart'), {
            'name': 'My Test Cart',
            'budget': '1000.00'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Cart.objects.filter(name='My Test Cart').exists())

    def test_view_cart(self):
        self.client.login(username='testuser', password=self.password)
        response = self.client.get(reverse('products:view_cart', args=[self.cart.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products/cart.html')
        self.assertContains(response, 'Django Testing')

class FormTests(TestCase):

    def test_create_cart_form_valid(self):
        form_data = {'name': 'New Cart', 'budget': '500.00'}
        form = CreateCartForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_create_cart_form_invalid(self):
        form_data = {'name': '', 'budget': '-100.00'}
        form = CreateCartForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        self.assertIn('budget', form.errors)

class PaymentAndOrderTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.password = 'testpass'
        self.user = User.objects.create_user(username='testuser', password=self.password)
        self.client.login(username='testuser', password=self.password)

        self.category = ProductCategory.objects.create(name='Books')
        self.product = Product.objects.create(
            name='Django Testing',
            description='Learn how to test Django applications',
            price=50.00,
            quantity=10,
            available=True,
            category=self.category
        )
        self.cart = Cart.objects.create(name='Test Cart')
        self.cart.users.add(self.user)
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=2)

    def test_payment_process(self):
        # Ввод адреса доставки
        response = self.client.post(reverse('products:enter_address', args=[self.cart.id]), {
            'address': '123 Test Street'
        })
        self.assertRedirects(response, reverse('products:confirm_payment', args=[self.cart.id]))

        # Подтверждение оплаты
        response = self.client.post(reverse('products:confirm_payment', args=[self.cart.id]), {
            'confirm': 'True'
        })
        # Проверяем перенаправление на детали заказа
        order = Order.objects.first()
        self.assertRedirects(response, reverse('products:order_detail', args=[order.id]))
        # Проверяем, что корзина удалена
        self.assertFalse(Cart.objects.filter(id=self.cart.id).exists())
        # Проверяем, что заказ создан
        self.assertTrue(Order.objects.filter(id=order.id).exists())
        self.assertEqual(order.total_cost, 100.00)
        self.assertEqual(order.address, '123 Test Street')

    def test_order_detail_view(self):
        # Создаём заказ
        order = Order.objects.create(
            address='123 Test Street',
            total_cost=100.00,
        )
        order.users.add(self.user)
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=2,
            price=50.00
        )

        # Проверяем доступ к деталям заказа
        response = self.client.get(reverse('products:order_detail', args=[order.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products/order_detail.html')
        self.assertContains(response, 'Django Testing')
        self.assertContains(response, '100.00')
