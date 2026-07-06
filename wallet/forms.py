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
    MIN_AMOUNT = Decimal('1000')
    MAX_AMOUNT = Decimal('10000000')
    PAYMENT_CHOICES = [
        ('aba_mobile',  'ABA Mobile'),
        ('acleda_mobile', 'ACLEDA Mobile'),
        ('bank_transfer', 'Bank Transfer'),
        ('card', 'Credit / Debit Card'),
    ]
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


class ChangePasswordForm(forms.Form):
    old_password  = forms.CharField(widget=forms.PasswordInput, label='Current Password')
    new_password  = forms.CharField(widget=forms.PasswordInput, label='New Password')
    new_password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm New Password')

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('new_password') != cleaned.get('new_password2'):
            self.add_error('new_password2', 'New passwords do not match.')
        return cleaned
