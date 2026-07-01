from rest_framework import viewsets
from django.shortcuts import render
from .models import (
    User, Wallet, Merchant, Biller, Transaction, Notification, IdentityVerification,
    Security, TransactionLimit, AuditLog, Report, Analytics, Backup, MerchantQR,
    BillPayment, Withdrawal, Topup, Transfer, FraudDetection
)
from .serializers import (
    UserSerializer, WalletSerializer, MerchantSerializer, BillerSerializer,
    TransactionSerializer, NotificationSerializer, IdentityVerificationSerializer,
    SecuritySerializer, TransactionLimitSerializer, AuditLogSerializer,
    ReportSerializer, AnalyticsSerializer, BackupSerializer, MerchantQRSerializer,
    BillPaymentSerializer, WithdrawalSerializer, TopupSerializer, TransferSerializer,
    FraudDetectionSerializer
)

def index(request):
    return render(request, 'wallet/index.html')

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class WalletViewSet(viewsets.ModelViewSet):
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer

class MerchantViewSet(viewsets.ModelViewSet):
    queryset = Merchant.objects.all()
    serializer_class = MerchantSerializer

class BillerViewSet(viewsets.ModelViewSet):
    queryset = Biller.objects.all()
    serializer_class = BillerSerializer

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

class IdentityVerificationViewSet(viewsets.ModelViewSet):
    queryset = IdentityVerification.objects.all()
    serializer_class = IdentityVerificationSerializer

class SecurityViewSet(viewsets.ModelViewSet):
    queryset = Security.objects.all()
    serializer_class = SecuritySerializer

class TransactionLimitViewSet(viewsets.ModelViewSet):
    queryset = TransactionLimit.objects.all()
    serializer_class = TransactionLimitSerializer

class AuditLogViewSet(viewsets.ModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer

class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer

class AnalyticsViewSet(viewsets.ModelViewSet):
    queryset = Analytics.objects.all()
    serializer_class = AnalyticsSerializer

class BackupViewSet(viewsets.ModelViewSet):
    queryset = Backup.objects.all()
    serializer_class = BackupSerializer

class MerchantQRViewSet(viewsets.ModelViewSet):
    queryset = MerchantQR.objects.all()
    serializer_class = MerchantQRSerializer

class BillPaymentViewSet(viewsets.ModelViewSet):
    queryset = BillPayment.objects.all()
    serializer_class = BillPaymentSerializer

class WithdrawalViewSet(viewsets.ModelViewSet):
    queryset = Withdrawal.objects.all()
    serializer_class = WithdrawalSerializer

class TopupViewSet(viewsets.ModelViewSet):
    queryset = Topup.objects.all()
    serializer_class = TopupSerializer

class TransferViewSet(viewsets.ModelViewSet):
    queryset = Transfer.objects.all()
    serializer_class = TransferSerializer

class FraudDetectionViewSet(viewsets.ModelViewSet):
    queryset = FraudDetection.objects.all()
    serializer_class = FraudDetectionSerializer
