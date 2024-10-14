from django.shortcuts import render, redirect, get_object_or_404
from products.models import ProductCategory, Product, Cart, CartItem, CartInvitation, ProductVote, Payment, PaymentConfirmation, OrderItem, Order
from django.contrib import messages
from django.views.decorators.http import require_POST
from .forms import CreateCartForm, SendInvitationForm, AssignPaymentForm, UpdateBudgetForm, VoteForm, PaymentAddressForm, ConfirmPaymentForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import datetime
from django.db import transaction



def index(request):
    return render(request, 'products/index.html')


@login_required
def catalog(request):
    # Получаем параметр категории из GET-запроса (если есть)
    category_id = request.GET.get('category')
    if category_id:
        products = Product.objects.filter(category_id=category_id, available=True)
    else:
        products = Product.objects.filter(available=True)

    categories = ProductCategory.objects.all()
    carts = request.user.carts.all()  # Получение всех корзин пользователя

    context = {
        'title': 'Store - Каталог',
        'products': products,
        'categories': categories,
        'carts': carts,  # Добавляем корзины в контекст
    }
    return render(request, 'products/catalog.html', context)


@login_required
def cart_list(request):
    user_carts = request.user.carts.all()
    # Получаем все неприёнятые приглашения для текущего пользователя
    received_invitations = request.user.received_invitations.filter(accepted=False)

    context = {
        'user_carts': user_carts,
        'received_invitations': received_invitations,
    }
    return render(request, 'products/cart_list.html', context)

# products/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import CreateCartForm
from .models import Cart
from django.contrib import messages

@login_required
def create_cart(request):
    if request.method == 'POST':
        form = CreateCartForm(request.POST, initial={'user': request.user})
        if form.is_valid():
            cart = form.save()
            cart.users.add(request.user)  # Добавляем создателя в корзину
            messages.success(request, f"Корзина '{cart.name}' успешно создана.")
            return redirect('products:cart_list')
    else:
        form = CreateCartForm()
    return render(request, 'products/create_cart.html', {'form': form})

@login_required
def send_invitation(request, cart_id):
    cart = get_object_or_404(Cart, id=cart_id)
    if request.user not in cart.users.all():
        messages.error(request, "У вас нет доступа к этой корзине.")
        return redirect('products:cart_list')

    if request.method == 'POST':
        form = SendInvitationForm(request.POST)
        if form.is_valid():
            to_user = form.cleaned_data['to_username']
            if to_user in cart.users.all():
                messages.warning(request, f"Пользователь '{to_user.username}' уже является участником корзины.")
            else:
                invitation, created = CartInvitation.objects.get_or_create(
                    cart=cart,
                    from_user=request.user,
                    to_user=to_user
                )
                if created:
                    messages.success(request, f"Приглашение отправлено пользователю '{to_user.username}'.")
                else:
                    messages.warning(request, f"Приглашение уже было отправлено пользователю '{to_user.username}'.")
            return redirect('products:cart_list')
    else:
        form = SendInvitationForm()
    return render(request, 'products/send_invitation.html', {'form': form, 'cart': cart})

@login_required
def accept_invitation(request, invitation_id):
    invitation = get_object_or_404(CartInvitation, id=invitation_id, to_user=request.user)
    if invitation.accepted:
        messages.info(request, "Это приглашение уже принято.")
    else:
        invitation.cart.users.add(request.user)
        invitation.accepted = True
        invitation.save()
        messages.success(request, f"Вы успешно присоединились к корзине '{invitation.cart.name}'.")
    return redirect('products:cart_list')

@require_POST
@login_required
def reject_invitation(request, invitation_id):
    invitation = get_object_or_404(CartInvitation, id=invitation_id, to_user=request.user)
    if invitation.accepted:
        messages.info(request, "Это приглашение уже принято.")
    else:
        invitation.delete()
        messages.success(request, f"Вы отклонили приглашение в корзину '{invitation.cart.name}'.")
    return redirect('products:cart_list')

@login_required
def view_cart(request, cart_id):
    cart = get_object_or_404(Cart, id=cart_id)
    if request.user not in cart.users.all():
        messages.error(request, "У вас нет доступа к этой корзине.")
        return redirect('products:cart_list')
    cart_items = cart.items.select_related('product').all()
    total_cost = cart.get_total_cost()
    budget = cart.budget
    budget_exceeded = cart.is_over_budget()
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'total_cost': total_cost,
        'budget': budget,
        'budget_exceeded': budget_exceeded,
    }
    return render(request, 'products/cart.html', context)

