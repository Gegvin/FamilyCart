from django import forms
from .models import Cart, CartInvitation
from django.contrib.auth.models import User

class CreateCartForm(forms.ModelForm):
    """
    Форма для создания новой корзины.
    Пользователь вводит название корзины.
    """
    name = forms.CharField(
        max_length=255,
        label='Название корзины',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите название корзины'
        }),
        required=True
    )

    class Meta:
        model = Cart
        fields = ['name']

    def clean_name(self):
        """
        Проверка уникальности названия корзины для пользователя.
        """
        name = self.cleaned_data.get('name')
        user = self.initial.get('user')  # Передаём пользователя через инициализацию формы
        if Cart.objects.filter(name=name, users=user).exists():
            raise forms.ValidationError("У вас уже есть корзина с таким названием.")
        return name

class SendInvitationForm(forms.Form):
    to_username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Никнейм пользователя'}),
        required=True
    )

    def clean_to_username(self):
        username = self.cleaned_data.get('to_username')
        try:
            user = User.objects.get(username=username)
            return user
        except User.DoesNotExist:
            raise forms.ValidationError("Пользователь с таким никнеймом не найден.")

class AddToCartForm(forms.Form):
    cart_id = forms.IntegerField(widget=forms.HiddenInput())
    product_id = forms.IntegerField(widget=forms.HiddenInput())
    quantity = forms.IntegerField(min_value=1, initial=1, label='Количество', widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}))