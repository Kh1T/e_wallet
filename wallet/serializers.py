from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import (
    User, Wallet, Merchant, Biller, Transaction, Notification, IdentityVerification,
    Security, TransactionLimit, AuditLog, Report, Analytics, Backup, MerchantQR,
    BillPayment, Withdrawal, Topup, Transfer, FraudDetection
)
import uuid


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for new user registration.
    Automatically creates a linked Wallet for the new user.
    """
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True, label='Confirm Password')

    class Meta:
        model = User
        fields = ['full_name', 'email', 'phone', 'password', 'password2']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        # Use email as username
        user = User(
            username=validated_data['email'],
            **validated_data
        )
        user.set_password(password)
        user.save()
        # Auto-create a KHR wallet for the new user
        Wallet.objects.create(
            user=user,
            wallet_number=f'WAL-{uuid.uuid4().hex[:10].upper()}',
            currency='KHR',
        )
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer used for documenting login input fields."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing the authenticated user's password."""
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    new_password2 = serializers.CharField(write_only=True, required=True, label='Confirm New Password')

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({'new_password': 'New passwords do not match.'})
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for reading and updating the user's own profile."""
    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'phone', 'role', 'status', 'date_joined']
        read_only_fields = ['id', 'role', 'status', 'date_joined', 'email']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'phone', 'role', 'status']

class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = '__all__'

class MerchantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Merchant
        fields = '__all__'

class BillerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Biller
        fields = '__all__'

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'

class IdentityVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = IdentityVerification
        fields = '__all__'

class SecuritySerializer(serializers.ModelSerializer):
    class Meta:
        model = Security
        fields = '__all__'

class TransactionLimitSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionLimit
        fields = '__all__'

class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = '__all__'

class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = '__all__'

class AnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Analytics
        fields = '__all__'

class BackupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Backup
        fields = '__all__'

class MerchantQRSerializer(serializers.ModelSerializer):
    class Meta:
        model = MerchantQR
        fields = '__all__'

class BillPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillPayment
        fields = '__all__'

class WithdrawalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Withdrawal
        fields = '__all__'

class TopupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topup
        fields = '__all__'

class TransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transfer
        fields = '__all__'

class FraudDetectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FraudDetection
        fields = '__all__'