@require_POST
@login_required
def add_to_cart(request):
    cart_id = request.POST.get('cart_id')
    product_id = request.POST.get('product_id')
    quantity = request.POST.get('quantity', 1)

    # Проверяем наличие cart_id и product_id
    if not cart_id or not product_id:
        messages.error(request, "Некорректные данные формы.")
        return redirect('products:catalog')

    # Получаем корзину и товар
    cart = get_object_or_404(Cart, id=cart_id, users=request.user)
    product = get_object_or_404(Product, id=product_id, available=True)

    # Проверяем и преобразуем количество
    try:
        quantity = int(quantity)
        if quantity < 1:
            raise ValueError
    except ValueError:
        messages.error(request, "Некорректное количество.")
        return redirect('products:catalog')

    # Проверяем наличие товара в корзине
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

    if not created:
        # Проверяем, достаточно ли товара на складе
        total_quantity = cart_item.quantity + quantity
        if total_quantity > product.quantity:
            available_quantity = product.quantity - cart_item.quantity
            if available_quantity > 0:
                messages.warning(
                    request,
                    f"Недостаточно товара '{product.name}' на складе. Вы можете добавить только {available_quantity} шт."
                )
            else:
                messages.warning(
                    request,
                    f"Товара '{product.name}' больше нет на складе."
                )
            return redirect('products:catalog')
        else:
            # Увеличиваем количество товара
            cart_item.quantity = total_quantity
            cart_item.save()
            messages.success(
                request,
                f"Количество '{product.name}' в корзине '{cart.name}' увеличено до {cart_item.quantity} шт."
            )
    else:
        # Проверяем, достаточно ли товара на складе
        if quantity > product.quantity:
            messages.warning(
                request,
                f"Недостаточно товара '{product.name}' на складе. Осталось только {product.quantity} шт."
            )
            return redirect('products:catalog')
        else:
            # Устанавливаем начальное количество
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(
                request,
                f"Товар '{product.name}' добавлен в корзину '{cart.name}' в количестве {quantity} шт."
            )

    return redirect('products:catalog')

@require_POST
@login_required
def remove_from_cart(request, cart_id, item_id):
    cart = get_object_or_404(Cart, id=cart_id)
    if request.user not in cart.users.all():
        messages.error(request, "У вас нет доступа к этой корзине.")
        return redirect('products:cart_list')
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    cart_item.delete()
    messages.success(request, f"Товар '{cart_item.product.name}' удалён из корзины.")
    return redirect('products:view_cart', cart_id=cart.id)

@require_POST
@login_required
@require_POST
@login_required
def update_cart(request, cart_id, item_id):
    cart = get_object_or_404(Cart, id=cart_id)
    if request.user not in cart.users.all():
        messages.error(request, "У вас нет доступа к этой корзине.")
        return redirect('products:cart_list')
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    try:
        quantity = int(request.POST.get('quantity', 1))
        if quantity > 0:
            if quantity <= cart_item.product.quantity:  # Исправлено здесь
                cart_item.quantity = quantity
                cart_item.save()
                messages.success(request, f"Количество товара '{cart_item.product.name}' обновлено.")
            else:
                messages.warning(request, f"Недостаточно товара '{cart_item.product.name}' на складе.")
        else:
            cart_item.delete()
            messages.success(request, f"Товар '{cart_item.product.name}' удалён из корзины.")
    except ValueError:
        messages.error(request, "Неверный формат количества.")
    return redirect('products:view_cart', cart_id=cart.id)


@login_required
def assign_payment(request, cart_id, item_id):
    cart = get_object_or_404(Cart, id=cart_id)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

    if request.method == 'POST':
        form = AssignPaymentForm(request.POST)
        if form.is_valid():
            paid_by = form.cleaned_data['paid_by']
            cart_item.paid_by = paid_by
            cart_item.save()
            return redirect('products:view_cart', cart_id=cart.id)
    else:
        form = AssignPaymentForm()

    context = {
        'cart': cart,
        'cart_item': cart_item,
        'form': form,
    }
    return render(request, 'products/assign_payment.html', context)

@login_required
def update_budget(request, cart_id):
    cart = get_object_or_404(Cart, id=cart_id)
    if request.user not in cart.users.all():
        messages.error(request, "У вас нет доступа к этой корзине.")
        return redirect('products:cart_list')

    if request.method == 'POST':
        form = UpdateBudgetForm(request.POST, instance=cart)
        if form.is_valid():
            form.save()
            messages.success(request, f"Бюджет корзины '{cart.name}' обновлён.")
            return redirect('products:view_cart', cart_id=cart.id)
    else:
        form = UpdateBudgetForm(instance=cart)

    context = {
        'form': form,
        'cart': cart,
    }
    return render(request, 'products/update_budget.html', context)


