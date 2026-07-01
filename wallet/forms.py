from django import forms
from decimal import Decimal


class LoginForm(forms.Form):
    email    = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)


class RegisterForm(forms.Form):
    full_name = forms.CharField(max_length=255)
    email     = forms.EmailField()
    phone     = forms.CharField(max_length=50)
    password  = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password') != cleaned.get('password2'):
            self.add_error('password2', 'Passwords do not match.')
        return cleaned


class SendMoneyForm(forms.Form):
    recipient_wallet = forms.CharField(max_length=100, label='Recipient Wallet Number')
    amount           = forms.DecimalField(
        min_value=Decimal('0.01'), max_digits=12, decimal_places=2
    )
    description = forms.CharField(max_length=255, required=False)


class TopupForm(forms.Form):
    PAYMENT_CHOICES = [
        ('bank',    'Bank Transfer'),
        ('card',    'Credit / Debit Card'),
        ('aba',     'ABA Mobile'),
        ('acleda',  'ACLEDA Mobile'),
    ]
    amount         = forms.DecimalField(min_value=Decimal('1.00'), max_digits=12, decimal_places=2)
    payment_method = forms.ChoiceField(choices=PAYMENT_CHOICES)


class ProfileUpdateForm(forms.Form):
    full_name = forms.CharField(max_length=255)
    phone     = forms.CharField(max_length=50)


class ChangePasswordForm(forms.Form):
    old_password  = forms.CharField(widget=forms.PasswordInput, label='Current Password')
    new_password  = forms.CharField(widget=forms.PasswordInput, label='New Password')
    new_password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm New Password')

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('new_password') != cleaned.get('new_password2'):
            self.add_error('new_password2', 'New passwords do not match.')
        return cleaned
