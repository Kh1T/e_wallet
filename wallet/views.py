from rest_framework import viewsets, generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.db import transaction as db_transaction
from django.db.models import Sum, Q
from django.utils import timezone
from decimal import Decimal
import uuid

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
    FraudDetectionSerializer,
    RegisterSerializer, LoginSerializer, ChangePasswordSerializer, UserProfileSerializer,
)
from .forms import (
    LoginForm, RegisterForm, SendMoneyForm, TopupForm,
    ProfileUpdateForm, ChangePasswordForm,
)


# ─────────────────────────────────────────
#  LEGACY INDEX (redirects to dashboard)
# ─────────────────────────────────────────
def index(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


# ═════════════════════════════════════════
#  GUI / SESSION-BASED VIEWS
# ═════════════════════════════════════════

class LoginPageView(View):
    """GET/POST /login/ — Session-based login page."""
    template_name = 'wallet/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return render(request, self.template_name, {'form': LoginForm()})

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
            )
            if user:
                auth_login(request, user)
                return redirect('dashboard')
            form.add_error(None, 'Invalid email or password.')
        return render(request, self.template_name, {'form': form})


class RegisterPageView(View):
    """GET/POST /register/ — Session-based registration page."""
    template_name = 'wallet/register.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return render(request, self.template_name, {'form': RegisterForm()})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            if User.objects.filter(email=d['email']).exists():
                form.add_error('email', 'An account with this email already exists.')
            elif User.objects.filter(phone=d['phone']).exists():
                form.add_error('phone', 'This phone number is already registered.')
            else:
                user = User(
                    username=d['email'],
                    email=d['email'],
                    full_name=d['full_name'],
                    phone=d['phone'],
                )
                user.set_password(d['password'])
                user.save()
                Wallet.objects.create(
                    user=user,
                    wallet_number=f'WAL-{uuid.uuid4().hex[:10].upper()}',
                    currency='KHR',
                )
                auth_login(request, user)
                messages.success(request, f'Welcome, {user.full_name}! Your wallet has been created.')
                return redirect('dashboard')
        return render(request, self.template_name, {'form': form})


class LogoutPageView(View):
    """POST /logout/ — Logs out and redirects to login."""
    def post(self, request):
        auth_logout(request)
        return redirect('login')


class DashboardView(LoginRequiredMixin, View):
    """GET / — Main dashboard."""
    login_url = '/login/'

    def get(self, request):
        wallet = Wallet.objects.filter(user=request.user).first()
        recent_transactions = []
        received_transfers  = []
        total_income        = Decimal('0')
        total_expense       = Decimal('0')
        unread_count        = Notification.objects.filter(user=request.user, is_read=False).count()

        if wallet:
            now         = timezone.now()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            recent_transactions = (
                Transaction.objects
                .filter(wallet=wallet)
                .order_by('-created_at')[:6]
            )
            received_transfers = (
                Transfer.objects
                .filter(receiver_wallet=wallet)
                .select_related('transaction', 'sender_wallet__user')
                .order_by('-created_at')[:6]
            )
            total_expense = (
                Transaction.objects
                .filter(wallet=wallet, created_at__gte=month_start)
                .aggregate(t=Sum('amount'))['t'] or Decimal('0')
            )
            total_income = (
                Transfer.objects
                .filter(receiver_wallet=wallet, created_at__gte=month_start)
                .aggregate(t=Sum('transaction__amount'))['t'] or Decimal('0')
            )

        ctx = {
            'wallet':               wallet,
            'recent_transactions':  recent_transactions,
            'received_transfers':   received_transfers,
            'total_income':         total_income,
            'total_expense':        total_expense,
            'unread_count':         unread_count,
            'active_page':          'dashboard',
        }
        return render(request, 'wallet/dashboard.html', ctx)