@login_required
def vote_to_remove(request, cart_id, item_id):
    cart = get_object_or_404(Cart, id=cart_id)
    if request.user not in cart.users.all():
        messages.error(request, "У вас нет доступа к этой корзине.")
        return redirect('products:cart_list')

    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

    if not cart.is_over_budget():
        messages.info(request, "Бюджет корзины не превышен. Голосование не требуется.")
        return redirect('products:view_cart', cart_id=cart.id)

    if request.method == 'POST':
        form = VoteForm(request.POST)
        if form.is_valid():
            vote_choice = form.cleaned_data['vote']
            vote, created = ProductVote.objects.get_or_create(
                cart_item=cart_item,
                user=request.user,
                defaults={'vote': vote_choice}
            )
            if not created:
                vote.vote = vote_choice
                vote.save()
                messages.success(request, f"Ваш голос за товар '{cart_item.product.name}' обновлён.")
            else:
                messages.success(request, f"Ваш голос за товар '{cart_item.product.name}' учтён.")

            # Проверка, все ли пользователи проголосовали против
            total_users = cart.users.count()
            votes_against = cart_item.votes.filter(vote='AGAINST').count()
            if votes_against == total_users:
                cart_item.delete()
                messages.success(request,
                                 f"Товар '{cart_item.product.name}' был удалён из корзины из-за отрицательных голосов.")
            return redirect('products:view_cart', cart_id=cart.id)
    else:
        form = VoteForm()

    context = {
        'form': form,
        'cart': cart,
        'cart_item': cart_item,
    }
    return render(request, 'products/vote_to_remove.html', context)


@login_required
def enter_address(request, cart_id):
    cart = get_object_or_404(Cart, id=cart_id)
    if request.user not in cart.users.all():
        messages.error(request, "У вас нет доступа к этой корзине.")
        return redirect('products:cart_list')

    # Получаем или создаём экземпляр Payment, связанный с корзиной
    payment, created = Payment.objects.get_or_create(cart=cart)

    if request.method == 'POST':
        form = PaymentAddressForm(request.POST, instance=payment)
        if form.is_valid():
            form.save()
            # Создаём или обновляем записи в PaymentConfirmation
            PaymentConfirmation.objects.get_or_create(cart=cart, user=request.user)
            messages.success(request, "Адрес успешно сохранён.")
            return redirect('products:confirm_payment', cart_id=cart.id)
    else:
        form = PaymentAddressForm(instance=payment)

    context = {
        'form': form,
        'cart': cart,
    }
    return render(request, 'products/enter_address.html', context)



@login_required
def confirm_payment(request, cart_id):
    cart = get_object_or_404(Cart, id=cart_id)
    if request.user not in cart.users.all():
        messages.error(request, "У вас нет доступа к этой корзине.")
        return redirect('products:cart_list')

    # Получаем или создаём экземпляр Payment, связанный с корзиной
    payment, created = Payment.objects.get_or_create(cart=cart)

    # Проверяем, заполнен ли адрес
    if not payment.address:
        messages.error(request, "Сначала нужно ввести адрес доставки.")
        return redirect('products:enter_address', cart_id=cart.id)

    # Получаем или создаём запись подтверждения оплаты для пользователя
    confirmation, created = PaymentConfirmation.objects.get_or_create(cart=cart, user=request.user)

    if request.method == 'POST':
        form = ConfirmPaymentForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                insufficient_items = []
                for item in cart.items.select_related('product'):
                    product = item.product
                    if item.quantity > product.quantity:
                        insufficient_items.append({
                            'product': product,
                            'available_quantity': product.quantity,
                        })

                if insufficient_items:
                    message = "Некоторые товары недоступны в желаемом количестве:\n"
                    for entry in insufficient_items:
                        message += f"Товар '{entry['product'].name}' доступен в количестве {entry['available_quantity']} шт.\n"
                    messages.error(request, message)
                    return redirect('products:view_cart', cart_id=cart.id)
                else:
                    # Уменьшаем количество товаров на складе
                    for item in cart.items.select_related('product'):
                        product = item.product
                        product.quantity -= item.quantity
                        product.save()

                    # Отмечаем, что пользователь подтвердил оплату
                    confirmation.confirmed = True
                    confirmation.confirmed_at = timezone.now()
                    confirmation.save()
                    messages.success(request, "Вы подтвердили оплату.")

                    # Проверяем, подтвердили ли оплату все пользователи
                    total_users = cart.users.count()
                    confirmed_payments = PaymentConfirmation.objects.filter(cart=cart, confirmed=True).count()
                    if confirmed_payments == total_users:
                        # Все пользователи подтвердили, завершаем заказ
                        cart.completed = True
                        cart.save()
                        messages.success(request, "Оплата прошла успешно. Спасибо за покупку!")

                        # Создаём заказ перед удалением корзины
                        order = Order.objects.create(
                            address=payment.address,
                            total_cost=cart.get_total_cost(),
                        )
                        # Добавляем пользователей в заказ
                        order.users.set(cart.users.all())
                        # Создаём элементы заказа
                        for item in cart.items.select_related('product'):
                            OrderItem.objects.create(
                                order=order,
                                product=item.product,
                                quantity=item.quantity,
                                price=item.product.price,
                            )

                        # Удаляем корзину после успешной оплаты
                        cart.delete()
                        messages.success(request, "Корзина успешно удалена после оплаты.")

                        # Перенаправляем на страницу деталей заказа
                        return redirect('products:order_detail', order_id=order.id)

                    # Перенаправляем обратно на страницу подтверждения оплаты
                    return redirect('products:confirm_payment', cart_id=cart.id)
    else:
        form = ConfirmPaymentForm()

    # Добавляем возвращаемый HttpResponse
    context = {
        'cart': cart,
        'user_confirmed': confirmation.confirmed,
        'payment': payment,
        'form': form,
    }
    return render(request, 'products/payment.html', context)

