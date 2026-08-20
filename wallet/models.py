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

    # Address fields - current residence
    village = models.ForeignKey('Village', on_delete=models.SET_NULL, null=True, blank=True, related_name='residents')
    street_address = models.CharField(max_length=255, null=True, blank=True, help_text="House number, street, building")

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
    
    # Address - can use village from hierarchy OR free text
    village = models.ForeignKey('Village', on_delete=models.SET_NULL, null=True, blank=True, related_name='kyc_residents')
    address_detail = models.CharField(max_length=255, null=True, blank=True, help_text="House number, street, additional details")
    address = models.TextField(null=True, blank=True, help_text="Legacy free-text address (auto-generated from village if empty)")
    
    nationality = models.CharField(max_length=100, null=True, blank=True)
    id_document = models.CharField(max_length=255, null=True, blank=True)
    selfie_image = models.CharField(max_length=255, null=True, blank=True)
    verification_status = models.CharField(max_length=50, default='pending')
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True, help_text='Reason for rejection (shown to user)')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        # Auto-generate address text from village if empty
        if not self.address and self.village:
            commune = self.village.commune
            district = commune.district
            province = district.province
            detail = self.address_detail or ""
            self.address = f"{detail}, {self.village.name}, {commune.name}, {district.name}, {province.name}".lstrip(", ")
        super().save(*args, **kwargs)

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

class BakongPayment(models.Model):
    """Track Bakong QR payment transactions."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    ]
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='bakong_payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='KHR')
    reference_number = models.CharField(max_length=100, unique=True)
    qr_code = models.TextField(null=True, blank=True)  # Base64 encoded QR image
    # The MD5 of the exact KHQR payload. Bakong uses this value to look up a
    # completed transaction through /v1/check_transaction_by_md5.
    bakong_md5 = models.CharField(max_length=32, null=True, blank=True, db_index=True)
    bakong_tx_id = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    webhook_payload = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Bakong {self.reference_number} - {self.amount} {self.currency}"

class FraudDetection(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE)
    risk_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    status = models.CharField(max_length=50, default='pending')
    detected_at = models.DateTimeField(auto_now_add=True)


# ── Address Hierarchy Models (Cambodia Administrative Divisions) ─────────────────

class Province(models.Model):
    """Cambodian provinces."""
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    name_other = models.CharField(max_length=100, null=True, blank=True, help_text="English name or alternative")
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='provinces_created')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'Province'
        verbose_name_plural = 'Provinces'

    def __str__(self):
        return f"{self.name} ({self.code})"


class District(models.Model):
    """Cambodian districts (Khan/Srok)."""
    province = models.ForeignKey(Province, on_delete=models.CASCADE, related_name='districts')
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    name_other = models.CharField(max_length=100, null=True, blank=True, help_text="English name or alternative")
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='districts_created')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'District'
        verbose_name_plural = 'Districts'

    def __str__(self):
        return f"{self.name} ({self.code})"


class Commune(models.Model):
    """Cambodian communes (Sangkat/Khum)."""
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='communes')
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    name_other = models.CharField(max_length=100, null=True, blank=True, help_text="English name or alternative")
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='communes_created')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'Commune'
        verbose_name_plural = 'Communes'

    def __str__(self):
        return f"{self.name} ({self.code})"


class Village(models.Model):
    """Cambodian villages (Phum)."""
    commune = models.ForeignKey(Commune, on_delete=models.CASCADE, related_name='villages')
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    name_other = models.CharField(max_length=100, null=True, blank=True, help_text="English name or alternative")
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='villages_created')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'Village'
        verbose_name_plural = 'Villages'

    def __str__(self):
        return f"{self.name} ({self.code})"


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_security_and_limits(sender, instance, created, **kwargs):
    if created:
        Security.objects.get_or_create(user=instance)
        TransactionLimit.objects.get_or_create(user=instance)