class TransactionListView(LoginRequiredMixin, View):
    """GET /transactions/ — Full transaction history."""
    login_url = '/login/'

    def get(self, request):
        wallet = Wallet.objects.filter(user=request.user).first()
        transactions       = []
        received_transfers = []

        if wallet:
            transactions = (
                Transaction.objects
                .filter(wallet=wallet)
                .order_by('-created_at')
            )
            received_transfers = (
                Transfer.objects
                .filter(receiver_wallet=wallet)
                .select_related('transaction', 'sender_wallet__user')
                .order_by('-created_at')
            )

        ctx = {
            'wallet':               wallet,
            'transactions':         transactions,
            'received_transfers':   received_transfers,
            'active_page':          'transactions',
        }
        return render(request, 'wallet/transactions.html', ctx)


class SendMoneyView(LoginRequiredMixin, View):
    """GET/POST /send/ — Transfer money to another wallet by wallet number."""
    login_url = '/login/'
    template_name = 'wallet/send.html'

    def get(self, request):
        wallet = Wallet.objects.filter(user=request.user).first()
        return render(request, self.template_name, {
            'form': SendMoneyForm(), 'wallet': wallet, 'active_page': 'send',
        })

    def post(self, request):
        wallet = Wallet.objects.filter(user=request.user).first()
        form   = SendMoneyForm(request.POST)

        if not wallet:
            messages.error(request, 'You do not have a wallet yet.')
            return redirect('dashboard')

        if form.is_valid():
            d = form.cleaned_data
            try:
                recipient = Wallet.objects.get(wallet_number=d['recipient_wallet'])
            except Wallet.DoesNotExist:
                form.add_error('recipient_wallet', 'Wallet number not found.')
                return render(request, self.template_name, {'form': form, 'wallet': wallet, 'active_page': 'send'})

            if recipient.pk == wallet.pk:
                form.add_error('recipient_wallet', 'You cannot transfer to your own wallet.')
                return render(request, self.template_name, {'form': form, 'wallet': wallet, 'active_page': 'send'})

            if wallet.balance < d['amount']:
                form.add_error('amount', f'Insufficient balance. Available: {wallet.balance} {wallet.currency}')
                return render(request, self.template_name, {'form': form, 'wallet': wallet, 'active_page': 'send'})

            with db_transaction.atomic():
                tx = Transaction.objects.create(
                    wallet=wallet,
                    transaction_type='transfer',
                    amount=d['amount'],
                    status='completed',
                    description=d.get('description', ''),
                    reference=f'TRF-{uuid.uuid4().hex[:8].upper()}',
                )
                Transfer.objects.create(
                    transaction=tx,
                    sender_wallet=wallet,
                    receiver_wallet=recipient,
                )
                wallet.balance    -= d['amount']
                recipient.balance += d['amount']
                wallet.save()
                recipient.save()
                Notification.objects.create(
                    user=recipient.user,
                    transaction=tx,
                    title='Money Received',
                    message=f'You received {d["amount"]} {wallet.currency} from {request.user.full_name}.',
                )

            messages.success(request, f'Successfully sent {d["amount"]} {wallet.currency} to {recipient.wallet_number}!')
            return redirect('dashboard')

        return render(request, self.template_name, {'form': form, 'wallet': wallet, 'active_page': 'send'})