@login_required
def initiate_payment(request, cart_id):
    cart = get_object_or_404(Cart, id=cart_id, users=request.user)

    # Получаем или создаём объект Payment для корзины
    payment, created = Payment.objects.get_or_create(cart=cart)

    # Если оплата уже завершена, перенаправляем обратно
    if payment.completed:
        messages.info(request, "Оплата для этой корзины уже завершена.")
        return redirect('products:view_cart', cart_id=cart.id)

    # Если адрес уже введён и все пользователи подтвердили оплату
    if payment.address and payment.confirmed_by.count() >= cart.users.count():
        payment.completed = True
        payment.save()
        messages.success(request, "Оплата успешно завершена.")
        # Сохраняем cart_id перед удалением
        cart_id = cart.id
        # Удаляем корзину после успешной оплаты
        cart.delete()
        messages.success(request, "Корзина успешно удалена после оплаты.")
        # Перенаправляем на список корзин
        return redirect('products:cart_list')

    if request.method == 'POST':
        if not payment.address:
            # Обработка ввода адреса
            form = PaymentAddressForm(request.POST, instance=payment)
            if form.is_valid():
                payment = form.save(commit=False)
                payment.initiated_by = request.user
                payment.created_at = timezone.now()
                payment.save()
                # Создаём или обновляем записи в PaymentConfirmation для всех пользователей корзины
                for user in cart.users.all():
                    PaymentConfirmation.objects.get_or_create(cart=cart, user=user)
                messages.success(request, "Адрес успешно сохранён.")
                return redirect('products:initiate_payment', cart_id=cart.id)
        else:
            # Обработка подтверждения оплаты
            form = ConfirmPaymentForm(request.POST)
            if form.is_valid():
                payment.confirmed_by.add(request.user)
                payment.save()
                messages.success(request, "Ваше подтверждение оплаты учтено.")
                # Проверка, подтвердили ли все пользователи
                if payment.confirmed_by.count() >= cart.users.count():
                    payment.completed = True
                    payment.save()
                    messages.success(request, "Оплата успешно завершена.")
                    # Сохраняем cart_id перед удалением
                    cart_id = cart.id
                    # Удаляем корзину после успешной оплаты
                    cart.delete()
                    messages.success(request, "Корзина успешно удалена после оплаты.")
                    # Перенаправляем на список корзин
                    return redirect('products:cart_list')
    else:
        if not payment.address:
            form = PaymentAddressForm(instance=payment)
        else:
            form = ConfirmPaymentForm()

    context = {
        'cart': cart,
        'form': form,
        'payment': payment,
    }
    return render(request, 'products/payment.html', context)



@login_required
def delete_cart(request, cart_id):
    cart = get_object_or_404(Cart, id=cart_id, users=request.user)

    if request.method == 'POST':
        cart.delete()
        messages.success(request, f"Корзина '{cart.name}' успешно удалена.")
        return redirect('products:cart_list')

    context = {
        'cart': cart,
    }
    return render(request, 'products/confirm_delete_cart.html', context)

@login_required
def order_list(request):
    orders = request.user.orders.all()
    context = {
        'orders': orders,
    }
    return render(request, 'products/orders.html', context)

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, users=request.user)
    context = {
        'order': order,
    }
    return render(request, 'products/order_detail.html', context)