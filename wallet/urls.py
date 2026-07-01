from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'wallets', views.WalletViewSet)
router.register(r'merchants', views.MerchantViewSet)
router.register(r'billers', views.BillerViewSet)
router.register(r'transactions', views.TransactionViewSet)
router.register(r'notifications', views.NotificationViewSet)
router.register(r'identity-verifications', views.IdentityVerificationViewSet)
router.register(r'security', views.SecurityViewSet)
router.register(r'transaction-limits', views.TransactionLimitViewSet)
router.register(r'audit-logs', views.AuditLogViewSet)
router.register(r'reports', views.ReportViewSet)
router.register(r'analytics', views.AnalyticsViewSet)
router.register(r'backups', views.BackupViewSet)
router.register(r'merchant-qrs', views.MerchantQRViewSet)
router.register(r'bill-payments', views.BillPaymentViewSet)
router.register(r'withdrawals', views.WithdrawalViewSet)
router.register(r'topups', views.TopupViewSet)
router.register(r'transfers', views.TransferViewSet)
router.register(r'fraud-detections', views.FraudDetectionViewSet)

urlpatterns = [
    path('', views.index, name='index'),
    path('api/', include(router.urls)),
]
