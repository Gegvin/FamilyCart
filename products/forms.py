from django import forms
from .models import Cart, CartInvitation, CartItem, Payment
from django.contrib.auth.models import User

class CreateCartForm(forms.ModelForm):
    name = forms.CharField(
        max_length=255,
        label='Название корзины',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите название корзины'
        }),
        required=True
    )
    budget = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label='Бюджет (₽)',
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите бюджет (опционально)'
        })
    )

    class Meta:
        model = Cart
        fields = ['name', 'budget']

    def clean_budget(self):
        budget = self.cleaned_data.get('budget')
        if budget is not None and budget < 0:
            raise forms.ValidationError("Бюджет не может быть отрицательным.")
        return budget

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

class AssignPaymentForm(forms.ModelForm):
    paid_by = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=True,
        label='Оплачивает',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = CartItem
        fields = ['paid_by']

    def __init__(self, *args, **kwargs):
        users = kwargs.pop('users', None)
        super().__init__(*args, **kwargs)
        if users:
            self.fields['paid_by'].queryset = users

class UpdateBudgetForm(forms.ModelForm):
    budget = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label='Бюджет',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Введите бюджет (опционально)'})
    )

    class Meta:
        model = Cart
        fields = ['budget']

class VoteForm(forms.Form):
    VOTE_CHOICES = (
        ('AGAINST', 'Против'),
    )
    vote = forms.ChoiceField(
        choices=VOTE_CHOICES,
        widget=forms.RadioSelect,
        required=True,
        label='Голосование'
    )




class PaymentAddressForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['address']
        widgets = {
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Введите ваш адрес',
                'rows': 3,
            }),
        }
        labels = {
            'address': 'Адрес доставки',
        }


class ConfirmPaymentForm(forms.Form):
    confirm = forms.BooleanField(required=True, widget=forms.HiddenInput(), initial=True)