from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

class User(AbstractUser):
    # Extending default user
    full_name = models.CharField(max_length=255)
    # email is already in AbstractUser but we make it unique
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=50, unique=True)
    role = models.CharField(max_length=50, default='customer')
    status = models.CharField(max_length=50, default='active')

    # Password reset fields
    password_reset_token = models.CharField(max_length=255, null=True, blank=True)
    password_reset_sent_at = models.DateTimeField(null=True, blank=True)

    # AbstractUser already has password, date_joined, etc.

class Wallet(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallets')
    wallet_number = models.CharField(max_length=100, unique=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    CURRENCY_CHOICES = [('KHR', 'KHR'), ('USD', 'USD')]
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='KHR')
    status = models.CharField(max_length=50, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

class Merchant(models.Model):
    merchant_name = models.CharField(max_length=255)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=50, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

class Biller(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='biller_profile')
    biller_name = models.CharField(max_length=255)
    category = models.CharField(max_length=100, null=True, blank=True)
    account_number = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=50, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.biller_name

    @property
    def wallet(self):
        """Get the biller's wallet (if they have a user account)."""
        if self.user:
            return self.user.wallets.first()
        return None

    @property
    def balance(self):
        """Get the biller's wallet balance."""
        wallet = self.wallet
        return wallet.balance if wallet else Decimal('0.00')

class Transaction(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    merchant = models.ForeignKey(Merchant, on_delete=models.SET_NULL, null=True, blank=True)
    biller = models.ForeignKey(Biller, on_delete=models.SET_NULL, null=True, blank=True)
    transaction_type = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=50, default='pending')
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('transfer', 'Transfer'),
        ('bill_payment', 'Bill Payment'),
        ('topup', 'Top Up'),
        ('withdrawal', 'Withdrawal'),
        ('security', 'Security'),
        ('kyc', 'KYC'),
        ('wallet', 'Wallet'),
        ('system', 'System'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True)
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, default='system')
    title = models.CharField(max_length=255)
    message = models.TextField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class IdentityVerification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    national_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    nationality = models.CharField(max_length=100, null=True, blank=True)
    id_document = models.CharField(max_length=255, null=True, blank=True)
    selfie_image = models.CharField(max_length=255, null=True, blank=True)
    verification_status = models.CharField(max_length=50, default='pending')
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True, help_text='Reason for rejection (shown to user)')
    created_at = models.DateTimeField(auto_now_add=True)

class Security(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    pin_hash = models.CharField(max_length=255, null=True, blank=True)
    otp_enabled = models.BooleanField(default=False)
    two_factor_enabled = models.BooleanField(default=False)
    biometric_enabled = models.BooleanField(default=False)
    temp_otp = models.CharField(max_length=6, null=True, blank=True)
    temp_otp_expiry = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class TransactionLimit(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    daily_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    monthly_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    yearly_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)
    ip_address = models.CharField(max_length=45, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Report(models.Model):
    report_type = models.CharField(max_length=100)
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

class Analytics(models.Model):
    period = models.CharField(max_length=50)
    total_income = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    total_expense = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    wallet_usage = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

class Backup(models.Model):
    backup_date = models.DateTimeField(auto_now_add=True)
    backup_location = models.CharField(max_length=255)
    status = models.CharField(max_length=50, default='pending')

class MerchantQR(models.Model):
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE)
    qr_code = models.TextField(unique=True)
    status = models.CharField(max_length=50, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

class BillPayment(models.Model):
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE)
    bill_type = models.CharField(max_length=100)
    account_reference = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

class Withdrawal(models.Model):
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE)
    bank_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

class Topup(models.Model):
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=100)
    provider = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Transfer(models.Model):
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE)
    sender_wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='sent_transfers')
    receiver_wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='received_transfers')
    created_at = models.DateTimeField(auto_now_add=True)

class FraudDetection(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE)
    risk_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    status = models.CharField(max_length=50, default='pending')
    detected_at = models.DateTimeField(auto_now_add=True)


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_security_and_limits(sender, instance, created, **kwargs):
    if created:
        Security.objects.get_or_create(user=instance)
        TransactionLimit.objects.get_or_create(user=instance)