class TopupView(LoginRequiredMixin, View):
    """GET/POST /topup/ — Top up wallet balance."""
    login_url = '/login/'
    template_name = 'wallet/topup.html'

    def get(self, request):
        wallet = Wallet.objects.filter(user=request.user).first()
        return render(request, self.template_name, {
            'form': TopupForm(), 'wallet': wallet, 'active_page': 'topup',
        })

    def post(self, request):
        wallet = Wallet.objects.filter(user=request.user).first()
        form   = TopupForm(request.POST)

        if not wallet:
            messages.error(request, 'You do not have a wallet yet.')
            return redirect('dashboard')

        if form.is_valid():
            d = form.cleaned_data
            with db_transaction.atomic():
                tx = Transaction.objects.create(
                    wallet=wallet,
                    transaction_type='topup',
                    amount=d['amount'],
                    status='completed',
                    description=f'Top-up via {d["payment_method"]}',
                    reference=f'TOP-{uuid.uuid4().hex[:8].upper()}',
                )
                Topup.objects.create(
                    transaction=tx,
                    payment_method=d['payment_method'],
                )
                wallet.balance += d['amount']
                wallet.save()
                Notification.objects.create(
                    user=request.user,
                    transaction=tx,
                    title='Wallet Topped Up',
                    message=f'Your wallet has been credited with {d["amount"]} {wallet.currency}.',
                )

            messages.success(request, f'Wallet topped up with {d["amount"]} {wallet.currency}!')
            return redirect('dashboard')

        return render(request, self.template_name, {'form': form, 'wallet': wallet, 'active_page': 'topup'})


class ProfileView(LoginRequiredMixin, View):
    """GET/POST /profile/ — View & update profile, change password."""
    login_url = '/login/'
    template_name = 'wallet/profile.html'

    def get(self, request):
        profile_form  = ProfileUpdateForm(initial={
            'full_name': request.user.full_name,
            'phone':     request.user.phone,
        })
        password_form = ChangePasswordForm()
        return render(request, self.template_name, {
            'profile_form':  profile_form,
            'password_form': password_form,
            'active_page':   'profile',
        })

    def post(self, request):
        action = request.POST.get('action')
        profile_form  = ProfileUpdateForm(initial={'full_name': request.user.full_name, 'phone': request.user.phone})
        password_form = ChangePasswordForm()

        if action == 'update_profile':
            profile_form = ProfileUpdateForm(request.POST)
            if profile_form.is_valid():
                d = profile_form.cleaned_data
                request.user.full_name = d['full_name']
                request.user.phone     = d['phone']
                request.user.save()
                messages.success(request, 'Profile updated successfully!')
                return redirect('profile')

        elif action == 'change_password':
            password_form = ChangePasswordForm(request.POST)
            if password_form.is_valid():
                d = password_form.cleaned_data
                if not request.user.check_password(d['old_password']):
                    password_form.add_error('old_password', 'Current password is incorrect.')
                else:
                    request.user.set_password(d['new_password'])
                    request.user.save()
                    auth_login(request, request.user)  # keep session alive
                    messages.success(request, 'Password changed successfully!')
                    return redirect('profile')

        return render(request, self.template_name, {
            'profile_form':  profile_form,
            'password_form': password_form,
            'active_page':   'profile',
        })


# ─────────────────────────────────────────
#  AUTH VIEWS
# ─────────────────────────────────────────

class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    Register a new user. No authentication required.
    Auto-creates a KHR wallet for the user.
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'message': 'Registration successful.',
            'user': UserProfileSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    POST /api/auth/login/
    Login with email + password. Returns JWT tokens.
    No authentication required.
    """
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {'error': 'Email and password are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Authenticate using username=email (since we set username = email on register)
        user = authenticate(request, username=email, password=password)

        if user is None:
            return Response(
                {'error': 'Invalid email or password.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if user.status != 'active':
            return Response(
                {'error': 'Your account is inactive. Please contact support.'},
                status=status.HTTP_403_FORBIDDEN
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            'message': 'Login successful.',
            'user': UserProfileSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Blacklist the refresh token to log out.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Logged out successfully.'}, status=status.HTTP_200_OK)
        except Exception:
            return Response({'error': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)


class MeView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/auth/me/ — Get current user profile.
    PUT  /api/auth/me/ — Update current user profile (full_name, phone).
    PATCH /api/auth/me/ — Partial update.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """
    POST /api/auth/change-password/
    Change the authenticated user's password.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'error': 'Old password is incorrect.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({'message': 'Password changed successfully.'}, status=status.HTTP_200_OK)


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
