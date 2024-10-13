from django.shortcuts import render, redirect, get_object_or_404
from products.models import ProductCategory, Product, Cart, CartItem, CartInvitation
from django.contrib import messages
from django.views.decorators.http import require_POST
from .forms import CreateCartForm, SendInvitationForm
from django.contrib.auth.decorators import login_required


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
    context = {
        'cart': cart,
        'cart_items': cart_items,  # Изменено с 'items' на 'cart_items'
        'total_cost': total_cost,
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

    # Проверяем наличие товара в корзине
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

    try:
        quantity = int(quantity)
        if quantity < 1:
            raise ValueError
    except ValueError:
        messages.error(request, "Некорректное количество.")
        return redirect('products:catalog')

    if not created:
        # Увеличиваем количество товара
        cart_item.quantity += quantity
        cart_item.save()
        messages.success(request, f"Количество '{product.name}' в корзине '{cart.name}' увеличено.")
    else:
        # Устанавливаем начальное количество
        cart_item.quantity = quantity
        cart_item.save()
        messages.success(request, f"Товар '{product.name}' добавлен в корзину '{cart.name}'.")

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
def update_cart(request, cart_id, item_id):
    cart = get_object_or_404(Cart, id=cart_id)
    if request.user not in cart.users.all():
        messages.error(request, "У вас нет доступа к этой корзине.")
        return redirect('products:cart_list')
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    try:
        quantity = int(request.POST.get('quantity', 1))
        if quantity > 0:
            if quantity <= cart_item.product.stock:
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