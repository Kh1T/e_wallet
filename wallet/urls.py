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
    path('dashboard/',    views.DashboardView.as_view(),    name='dashboard'),
    path('transactions/', views.TransactionListView.as_view(), name='transactions'),
    path('send/',         views.SendMoneyView.as_view(),    name='send'),
    path('topup/',        views.TopupView.as_view(),        name='topup'),
    path('profile/',      views.ProfileView.as_view(),      name='profile'),
    path('kyc/',          views.KYCVerificationView.as_view(), name='kyc'),
    path('kyc-review/',   views.KYCReviewView.as_view(),     name='kyc_review'),

    # ── Auth API endpoints (JWT) ────────────────────────────────────
    path('api/auth/register/',        views.RegisterView.as_view(),       name='auth-register'),
    path('api/auth/login/',           views.LoginView.as_view(),          name='auth-login'),
    path('api/auth/logout/',          views.LogoutView.as_view(),         name='auth-logout'),
    path('api/auth/me/',              views.MeView.as_view(),             name='auth-me'),
    path('api/auth/change-password/', views.ChangePasswordView.as_view(), name='auth-change-password'),
    path('api/auth/token/refresh/',   views.AuthTokenRefreshView.as_view(), name='auth-token-refresh'),

    # ── Resource API endpoints (CRUD) ───────────────────────────────
    path('api/', include(router.urls)),
]
