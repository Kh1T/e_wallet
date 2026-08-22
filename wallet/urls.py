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

    # ── GUI Page routes ─────────────────────────────────────────────
    path('login/',        views.LoginPageView.as_view(),    name='login'),
    path('register/',     views.RegisterPageView.as_view(), name='register'),
    path('logout/',       views.LogoutPageView.as_view(),   name='logout'),
    path('forgot-password/', views.ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', views.ResetPasswordView.as_view(), name='reset-password'),
    path('dashboard/',    views.DashboardView.as_view(),    name='dashboard'),
    path('accounts/',     views.AccountsView.as_view(),   name='accounts'),
    path('transactions/', views.TransactionListView.as_view(), name='transactions'),
    path('accounts/statement/download/', views.AccountStatementDownloadView.as_view(), name='account_statement_download'),
    path('create-wallet/', views.CreateWalletView.as_view(), name='create_wallet'),
    path('wallet-management/', views.WalletManagementView.as_view(), name='wallet_management'),
    path('send/',         views.SendMoneyView.as_view(),    name='send'),
    path('topup/',        views.TopupView.as_view(),        name='topup'),
    path('bill-payment/', views.BillPaymentPageView.as_view(), name='bill_payment'),
    path('profile/',      views.ProfileView.as_view(),      name='profile'),
    path('kyc/',          views.KYCVerificationView.as_view(), name='kyc'),
    path('reports/',       views.UserReportsView.as_view(),   name='reports'),
    path('kyc-review/',   views.KYCReviewView.as_view(),     name='kyc_review'),
    path('notifications/', views.NotificationListView.as_view(), name='notifications'),
    
    # ── Bakong Payment routes ───────────────────────────────────────
    path('bakong-topup/', views.BakongTopupView.as_view(), name='bakong_topup'),
    path('bakong-qr/<int:payment_id>/', views.BakongQRDisplayView.as_view(), name='bakong_qr_display'),
    path('bakong-history/', views.BakongPaymentHistoryView.as_view(), name='bakong_history'),

    # ── Auth API endpoints (JWT) ────────────────────────────────────
    path('api/auth/register/',        views.RegisterView.as_view(),       name='auth-register'),
    path('api/auth/login/',           views.LoginView.as_view(),          name='auth-login'),
    path('api/auth/logout/',          views.LogoutView.as_view(),         name='auth-logout'),
    path('api/auth/me/',              views.MeView.as_view(),             name='auth-me'),
    path('api/auth/change-password/', views.ChangePasswordView.as_view(), name='auth-change-password'),
    path('api/auth/token/refresh/',   views.AuthTokenRefreshView.as_view(), name='auth-token-refresh'),

    # ── Password Reset API endpoints (Resend) ───────────────────────
    path('api/auth/password-reset/request/', views.PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('api/auth/password-reset/verify/',  views.PasswordResetVerifyView.as_view(),  name='password-reset-verify'),
    path('api/auth/password-reset/validate/', views.PasswordResetValidateTokenView.as_view(), name='password-reset-validate'),

    # ── Transfer API endpoints ──────────────────────────────────────
    path('api/transfers/p2p/',        views.PeerToPeerTransferView.as_view(), name='p2p-transfer'),
    path('api/transfers/history/',    views.TransferHistoryView.as_view(),    name='transfer-history'),

    # ── Admin API endpoints ─────────────────────────────────────────
    path('api/admin/transactions/',         views.AdminAllTransactionsView.as_view(),   name='admin-transactions'),
    path('api/admin/transactions/summary/',  views.AdminTransactionSummaryView.as_view(), name='admin-transactions-summary'),
    
    # ── Bakong API endpoints ────────────────────────────────────────
    path('api/bakong/verify/', views.BakongVerifyTransactionAPI.as_view(), name='bakong-verify-transaction'),
    path('api/bakong/payment/<int:payment_id>/status/', views.BakongPaymentStatusAPI.as_view(), name='bakong-payment-status'),
    path('webhooks/bakong/', views.BakongWebhookView.as_view(), name='bakong-webhook'),

    # ── Address Hierarchy API endpoints ───────────────────────────
    path('api/addresses/provinces/', views.ProvinceListView.as_view(), name='address-provinces'),
    path('api/addresses/provinces/<int:province_id>/districts/', views.DistrictListView.as_view(), name='address-districts'),
    path('api/addresses/districts/<int:district_id>/communes/', views.CommuneListView.as_view(), name='address-communes'),
    path('api/addresses/communes/<int:commune_id>/villages/', views.VillageListView.as_view(), name='address-villages'),

    # ── Resource API endpoints (CRUD) ───────────────────────────────
    path('api/', include(router.urls)),
]
