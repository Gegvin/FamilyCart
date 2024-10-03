# products/urls.py

from django.urls import path
from .views import index, catalog

urlpatterns = [
    path('', index, name='index'),  # Главная страница
    path('catalog/', catalog, name='catalog'),  # Каталог товаров

]