from django.shortcuts import render, HttpResponse
from products.models import ProductCategory, Product


def index(request):
    return render(request, 'products/index.html')


def catalog(request):
    # Получаем параметр категории из GET-запроса (если есть)
    category_id = request.GET.get('category')
    if category_id:
        products = Product.objects.filter(category_id=category_id)
    else:
        products = Product.objects.all()

    categories = ProductCategory.objects.all()

    context = {
        'title': 'Store - Каталог',
        'products': products,
        'categories': categories,
    }
    return render(request, 'products/catalog.html', context)
