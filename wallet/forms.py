from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal

from .models import Wallet


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
    sender_wallet = forms.ModelChoiceField(
        queryset=Wallet.objects.none(),
        label='From Wallet',
        empty_label=None,
    )
    recipient_wallet = forms.CharField(max_length=100, label='Recipient Wallet Number')
    amount           = forms.DecimalField(
        min_value=Decimal('0.01'), max_digits=12, decimal_places=2
    )
    description = forms.CharField(max_length=255, required=False)
    pin         = forms.CharField(max_length=6, min_length=4, widget=forms.PasswordInput, label='Transaction PIN')
    otp_code    = forms.CharField(max_length=6, required=False, label='OTP Code')

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields['sender_wallet'].queryset = Wallet.objects.filter(user=user)


class ChangePinForm(forms.Form):
    old_pin = forms.CharField(
        max_length=6, min_length=4, widget=forms.PasswordInput, required=False, label='Current PIN (if set)'
    )
    new_pin = forms.CharField(
        max_length=6, min_length=4, widget=forms.PasswordInput, label='New PIN'
    )
    new_pin2 = forms.CharField(
        max_length=6, min_length=4, widget=forms.PasswordInput, label='Confirm New PIN'
    )

    def __init__(self, *args, has_pin=False, **kwargs):
        super().__init__(*args, **kwargs)
        if has_pin:
            self.fields['old_pin'].required = True

    def clean(self):
        cleaned = super().clean()
        new_pin = cleaned.get('new_pin')
        new_pin2 = cleaned.get('new_pin2')
        if new_pin and new_pin2 and new_pin != new_pin2:
            self.add_error('new_pin2', 'New PINs do not match.')
        if new_pin and not new_pin.isdigit():
            self.add_error('new_pin', 'PIN must contain only digits.')
        return cleaned



class TopupForm(forms.Form):
    MIN_AMOUNT = Decimal('1000')
    MAX_AMOUNT = Decimal('10000000')
    PAYMENT_CHOICES = [
        ('aba_mobile',  'ABA Mobile'),
        ('acleda_mobile', 'ACLEDA Mobile'),
        ('bank_transfer', 'Bank Transfer'),
        ('card', 'Credit / Debit Card'),
    ]
    wallet = forms.ModelChoiceField(
        queryset=Wallet.objects.none(),
        label='Top Up To Wallet',
        empty_label=None,
    )
    amount = forms.DecimalField(
        required=True,
        min_value=MIN_AMOUNT,
        max_value=MAX_AMOUNT,
        max_digits=12,
        decimal_places=0,
        error_messages={
            'required': 'Amount is required.',
            'invalid': 'Amount must be numeric.',
            'min_value': 'Minimum top up is 1,000 KHR.',
            'max_value': 'Maximum top up is 10,000,000 KHR.',
        },
    )
    payment_method = forms.ChoiceField(choices=PAYMENT_CHOICES)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields['wallet'].queryset = Wallet.objects.filter(user=user)


class ProfileUpdateForm(forms.Form):
    full_name = forms.CharField(max_length=255)
    phone     = forms.CharField(max_length=50)


class KYCVerificationForm(forms.Form):
    full_name = forms.CharField(max_length=255, label='Full Name')
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Date of Birth'
    )
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), label='Address')
    nationality = forms.CharField(max_length=100, label='Nationality')
    national_id = forms.CharField(max_length=100, label='National ID Number')
    id_document = forms.FileField(label='ID Document (Passport / National ID)')
    selfie_image = forms.FileField(label='Selfie Image', required=False)

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_national_id(self):
        national_id = self.cleaned_data.get('national_id')
        if national_id:
            from .models import IdentityVerification
            existing = IdentityVerification.objects.filter(national_id=national_id).first()
            if existing and (not self.user or existing.user != self.user):
                raise ValidationError('This National ID is already registered with another account.')
        return national_id


class ChangePasswordForm(forms.Form):
    old_password  = forms.CharField(widget=forms.PasswordInput, label='Current Password')
    new_password  = forms.CharField(widget=forms.PasswordInput, label='New Password')
    new_password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm New Password')

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('new_password') != cleaned.get('new_password2'):
            self.add_error('new_password2', 'New passwords do not match.')
        return cleaned


class WalletManagementForm(forms.Form):
    ACTION_CHOICES = [
        ('view_balance', 'View Balance'),
        ('view_info', 'View Wallet Information'),
        ('update_info', 'Update Wallet Information'),
        ('freeze', 'Freeze Wallet'),
        ('unfreeze', 'Unfreeze Wallet'),
        ('close', 'Close Wallet'),
    ]
    action = forms.ChoiceField(choices=ACTION_CHOICES, widget=forms.RadioSelect)


class UpdateWalletForm(forms.Form):
    CURRENCY_CHOICES = [('KHR', 'KHR'), ('USD', 'USD')]
    currency = forms.ChoiceField(choices=CURRENCY_CHOICES, label='Currency')


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(label='Email address')


class ResetPasswordForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput, label='New Password')
    new_password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm New Password')

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('new_password') != cleaned.get('new_password2'):
            self.add_error('new_password2', 'Passwords do not match.')
        return cleaned
