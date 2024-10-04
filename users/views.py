# users/views.py

from django.shortcuts import render, redirect
from .forms import CustomAuthenticationForm, CustomUserCreationForm
from django.contrib.auth import login as auth_login  # Переименуйте, чтобы избежать конфликтов
from django.contrib import messages  # Добавьте импорт сообщений

def login_view(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)  # Используйте переименованный login
            messages.success(request, f'Добро пожаловать, {user.username}!')
            return redirect('index')  # Замените на нужный URL
        else:
            messages.error(request, 'Неверные имя пользователя или пароль.')
    else:
        form = CustomAuthenticationForm()
    return render(request, 'users/login.html', {'form': form})

def registration_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)  # Автоматический вход пользователя после регистрации
            messages.success(request, f'Добро пожаловать, {user.username}! Ваш аккаунт успешно создан.')
            return redirect('index')  # Замените на нужный вам URL
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки ниже.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'users/registration.html', {'form': form})