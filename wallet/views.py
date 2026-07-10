from rest_framework import viewsets, generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.conf import settings
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.views import View
from django.db import transaction as db_transaction
from django.db.models import Sum, Q
from django.utils import timezone
from decimal import Decimal
import os
import uuid
import random

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from .email_utils import (
    generate_reset_token,
    send_password_reset_email,
    send_password_reset_confirmation,
)


def _set_jwt_cookies(response, access_token, refresh_token=None):
    response.set_cookie(
        'access_token',
        access_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite='Lax',
        max_age=60 * 60,
    )
    if refresh_token:
        response.set_cookie(
            'refresh_token',
            refresh_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Lax',
            max_age=24 * 60 * 60,
        )
    return response

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
    generate_wallet_number,
)
from .forms import (
    LoginForm, RegisterForm, SendMoneyForm, TopupForm,
    ProfileUpdateForm, ChangePasswordForm, KYCVerificationForm,
    WalletManagementForm, UpdateWalletForm, ChangePinForm,
    ForgotPasswordForm, ResetPasswordForm
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
                auth_login(request, user)
                messages.success(request, f'Welcome, {user.full_name}! Please create your new E-wallet to continue.')
                return redirect('create_wallet')
        return render(request, self.template_name, {'form': form})


class LogoutPageView(View):
    """POST /logout/ — Logs out and redirects to login."""
    def post(self, request):
        auth_logout(request)
        return redirect('login')


class ForgotPasswordView(View):
    """GET/POST /forgot-password/ — Request password reset via email."""
    template_name = 'wallet/forgot_password.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return render(request, self.template_name, {'form': ForgotPasswordForm()})

    def post(self, request):
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                # Generate reset token
                token = generate_reset_token()
                user.password_reset_token = token
                user.password_reset_sent_at = timezone.now()
                user.save()

                # Build reset URL
                reset_url = request.build_absolute_uri(
                    reverse('reset-password') + f'?token={token}'
                )

                # Send email via Resend
                result = send_password_reset_email(user, reset_url)

                if result['success']:
                    messages.success(request, 'Password reset link has been sent to your email.')
                    return redirect('login')
                else:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to send reset email: {result.get('error', 'Unknown error')}")
                    messages.error(request, f"Failed to send reset email: {result.get('error', 'Please try again later.')}")
            except User.DoesNotExist:
                # Don't reveal if email exists
                messages.success(request, 'Password reset link has been sent to your email.')
                return redirect('login')

        return render(request, self.template_name, {'form': form})


class ResetPasswordView(View):
    """GET/POST /reset-password/ — Reset password using token."""
    template_name = 'wallet/reset_password.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')

        token = request.GET.get('token')
        if not token:
            messages.error(request, 'Invalid reset link.')
            return redirect('login')

        # Validate token
        try:
            user = User.objects.get(password_reset_token=token)
            # Check if token is expired (1 hour)
            if user.password_reset_sent_at:
                time_diff = timezone.now() - user.password_reset_sent_at
                if time_diff.total_seconds() > 3600:
                    messages.error(request, 'Reset link has expired. Please request a new one.')
                    return redirect('forgot-password')
        except User.DoesNotExist:
            messages.error(request, 'Invalid reset link.')
            return redirect('login')

        return render(request, self.template_name, {'form': ResetPasswordForm(), 'token': token})

    def post(self, request):
        token = request.POST.get('token')
        if not token:
            messages.error(request, 'Invalid reset link.')
            return redirect('login')

        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            try:
                user = User.objects.get(password_reset_token=token)
                # Check if token is expired
                if user.password_reset_sent_at:
                    time_diff = timezone.now() - user.password_reset_sent_at
                    if time_diff.total_seconds() > 3600:
                        messages.error(request, 'Reset link has expired. Please request a new one.')
                        return redirect('forgot-password')

                # Set new password
                user.set_password(form.cleaned_data['new_password'])
                user.password_reset_token = None
                user.password_reset_sent_at = None
                user.save()

                # Send confirmation email
                send_password_reset_confirmation(user)

                messages.success(request, 'Password has been reset successfully. Please log in.')
                return redirect('login')

            except User.DoesNotExist:
                messages.error(request, 'Invalid reset link.')
                return redirect('login')

        return render(request, self.template_name, {'form': form, 'token': token})


class DashboardView(LoginRequiredMixin, View):
    """GET / — Main dashboard."""
    login_url = '/login/'

    def get(self, request):
        wallet = Wallet.objects.filter(user=request.user).first()
        verification = IdentityVerification.objects.filter(user=request.user).first()
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
            'verification':         verification,
            'recent_transactions':  recent_transactions,
            'received_transfers':   received_transfers,
            'total_income':         total_income,
            'total_expense':        total_expense,
            'unread_count':         unread_count,
            'topup_success_speech': request.session.pop('topup_success_speech', ''),
            'active_page':          'dashboard',
        }
        return render(request, 'wallet/dashboard.html', ctx)


class AccountsView(LoginRequiredMixin, View):
    """GET /accounts/ — View all user accounts/wallets with balances."""
    login_url = '/login/'
    template_name = 'wallet/accounts.html'

    def get(self, request):
        wallets = Wallet.objects.filter(user=request.user).order_by('created_at')
        total_balance = wallets.aggregate(total=Sum('balance'))['total'] or Decimal('0')

        ctx = {
            'wallets': wallets,
            'total_balance': total_balance,
            'active_page': 'accounts',
        }
        return render(request, self.template_name, ctx)


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


class CreateWalletView(LoginRequiredMixin, View):
    """GET/POST /create-wallet/ — Create a wallet for the authenticated user."""
    login_url = '/login/'
    template_name = 'wallet/create_wallet.html'

    def get(self, request):
        verification = IdentityVerification.objects.filter(user=request.user).first()
        is_kyc_verified = bool(verification and verification.verification_status == 'verified')

        existing_wallets = Wallet.objects.filter(user=request.user).order_by('created_at')
        wallet = existing_wallets.first()
        if not is_kyc_verified:
            messages.warning(request, 'KYC verification is required before creating a wallet. Please complete your KYC first.')
            return redirect('kyc')

        if existing_wallets.count() >= 5:
            messages.info(request, 'Wallet creation limit reached. You can create up to 5 wallets.')
            return render(request, self.template_name, {
                'active_page': 'create_wallet',
                'existing_wallets': existing_wallets,
                'can_create_separate': False,
            })
        if wallet and existing_wallets.count() >= 1:
            return render(request, self.template_name, {
                'active_page': 'create_wallet',
                'existing_wallets': existing_wallets,
                'can_create_separate': True,
            })
        return render(request, self.template_name, {'active_page': 'create_wallet', 'existing_wallets': existing_wallets})

    def post(self, request):
        verification = IdentityVerification.objects.filter(user=request.user).first()
        is_kyc_verified = bool(verification and verification.verification_status == 'verified')
        if not is_kyc_verified:
            messages.error(request, 'KYC verification is required before creating a wallet. Please complete your KYC first.')
            return redirect('kyc')

        wallet_type = request.POST.get('wallet_type', 'primary')
        existing_wallets = Wallet.objects.filter(user=request.user).order_by('created_at')
        if existing_wallets.count() >= 5:
            messages.error(request, 'Wallet creation limit exceeded. You can create up to 5 wallets.')
            return render(request, self.template_name, {
                'active_page': 'create_wallet',
                'existing_wallets': existing_wallets,
                'can_create_separate': existing_wallets.count() == 1,
            })

        if existing_wallets.exists() and wallet_type != 'separate':
            messages.info(request, 'You already have a wallet. Choose the separate option to create another one.')
            return render(request, self.template_name, {
                'active_page': 'create_wallet',
                'existing_wallets': existing_wallets,
                'can_create_separate': True,
            })

        wallet = Wallet.objects.create(
            user=request.user,
            wallet_number=generate_wallet_number(request.user),
            currency='KHR',
        )
        messages.success(request, f'Wallet created successfully! Your wallet number is {wallet.wallet_number}.')
        return redirect('dashboard')


class WalletManagementView(LoginRequiredMixin, View):
    """GET/POST /wallet-management/ — Manage wallet (view balance, freeze, close, etc.)."""
    login_url = '/login/'
    template_name = 'wallet/wallet_management.html'

    def get(self, request):
        wallets = Wallet.objects.filter(user=request.user).order_by('created_at')
        if not wallets.exists():
            messages.warning(request, 'You do not have a wallet. Please create one first.')
            return redirect('create_wallet')

        selected_wallet_id = request.GET.get('wallet_id')
        wallet = wallets.filter(id=selected_wallet_id).first() if selected_wallet_id else wallets.first()
        if not wallet:
            wallet = wallets.first()

        action = request.GET.get('action', 'select')
        form = UpdateWalletForm(initial={'currency': wallet.currency}) if action == 'update_info' else WalletManagementForm()
        ctx = {
            'wallet': wallet,
            'wallets': wallets,
            'selected_wallet_id': wallet.id,
            'action': action,
            'form': form,
            'active_page': 'wallet_management',
        }
        return render(request, self.template_name, ctx)

    def post(self, request):
        selected_wallet_id = request.POST.get('wallet_id') or request.GET.get('wallet_id')
        wallets = Wallet.objects.filter(user=request.user).order_by('created_at')
        wallet = wallets.filter(id=selected_wallet_id).first() if selected_wallet_id else wallets.first()
        if not wallet:
            wallet = wallets.first()
        if not wallet:
            messages.error(request, 'You do not have a wallet.')
            return redirect('create_wallet')

        action = request.POST.get('action')

        if action == 'update_info':
            form = UpdateWalletForm(request.POST or None, initial={'currency': wallet.currency})
            if request.method == 'POST' and form.is_valid():
                wallet.currency = form.cleaned_data['currency']
                wallet.save()
                messages.success(request, 'Wallet information updated successfully.')
                return redirect(f"{reverse('wallet_management')}?wallet_id={wallet.id}")
            ctx = {
                'wallet': wallet,
                'wallets': wallets,
                'selected_wallet_id': wallet.id,
                'action': 'update_info',
                'form': form,
                'active_page': 'wallet_management',
            }
            return render(request, self.template_name, ctx)

        elif action == 'freeze':
            if wallet.status == 'frozen':
                messages.info(request, 'Wallet is already frozen.')
            else:
                wallet.status = 'frozen'
                wallet.save()
                messages.success(request, 'Wallet has been frozen successfully.')
            return redirect(f"{reverse('wallet_management')}?wallet_id={wallet.id}")

        elif action == 'unfreeze':
            if wallet.status == 'active':
                messages.info(request, 'Wallet is already active.')
            else:
                wallet.status = 'active'
                wallet.save()
                messages.success(request, 'Wallet has been unfrozen successfully.')
            return redirect(f"{reverse('wallet_management')}?wallet_id={wallet.id}")

        elif action == 'close':
            if wallet.balance != Decimal('0.00'):
                messages.error(request, 'Wallet cannot be closed while it still has a balance. Please transfer or withdraw the balance first.')
            else:
                wallet.status = 'closed'
                wallet.save()
                messages.success(request, 'Wallet has been closed successfully.')
            return redirect(f"{reverse('wallet_management')}?wallet_id={wallet.id}")

        elif action == 'reopen':
            if wallet.status == 'closed':
                wallet.status = 'active'
                wallet.save()
                messages.success(request, 'Wallet has been reopened successfully.')
            elif wallet.status == 'active':
                messages.info(request, 'Wallet is already active.')
            else:
                messages.info(request, f'Wallet is currently {wallet.status}.')
            return redirect(f"{reverse('wallet_management')}?wallet_id={wallet.id}")


        return redirect('wallet_management')


class SendMoneyView(LoginRequiredMixin, View):
    """GET/POST /send/ — Transfer money to another wallet by wallet number with PIN and OTP verification."""
    login_url = '/login/'
    template_name = 'wallet/send.html'

    def get(self, request):
        wallet = Wallet.objects.filter(user=request.user).first()
        verification = IdentityVerification.objects.filter(user=request.user).first()
        kyc_verified = verification and verification.verification_status == 'verified'
        security, _ = Security.objects.get_or_create(user=request.user)
        has_pin = bool(security.pin_hash)

        if not kyc_verified:
            messages.warning(request, 'KYC verification is required to send money. Please complete your KYC verification.')
        elif not has_pin:
            messages.warning(request, 'You must set up a transaction PIN in your profile settings before sending money.')

        return render(request, self.template_name, {
            'form': SendMoneyForm(),
            'wallet': wallet,
            'kyc_verified': kyc_verified,
            'has_pin': has_pin,
            'otp_required': security.otp_enabled,
            'otp_challenge': False,
            'active_page': 'send',
        })

    def post(self, request):
        wallet = Wallet.objects.filter(user=request.user).first()
        form   = SendMoneyForm(request.POST)

        # Check KYC verification status
        verification = IdentityVerification.objects.filter(user=request.user).first()
        kyc_verified = verification and verification.verification_status == 'verified'
        security, _ = Security.objects.get_or_create(user=request.user)
        has_pin = bool(security.pin_hash)

        if not kyc_verified:
            messages.error(request, 'KYC verification is required to send money. Please complete your KYC verification.')
            return render(request, self.template_name, {
                'form': form, 'wallet': wallet, 'kyc_verified': kyc_verified, 'has_pin': has_pin, 'otp_required': security.otp_enabled, 'otp_challenge': False, 'active_page': 'send'
            })

        if not has_pin:
            messages.error(request, 'You must set up a transaction PIN in your profile settings before sending money.')
            return redirect('profile')

        if not wallet:
            messages.error(request, 'You do not have a wallet yet.')
            return redirect('dashboard')

        if form.is_valid():
            d = form.cleaned_data
            
            # 1. Verify PIN
            from django.contrib.auth.hashers import check_password
            if not check_password(d['pin'], security.pin_hash):
                form.add_error('pin', 'Invalid transaction PIN.')
                return render(request, self.template_name, {
                    'form': form, 'wallet': wallet, 'kyc_verified': kyc_verified, 'has_pin': has_pin, 'otp_required': security.otp_enabled, 'otp_challenge': False, 'active_page': 'send'
                })

            # 2. Verify OTP if enabled
            if security.otp_enabled:
                otp_code = d.get('otp_code')
                if not otp_code:
                    # Generate and send OTP
                    import random
                    otp = str(random.randint(100000, 999999))
                    security.temp_otp = otp
                    security.temp_otp_expiry = timezone.now() + timezone.timedelta(minutes=5)
                    security.save()

                    Notification.objects.create(
                        user=request.user,
                        title='Transfer OTP Code',
                        message=f'Your OTP code for sending money is: {otp}',
                    )
                    messages.info(request, 'An OTP has been generated. Please check your notifications to verify.')
                    
                    return render(request, self.template_name, {
                        'form': form,
                        'wallet': wallet,
                        'kyc_verified': kyc_verified,
                        'has_pin': has_pin,
                        'otp_required': True,
                        'otp_challenge': True,
                        'active_page': 'send',
                    })
                
                # If OTP code is submitted, verify it
                if security.temp_otp != otp_code or security.temp_otp_expiry < timezone.now():
                    form.add_error('otp_code', 'Invalid or expired OTP code.')
                    return render(request, self.template_name, {
                        'form': form,
                        'wallet': wallet,
                        'kyc_verified': kyc_verified,
                        'has_pin': has_pin,
                        'otp_required': True,
                        'otp_challenge': True,
                        'active_page': 'send',
                    })

            # Clear temporary OTP once validation succeeds
            if security.otp_enabled:
                security.temp_otp = None
                security.temp_otp_expiry = None
                security.save()

            try:
                recipient = Wallet.objects.get(wallet_number=d['recipient_wallet'])
            except Wallet.DoesNotExist:
                form.add_error('recipient_wallet', 'Wallet number not found.')
                return render(request, self.template_name, {
                    'form': form, 'wallet': wallet, 'kyc_verified': kyc_verified, 'has_pin': has_pin, 'otp_required': security.otp_enabled, 'otp_challenge': False, 'active_page': 'send'
                })

            if recipient.pk == wallet.pk:
                form.add_error('recipient_wallet', 'You cannot transfer to your own wallet.')
                return render(request, self.template_name, {
                    'form': form, 'wallet': wallet, 'kyc_verified': kyc_verified, 'has_pin': has_pin, 'otp_required': security.otp_enabled, 'otp_challenge': False, 'active_page': 'send'
                })

            if wallet.balance < d['amount']:
                form.add_error('amount', f'Insufficient balance. Available: {wallet.balance} {wallet.currency}')
                return render(request, self.template_name, {
                    'form': form, 'wallet': wallet, 'kyc_verified': kyc_verified, 'has_pin': has_pin, 'otp_required': security.otp_enabled, 'otp_challenge': False, 'active_page': 'send'
                })

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
                Notification.objects.create(
                    user=request.user,
                    transaction=tx,
                    title='Money Sent',
                    message=f'You sent {d["amount"]} {wallet.currency} to {recipient.user.full_name}.',
                )

            messages.success(request, f'Successfully sent {d["amount"]} {wallet.currency} to {recipient.wallet_number}!')
            return redirect('dashboard')

        return render(request, self.template_name, {
            'form': form, 'wallet': wallet, 'kyc_verified': kyc_verified, 'has_pin': has_pin, 'otp_required': security.otp_enabled, 'otp_challenge': False, 'active_page': 'send'
        })


class TopupView(LoginRequiredMixin, View):
    """GET/POST /topup/ — Top up wallet balance."""
    login_url = '/login/'
    template_name = 'wallet/topup.html'
    fee_amount = Decimal('0')

    def _create_submission_token(self, request):
        token = uuid.uuid4().hex
        request.session['topup_submission_token'] = token
        return token

    def get(self, request):
        wallet = Wallet.objects.filter(user=request.user).first()
        return render(request, self.template_name, {
            'form': TopupForm(),
            'wallet': wallet,
            'active_page': 'topup',
            'transaction_fee': self.fee_amount,
            'submission_token': self._create_submission_token(request),
        })

    def post(self, request):
        wallet = Wallet.objects.filter(user=request.user).first()
        form   = TopupForm(request.POST)

        if not wallet:
            messages.error(request, 'You do not have a wallet yet.')
            return redirect('dashboard')

        if form.is_valid():
            submitted_token = request.POST.get('submission_token')
            session_token = request.session.get('topup_submission_token')
            if not submitted_token or submitted_token != session_token:
                messages.error(request, 'This top up request was already submitted. Please create a new one.')
                return redirect('topup')

            request.session.pop('topup_submission_token', None)
            d = form.cleaned_data
            payment_label = dict(TopupForm.PAYMENT_CHOICES).get(d['payment_method'], d['payment_method'])
            with db_transaction.atomic():
                tx = Transaction.objects.create(
                    wallet=wallet,
                    transaction_type='topup',
                    amount=d['amount'],
                    status='completed',
                    description=f'Top-up via {payment_label}',
                    reference=f'TOP-{uuid.uuid4().hex[:8].upper()}',
                )
                Topup.objects.create(
                    transaction=tx,
                    payment_method=d['payment_method'],
                    provider=payment_label,
                )
                wallet.balance += d['amount']
                wallet.save()
                Notification.objects.create(
                    user=request.user,
                    transaction=tx,
                    title='Wallet Topped Up',
                    message=f'Your wallet has been credited with {d["amount"]} {wallet.currency}.',
                )

            success_message = f'ការបញ្ចូលលុយបានជោគជ័យ ចំនួន {d["amount"]} {wallet.currency}!'
            request.session['topup_success_speech'] = success_message
            messages.success(request, success_message)
            return redirect('dashboard')

        return render(request, self.template_name, {
            'form': form,
            'wallet': wallet,
            'active_page': 'topup',
            'transaction_fee': self.fee_amount,
            'submission_token': request.session.get('topup_submission_token') or self._create_submission_token(request),
        })


class ProfileView(LoginRequiredMixin, View):
    """GET/POST /profile/ — View & update profile, change password, manage security PIN and OTP."""
    login_url = '/login/'
    template_name = 'wallet/profile.html'

    def get(self, request):
        security, _ = Security.objects.get_or_create(user=request.user)
        profile_form  = ProfileUpdateForm(initial={
            'full_name': request.user.full_name,
            'phone':     request.user.phone,
        })
        password_form = ChangePasswordForm()
        pin_form = ChangePinForm(has_pin=bool(security.pin_hash))
        return render(request, self.template_name, {
            'profile_form':  profile_form,
            'password_form': password_form,
            'pin_form':      pin_form,
            'security':      security,
            'active_page':   'profile',
        })

    def post(self, request):
        action = request.POST.get('action')
        security, _ = Security.objects.get_or_create(user=request.user)
        profile_form  = ProfileUpdateForm(initial={'full_name': request.user.full_name, 'phone': request.user.phone})
        password_form = ChangePasswordForm()
        pin_form = ChangePinForm(has_pin=bool(security.pin_hash))

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

        elif action == 'change_pin':
            pin_form = ChangePinForm(request.POST, has_pin=bool(security.pin_hash))
            if pin_form.is_valid():
                d = pin_form.cleaned_data
                from django.contrib.auth.hashers import make_password, check_password
                if security.pin_hash:
                    if not check_password(d['old_pin'], security.pin_hash):
                        pin_form.add_error('old_pin', 'Current PIN is incorrect.')
                        return render(request, self.template_name, {
                            'profile_form':  profile_form,
                            'password_form': password_form,
                            'pin_form':      pin_form,
                            'security':      security,
                            'active_page':   'profile',
                        })
                security.pin_hash = make_password(d['new_pin'])
                security.save()
                messages.success(request, 'Transaction PIN updated successfully!')
                return redirect('profile')

        elif action == 'toggle_security':
            otp_enabled = request.POST.get('otp_enabled') == 'on'
            security.otp_enabled = otp_enabled
            security.two_factor_enabled = otp_enabled
            security.save()
            messages.success(request, f"OTP validation {'enabled' if otp_enabled else 'disabled'} successfully!")
            return redirect('profile')

        return render(request, self.template_name, {
            'profile_form':  profile_form,
            'password_form': password_form,
            'pin_form':      pin_form,
            'security':      security,
            'active_page':   'profile',
        })


class UserReportsView(LoginRequiredMixin, View):
    """GET /reports/ — View daily, monthly, and annual transaction reports."""
    login_url = '/login/'
    template_name = 'wallet/reports.html'

    def get(self, request):
        wallet = Wallet.objects.filter(user=request.user).first()
        report_type = request.GET.get('report_type', 'daily')
        selected_date = request.GET.get('date')
        selected_month = request.GET.get('month')
        selected_year = request.GET.get('year')

        from datetime import datetime, timedelta
        from django.db.models import Sum, Count
        from django.db.models.functions import TruncDate, TruncMonth, TruncYear

        context = {
            'wallet': wallet,
            'report_type': report_type,
            'active_page': 'reports',
        }

        if not wallet:
            context['no_wallet'] = True
            return render(request, self.template_name, context)

        # Get user's wallet IDs for filtering
        user_wallet_ids = Wallet.objects.filter(user=request.user).values_list('id', flat=True)

        # Daily Report
        if report_type == 'daily':
            if selected_date:
                try:
                    report_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
                except ValueError:
                    report_date = timezone.now().date()
            else:
                report_date = timezone.now().date()

            # Get all transactions for this day (sent from user's wallets + received by user's wallets)
            sent_transactions = Transaction.objects.filter(
                wallet__in=user_wallet_ids,
                created_at__date=report_date
            ).select_related('wallet', 'merchant', 'biller').order_by('-created_at')

            # Received transfers
            received_transfers = Transfer.objects.filter(
                receiver_wallet__in=user_wallet_ids,
                created_at__date=report_date
            ).select_related('transaction', 'sender_wallet__user').order_by('-created_at')

            # Calculate totals
            total_sent = Transaction.objects.filter(
                wallet__in=user_wallet_ids,
                transaction_type='transfer',
                created_at__date=report_date
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

            total_topup = Transaction.objects.filter(
                wallet__in=user_wallet_ids,
                transaction_type='topup',
                created_at__date=report_date
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

            total_received = Transfer.objects.filter(
                receiver_wallet__in=user_wallet_ids,
                created_at__date=report_date
            ).aggregate(total=Sum('transaction__amount'))['total'] or Decimal('0')

            # Count by type
            transaction_counts = Transaction.objects.filter(
                wallet__in=user_wallet_ids,
                created_at__date=report_date
            ).values('transaction_type').annotate(
                count=Count('id'),
                total=Sum('amount')
            ).order_by('transaction_type')

            context.update({
                'report_date': report_date,
                'sent_transactions': sent_transactions,
                'received_transfers': received_transfers,
                'total_sent': total_sent,
                'total_topup': total_topup,
                'total_received': total_received,
                'transaction_counts': transaction_counts,
                'net_flow': total_received + total_topup - total_sent,
            })

        # Monthly Report
        elif report_type == 'monthly':
            if selected_month:
                try:
                    report_month = datetime.strptime(selected_month, '%Y-%m').date()
                except ValueError:
                    report_month = timezone.now().date().replace(day=1)
            else:
                report_month = timezone.now().date().replace(day=1)

            month_start = report_month.replace(day=1)
            if report_month.month == 12:
                month_end = report_month.replace(year=report_month.year + 1, month=1, day=1)
            else:
                month_end = report_month.replace(month=report_month.month + 1, day=1)

            # Daily breakdown for the month
            daily_breakdown = Transaction.objects.filter(
                wallet__in=user_wallet_ids,
                created_at__date__gte=month_start,
                created_at__date__lt=month_end
            ).annotate(
                day=TruncDate('created_at')
            ).values('day').annotate(
                count=Count('id'),
                total_sent=Sum('amount', filter=Q(transaction_type='transfer')),
                total_topup=Sum('amount', filter=Q(transaction_type='topup')),
            ).order_by('day')

            # Received transfers by day
            received_by_day = Transfer.objects.filter(
                receiver_wallet__in=user_wallet_ids,
                created_at__date__gte=month_start,
                created_at__date__lt=month_end
            ).annotate(
                day=TruncDate('created_at')
            ).values('day').annotate(
                total_received=Sum('transaction__amount'),
                count=Count('id')
            ).order_by('day')

            # Monthly totals
            monthly_sent = Transaction.objects.filter(
                wallet__in=user_wallet_ids,
                transaction_type='transfer',
                created_at__date__gte=month_start,
                created_at__date__lt=month_end
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

            monthly_topup = Transaction.objects.filter(
                wallet__in=user_wallet_ids,
                transaction_type='topup',
                created_at__date__gte=month_start,
                created_at__date__lt=month_end
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

            monthly_received = Transfer.objects.filter(
                receiver_wallet__in=user_wallet_ids,
                created_at__date__gte=month_start,
                created_at__date__lt=month_end
            ).aggregate(total=Sum('transaction__amount'))['total'] or Decimal('0')

            # Transaction type summary
            transaction_types = Transaction.objects.filter(
                wallet__in=user_wallet_ids,
                created_at__date__gte=month_start,
                created_at__date__lt=month_end
            ).values('transaction_type').annotate(
                count=Count('id'),
                total=Sum('amount')
            ).order_by('transaction_type')

            context.update({
                'report_month': report_month,
                'daily_breakdown': daily_breakdown,
                'received_by_day': received_by_day,
                'monthly_sent': monthly_sent,
                'monthly_topup': monthly_topup,
                'monthly_received': monthly_received,
                'monthly_net': monthly_received + monthly_topup - monthly_sent,
                'transaction_types': transaction_types,
            })

        # Annual Report
        elif report_type == 'annual':
            if selected_year:
                try:
                    report_year = int(selected_year)
                except ValueError:
                    report_year = timezone.now().year
            else:
                report_year = timezone.now().year

            year_start = datetime(report_year, 1, 1).date()
            year_end = datetime(report_year + 1, 1, 1).date()

            # Monthly breakdown for the year
            monthly_breakdown = Transaction.objects.filter(
                wallet__in=user_wallet_ids,
                created_at__date__gte=year_start,
                created_at__date__lt=year_end
            ).annotate(
                month=TruncMonth('created_at')
            ).values('month').annotate(
                count=Count('id'),
                total_sent=Sum('amount', filter=Q(transaction_type='transfer')),
                total_topup=Sum('amount', filter=Q(transaction_type='topup')),
            ).order_by('month')

            # Received transfers by month
            received_by_month = Transfer.objects.filter(
                receiver_wallet__in=user_wallet_ids,
                created_at__date__gte=year_start,
                created_at__date__lt=year_end
            ).annotate(
                month=TruncMonth('created_at')
            ).values('month').annotate(
                total_received=Sum('transaction__amount'),
                count=Count('id')
            ).order_by('month')

            # Annual totals
            annual_sent = Transaction.objects.filter(
                wallet__in=user_wallet_ids,
                transaction_type='transfer',
                created_at__date__gte=year_start,
                created_at__date__lt=year_end
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

            annual_topup = Transaction.objects.filter(
                wallet__in=user_wallet_ids,
                transaction_type='topup',
                created_at__date__gte=year_start,
                created_at__date__lt=year_end
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

            annual_received = Transfer.objects.filter(
                receiver_wallet__in=user_wallet_ids,
                created_at__date__gte=year_start,
                created_at__date__lt=year_end
            ).aggregate(total=Sum('transaction__amount'))['total'] or Decimal('0')

            # Quarter summary
            quarter_totals = []
            for q in range(1, 5):
                q_start = datetime(report_year, (q - 1) * 3 + 1, 1).date()
                q_end = datetime(report_year, q * 3 + 1 if q < 4 else 1, 1).date() if q < 4 else datetime(report_year + 1, 1, 1).date()

                q_sent = Transaction.objects.filter(
                    wallet__in=user_wallet_ids,
                    transaction_type='transfer',
                    created_at__date__gte=q_start,
                    created_at__date__lt=q_end
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

                q_topup = Transaction.objects.filter(
                    wallet__in=user_wallet_ids,
                    transaction_type='topup',
                    created_at__date__gte=q_start,
                    created_at__date__lt=q_end
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

                q_received = Transfer.objects.filter(
                    receiver_wallet__in=user_wallet_ids,
                    created_at__date__gte=q_start,
                    created_at__date__lt=q_end
                ).aggregate(total=Sum('transaction__amount'))['total'] or Decimal('0')

                quarter_totals.append({
                    'quarter': f'Q{q}',
                    'sent': q_sent,
                    'topup': q_topup,
                    'received': q_received,
                    'net': q_received + q_topup - q_sent,
                })

            context.update({
                'report_year': report_year,
                'monthly_breakdown': monthly_breakdown,
                'received_by_month': received_by_month,
                'annual_sent': annual_sent,
                'annual_topup': annual_topup,
                'annual_received': annual_received,
                'annual_net': annual_received + annual_topup - annual_sent,
                'quarter_totals': quarter_totals,
            })

        return render(request, self.template_name, context)


class AdminRequiredMixin(LoginRequiredMixin):
    login_url = '/login/'

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'admin'):
            raise PermissionDenied('You do not have permission to access this page.')
        return super().dispatch(request, *args, **kwargs)


class KYCVerificationView(LoginRequiredMixin, View):
    """GET/POST /kyc/ — KYC document submission and status."""
    login_url = '/login/'
    template_name = 'wallet/kyc.html'

    def get(self, request):
        verification, _ = IdentityVerification.objects.get_or_create(user=request.user)
        initial = {
            'full_name':     request.user.full_name,
            'date_of_birth': verification.date_of_birth,
            'address':       verification.address,
            'nationality':   verification.nationality,
            'national_id':   verification.national_id,
        }
        form = KYCVerificationForm(initial=initial)
        return render(request, self.template_name, {
            'form': form,
            'verification': verification,
            'active_page': 'kyc',
        })

    def post(self, request):
        verification, _ = IdentityVerification.objects.get_or_create(user=request.user)
        form = KYCVerificationForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            d = form.cleaned_data
            request.user.full_name = d['full_name']
            request.user.save()
            id_document = d['id_document']
            
            try:
                # Handle ID document
                id_path = default_storage.save(
                    f'kyc/{request.user.id}/id_document_{uuid.uuid4().hex[:8]}.{id_document.name.split(".")[-1]}',
                    id_document
                )
                
                # Handle selfie - either from file upload or camera capture
                selfie_image = d.get('selfie_image')
                selfie_image_data = request.POST.get('selfie_image_data')
                
                if selfie_image:
                    # File upload
                    selfie_path = default_storage.save(
                        f'kyc/{request.user.id}/selfie_{uuid.uuid4().hex[:8]}.{selfie_image.name.split(".")[-1]}',
                        selfie_image
                    )
                elif selfie_image_data:
                    # Camera capture - base64 data
                    import base64
                    from django.core.files.base import ContentFile
                    
                    # Remove the data URL prefix if present
                    if ';base64,' in selfie_image_data:
                        format, imgstr = selfie_image_data.split(';base64,')
                        ext = format.split('/')[-1] if '/' in format else 'jpg'
                    else:
                        imgstr = selfie_image_data
                        ext = 'jpg'
                    
                    # Decode base64 and save
                    image_data = base64.b64decode(imgstr)
                    file_name = f'selfie_{uuid.uuid4().hex[:8]}.{ext}'
                    selfie_path = default_storage.save(
                        f'kyc/{request.user.id}/{file_name}',
                        ContentFile(image_data)
                    )
                else:
                    form.add_error('selfie_image', 'Please provide a selfie image.')
                    return render(request, self.template_name, {
                        'form': form,
                        'verification': verification,
                        'active_page': 'kyc',
                    })
                
                verification.date_of_birth = d['date_of_birth']
                verification.address = d['address']
                verification.nationality = d['nationality']
                verification.national_id = d['national_id']
                verification.id_document = id_path
                verification.selfie_image = selfie_path
                verification.verification_status = 'pending'
                verification.verified_at = None
                verification.save()
                messages.success(request, 'KYC documents submitted successfully. Verification is pending.')
                return redirect('kyc')
            except Exception:
                form.add_error('national_id', 'This National ID is already registered with another account.')

        return render(request, self.template_name, {
            'form': form,
            'verification': verification,
            'active_page': 'kyc',
        })


class KYCReviewView(AdminRequiredMixin, View):
    """GET/POST /kyc-review/ — Admin-only KYC approval and rejection."""
    template_name = 'wallet/kyc_review.html'

    def get(self, request):
        submission_id = request.GET.get('submission')
        status_filter = request.GET.get('status', 'all')

        # Filter by status
        queryset = IdentityVerification.objects.all()
        if status_filter == 'pending':
            queryset = queryset.filter(verification_status='pending')
        elif status_filter == 'verified':
            queryset = queryset.filter(verification_status='verified')
        elif status_filter == 'rejected':
            queryset = queryset.filter(verification_status='rejected')

        submissions = queryset.order_by('-created_at')

        # Get single submission for detail view
        selected_submission = None
        if submission_id:
            try:
                selected_submission = IdentityVerification.objects.get(id=submission_id)
            except IdentityVerification.DoesNotExist:
                pass

        return render(request, self.template_name, {
            'submissions': submissions,
            'selected_submission': selected_submission,
            'status_filter': status_filter,
            'active_page': 'kyc_review',
        })

    def post(self, request):
        action = request.POST.get('action')
        submission_id = request.POST.get('submission_id')
        rejection_reason = request.POST.get('rejection_reason', '').strip()

        if not submission_id:
            messages.error(request, 'No submission selected.')
            return redirect('kyc_review')

        try:
            verification = IdentityVerification.objects.get(id=submission_id)
        except IdentityVerification.DoesNotExist:
            messages.error(request, 'Submission not found.')
            return redirect('kyc_review')

        if action == 'approve':
            if verification.verification_status != 'verified':
                verification.verification_status = 'verified'
                verification.verified_at = timezone.now()
                verification.rejection_reason = None  # Clear any previous rejection reason
                verification.save(update_fields=['verification_status', 'verified_at', 'rejection_reason'])
                Notification.objects.create(
                    user=verification.user,
                    title='KYC Verified',
                    message='Your identity verification has been approved. You can now send money and use all wallet features.',
                )
                messages.success(request, f'KYC for {verification.user.full_name} has been approved.')
            else:
                messages.info(request, 'This submission is already approved.')

        elif action == 'reject':
            if not rejection_reason:
                messages.error(request, 'Please provide a rejection reason.')
                return redirect(f'{request.path}?submission={submission_id}')

            if verification.verification_status != 'rejected':
                verification.verification_status = 'rejected'
                verification.verified_at = None
                verification.rejection_reason = rejection_reason
                verification.save(update_fields=['verification_status', 'verified_at', 'rejection_reason'])
                Notification.objects.create(
                    user=verification.user,
                    title='KYC Rejected',
                    message=f'Your identity verification has been rejected. Reason: {rejection_reason}',
                )
                messages.success(request, f'KYC for {verification.user.full_name} has been rejected.')
            else:
                messages.info(request, 'This submission is already rejected.')

        return redirect('kyc_review')


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
        response = Response({
            'message': 'Registration successful.',
            'user': UserProfileSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)
        _set_jwt_cookies(response, str(refresh.access_token), str(refresh))
        return response


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
        response = Response({
            'message': 'Login successful.',
            'user': UserProfileSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)
        _set_jwt_cookies(response, str(refresh.access_token), str(refresh))
        return response


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Blacklist the refresh token and clear JWT cookies.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
            response = Response({'message': 'Logged out successfully.'}, status=status.HTTP_200_OK)
            response.delete_cookie('access_token')
            response.delete_cookie('refresh_token')
            return response
        except Exception:
            return Response({'error': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)


class AuthTokenRefreshView(TokenRefreshView):
    """POST /api/auth/token/refresh/ — Refresh access token and update cookies."""

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            refresh = request.data.get('refresh')
            access_token = response.data.get('access')
            _set_jwt_cookies(response, access_token, refresh)
        return response


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
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # Check if user has verified KYC
        verification = IdentityVerification.objects.filter(user=request.user).first()
        if not (verification and verification.verification_status == 'verified'):
            return Response(
                {'error': 'KYC verification is required to create transfers. Please complete your KYC verification.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)


class PeerToPeerTransferView(APIView):
    """
    POST /api/transfers/p2p/
    Transfer money from authenticated user's wallet to another wallet.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        sender_wallet_id = request.data.get('sender_wallet_id')
        recipient_wallet_number = request.data.get('recipient_wallet_number')
        amount = request.data.get('amount')
        description = request.data.get('description', '')

        # Verify Security Settings (PIN and OTP)
        security, _ = Security.objects.get_or_create(user=request.user)
        if not security.pin_hash:
            return Response({'error': 'Please set up a transaction PIN in your security settings before sending money.'}, status=status.HTTP_400_BAD_REQUEST)
        
        pin = request.data.get('pin')
        if not pin:
            return Response({'error': 'Transaction PIN is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        from django.contrib.auth.hashers import check_password
        if not check_password(pin, security.pin_hash):
            return Response({'error': 'Invalid transaction PIN.'}, status=status.HTTP_400_BAD_REQUEST)

        if security.otp_enabled:
            otp = request.data.get('otp')
            if not otp:
                import random
                otp_val = str(random.randint(100000, 999999))
                security.temp_otp = otp_val
                security.temp_otp_expiry = timezone.now() + timezone.timedelta(minutes=5)
                security.save()

                Notification.objects.create(
                    user=request.user,
                    title='Transfer OTP Code',
                    message=f'Your OTP code for sending money is: {otp_val}',
                )
                return Response({
                    'error': 'OTP verification required.',
                    'otp_required': True
                }, status=status.HTTP_403_FORBIDDEN)

            if security.temp_otp != otp or security.temp_otp_expiry < timezone.now():
                return Response({'error': 'Invalid or expired OTP code.'}, status=status.HTTP_400_BAD_REQUEST)

        # Clear OTP on success
        if security.otp_enabled:
            security.temp_otp = None
            security.temp_otp_expiry = None
            security.save()

        # Validate KYC
        verification = IdentityVerification.objects.filter(user=request.user).first()
        if not (verification and verification.verification_status == 'verified'):
            return Response(
                {'error': 'KYC verification required.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get sender wallet
        try:
            sender_wallet = Wallet.objects.get(id=sender_wallet_id, user=request.user)
        except Wallet.DoesNotExist:
            return Response({'error': 'Sender wallet not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Check wallet status
        if sender_wallet.status != 'active':
            return Response({'error': 'Sender wallet is not active.'}, status=status.HTTP_400_BAD_REQUEST)

        # Get recipient wallet
        try:
            recipient_wallet = Wallet.objects.get(wallet_number=recipient_wallet_number)
        except Wallet.DoesNotExist:
            return Response({'error': 'Recipient wallet not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Check recipient wallet status
        if recipient_wallet.status != 'active':
            return Response({'error': 'Recipient wallet is not active.'}, status=status.HTTP_400_BAD_REQUEST)

        # Prevent self-transfer
        if sender_wallet.id == recipient_wallet.id:
            return Response({'error': 'Cannot transfer to same wallet.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate amount
        try:
            amount = Decimal(str(amount))
            if amount <= 0:
                raise ValueError
        except (ValueError, TypeError):
            return Response({'error': 'Invalid amount.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check balance
        if sender_wallet.balance < amount:
            return Response(
                {'error': f'Insufficient balance. Available: {sender_wallet.balance} {sender_wallet.currency}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check currency match
        if sender_wallet.currency != recipient_wallet.currency:
            return Response(
                {'error': f'Currency mismatch. Sender: {sender_wallet.currency}, Recipient: {recipient_wallet.currency}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check transaction limits
        today = timezone.now().date()
        daily_total = Transaction.objects.filter(
            wallet=sender_wallet,
            transaction_type='transfer',
            created_at__date=today
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        limit, _ = TransactionLimit.objects.get_or_create(user=request.user)
        if limit.daily_limit > 0 and daily_total + amount > limit.daily_limit:
            return Response(
                {'error': f'Daily transfer limit exceeded. Limit: {limit.daily_limit}, Already sent: {daily_total}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Monthly limit check
        month_start = today.replace(day=1)
        monthly_total = Transaction.objects.filter(
            wallet=sender_wallet,
            transaction_type='transfer',
            created_at__date__gte=month_start
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        if limit.monthly_limit > 0 and monthly_total + amount > limit.monthly_limit:
            return Response(
                {'error': f'Monthly transfer limit exceeded. Limit: {limit.monthly_limit}, Already sent: {monthly_total}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Execute transfer atomically
        with db_transaction.atomic():
            transaction = Transaction.objects.create(
                wallet=sender_wallet,
                transaction_type='transfer',
                amount=amount,
                status='completed',
                description=description,
                reference=f'TRF-{uuid.uuid4().hex[:8].upper()}',
            )
            transfer = Transfer.objects.create(
                transaction=transaction,
                sender_wallet=sender_wallet,
                receiver_wallet=recipient_wallet,
            )
            sender_wallet.balance -= amount
            recipient_wallet.balance += amount
            sender_wallet.save()
            recipient_wallet.save()

            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action=f'Transfer {amount} {sender_wallet.currency} to {recipient_wallet.wallet_number}',
                ip_address=request.META.get('REMOTE_ADDR'),
            )

            # Create notifications
            Notification.objects.create(
                user=recipient_wallet.user,
                transaction=transaction,
                title='Money Received',
                message=f'You received {amount} {sender_wallet.currency} from {request.user.full_name}.',
            )
            Notification.objects.create(
                user=request.user,
                transaction=transaction,
                title='Money Sent',
                message=f'You sent {amount} {sender_wallet.currency} to {recipient_wallet.user.full_name}.',
            )

        return Response({
            'message': 'Transfer successful.',
            'transfer': {
                'id': transfer.id,
                'reference': transaction.reference,
                'amount': str(amount),
                'currency': sender_wallet.currency,
                'sender_wallet': sender_wallet.wallet_number,
                'recipient_wallet': recipient_wallet.wallet_number,
                'recipient_name': recipient_wallet.user.full_name,
                'created_at': transfer.created_at,
            }
        }, status=status.HTTP_201_CREATED)


class TransferHistoryView(APIView):
    """
    GET /api/transfers/history/
    Get transfer history for authenticated user.
    Query params:
      - type: 'sent', 'received', or 'all' (default: 'all')
      - limit: number of results to return (default: 50)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        transfer_type = request.query_params.get('type', 'all')
        limit = int(request.query_params.get('limit', 50))

        wallet_ids = Wallet.objects.filter(user=request.user).values_list('id', flat=True)

        history = []

        if transfer_type in ['sent', 'all']:
            sent = Transfer.objects.filter(
                sender_wallet__in=wallet_ids
            ).select_related('transaction', 'receiver_wallet__user', 'sender_wallet').order_by('-created_at')[:limit]

            for t in sent:
                history.append({
                    'type': 'sent',
                    'amount': str(t.transaction.amount),
                    'currency': t.sender_wallet.currency,
                    'to_wallet_number': t.receiver_wallet.wallet_number,
                    'to_user_name': t.receiver_wallet.user.full_name,
                    'from_wallet_number': t.sender_wallet.wallet_number,
                    'from_user_name': request.user.full_name,
                    'date': t.created_at.isoformat(),
                    'reference': t.transaction.reference,
                    'description': t.transaction.description,
                    'status': t.transaction.status,
                })

        if transfer_type in ['received', 'all']:
            received = Transfer.objects.filter(
                receiver_wallet__in=wallet_ids
            ).select_related('transaction', 'sender_wallet__user', 'receiver_wallet').order_by('-created_at')[:limit]

            for t in received:
                history.append({
                    'type': 'received',
                    'amount': str(t.transaction.amount),
                    'currency': t.receiver_wallet.currency,
                    'from_wallet_number': t.sender_wallet.wallet_number,
                    'from_user_name': t.sender_wallet.user.full_name,
                    'to_wallet_number': t.receiver_wallet.wallet_number,
                    'to_user_name': request.user.full_name,
                    'date': t.created_at.isoformat(),
                    'reference': t.transaction.reference,
                    'description': t.transaction.description,
                    'status': t.transaction.status,
                })

        # Sort by date descending
        history.sort(key=lambda x: x['date'], reverse=True)

        # Apply limit after combining
        history = history[:limit]

        return Response({
            'count': len(history),
            'transfers': history
        })


class AdminRequiredPermission(IsAuthenticated):
    """Permission class that checks if user is admin/staff."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.is_staff or request.user.is_superuser or request.user.role == 'admin')
        )


class AdminAllTransactionsView(APIView):
    """
    GET /api/admin/transactions/
    Admin endpoint to view all transactions in the system.
    Query params:
      - type: 'transfer', 'topup', 'withdrawal', 'bill_payment', 'all' (default: 'all')
      - status: 'completed', 'pending', 'failed', 'refunded' (optional)
      - user_id: filter by specific user (optional)
      - start_date: YYYY-MM-DD (optional)
      - end_date: YYYY-MM-DD (optional)
      - limit: number of results (default: 100)
      - offset: pagination offset (default: 0)
    """
    permission_classes = [AdminRequiredPermission]

    def get(self, request):
        tx_type = request.query_params.get('type', 'all')
        status_filter = request.query_params.get('status')
        user_id = request.query_params.get('user_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        limit = int(request.query_params.get('limit', 100))
        offset = int(request.query_params.get('offset', 0))

        # Base queryset
        queryset = Transaction.objects.all().select_related('wallet', 'wallet__user', 'merchant', 'biller')

        # Apply filters
        if tx_type != 'all':
            queryset = queryset.filter(transaction_type=tx_type)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if user_id:
            queryset = queryset.filter(wallet__user_id=user_id)
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        # Get total count before pagination
        total_count = queryset.count()

        # Calculate totals
        from django.db.models import Sum
        totals = queryset.aggregate(
            total_amount=Sum('amount')
        )

        # Apply pagination
        queryset = queryset.order_by('-created_at')[offset:offset + limit]

        # Build response
        transactions = []
        for tx in queryset:
            tx_data = {
                'id': tx.id,
                'reference': tx.reference,
                'type': tx.transaction_type,
                'amount': str(tx.amount),
                'currency': tx.wallet.currency if tx.wallet else None,
                'status': tx.status,
                'description': tx.description,
                'created_at': tx.created_at.isoformat(),
                'user': {
                    'id': tx.wallet.user.id if tx.wallet and tx.wallet.user else None,
                    'full_name': tx.wallet.user.full_name if tx.wallet and tx.wallet.user else None,
                    'email': tx.wallet.user.email if tx.wallet and tx.wallet.user else None,
                } if tx.wallet else None,
                'wallet': {
                    'id': tx.wallet.id if tx.wallet else None,
                    'wallet_number': tx.wallet.wallet_number if tx.wallet else None,
                },
            }

            # Add transfer details if applicable
            if tx.transaction_type == 'transfer':
                try:
                    transfer = Transfer.objects.select_related(
                        'sender_wallet__user', 'receiver_wallet__user'
                    ).get(transaction=tx)
                    tx_data['transfer_details'] = {
                        'sender': {
                            'wallet_number': transfer.sender_wallet.wallet_number if transfer.sender_wallet else None,
                            'user_name': transfer.sender_wallet.user.full_name if transfer.sender_wallet and transfer.sender_wallet.user else None,
                        },
                        'receiver': {
                            'wallet_number': transfer.receiver_wallet.wallet_number if transfer.receiver_wallet else None,
                            'user_name': transfer.receiver_wallet.user.full_name if transfer.receiver_wallet and transfer.receiver_wallet.user else None,
                        },
                    }
                except Transfer.DoesNotExist:
                    tx_data['transfer_details'] = None

            transactions.append(tx_data)

        return Response({
            'total_count': total_count,
            'returned_count': len(transactions),
            'total_amount': str(totals['total_amount'] or 0),
            'offset': offset,
            'limit': limit,
            'transactions': transactions,
        })


class AdminTransactionSummaryView(APIView):
    """
    GET /api/admin/transactions/summary/
    Admin endpoint to get transaction summary statistics.
    Query params:
      - start_date: YYYY-MM-DD (optional)
      - end_date: YYYY-MM-DD (optional)
    """
    permission_classes = [AdminRequiredPermission]

    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        queryset = Transaction.objects.all()

        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        from django.db.models import Count, Sum

        # Summary by type
        by_type = queryset.values('transaction_type').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('transaction_type')

        # Summary by status
        by_status = queryset.values('status').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('status')

        # Daily summary (last 30 days by default)
        from django.utils import timezone
        from datetime import timedelta

        if not start_date:
            daily_queryset = queryset.filter(created_at__gte=timezone.now() - timedelta(days=30))
        else:
            daily_queryset = queryset

        daily_summary = daily_queryset.values('created_at__date').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-created_at__date')[:30]

        return Response({
            'by_type': [
                {
                    'type': item['transaction_type'],
                    'count': item['count'],
                    'total_amount': str(item['total_amount'] or 0)
                }
                for item in by_type
            ],
            'by_status': [
                {
                    'status': item['status'],
                    'count': item['count'],
                    'total_amount': str(item['total_amount'] or 0)
                }
                for item in by_status
            ],
            'daily_summary': [
                {
                    'date': item['created_at__date'].isoformat(),
                    'count': item['count'],
                    'total_amount': str(item['total_amount'] or 0)
                }
                for item in daily_summary
            ],
        })


class FraudDetectionViewSet(viewsets.ModelViewSet):
    queryset = FraudDetection.objects.all()
    serializer_class = FraudDetectionSerializer


# ═════════════════════════════════════════
#  PASSWORD RESET VIEWS (Resend API)
# ═════════════════════════════════════════

class PasswordResetRequestView(APIView):
    """
    POST /api/auth/password-reset/request/
    Request password reset. Sends reset link via email.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')

        if not email:
            return Response(
                {'error': 'Email is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Don't reveal if email exists for security
            return Response(
                {'message': 'If an account exists with this email, a password reset link has been sent.'},
                status=status.HTTP_200_OK
            )

        # Generate reset token
        token = generate_reset_token()
        user.password_reset_token = token
        user.password_reset_sent_at = timezone.now()
        user.save()

        # Build reset URL
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        reset_url = f"{frontend_url}/reset-password?token={token}"

        # Send email via Resend
        result = send_password_reset_email(user, reset_url)

        if result['success']:
            return Response(
                {'message': 'If an account exists with this email, a password reset link has been sent.'},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'error': 'Failed to send reset email. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PasswordResetVerifyView(APIView):
    """
    POST /api/auth/password-reset/verify/
    Verify reset token and set new password.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('token')
        new_password = request.data.get('new_password')

        if not token or not new_password:
            return Response(
                {'error': 'Token and new password are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate password length
        if len(new_password) < 8:
            return Response(
                {'error': 'Password must be at least 8 characters long.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(password_reset_token=token)
        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid or expired reset token.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if token is expired (1 hour validity)
        if user.password_reset_sent_at:
            time_diff = timezone.now() - user.password_reset_sent_at
            if time_diff.total_seconds() > 3600:  # 1 hour
                return Response(
                    {'error': 'Reset token has expired. Please request a new one.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Set new password
        user.set_password(new_password)
        user.password_reset_token = None
        user.password_reset_sent_at = None
        user.save()

        # Send confirmation email
        send_password_reset_confirmation(user)

        return Response(
            {'message': 'Password has been reset successfully.'},
            status=status.HTTP_200_OK
        )


class PasswordResetValidateTokenView(APIView):
    """
    GET /api/auth/password-reset/validate/?token=<token>
    Validate if a reset token is still valid.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get('token')

        if not token:
            return Response(
                {'error': 'Token is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(password_reset_token=token)
        except User.DoesNotExist:
            return Response(
                {'valid': False, 'error': 'Invalid token.'},
                status=status.HTTP_200_OK
            )

        # Check if token is expired
        if user.password_reset_sent_at:
            time_diff = timezone.now() - user.password_reset_sent_at
            if time_diff.total_seconds() > 3600:  # 1 hour
                return Response(
                    {'valid': False, 'error': 'Token has expired.'},
                    status=status.HTTP_200_OK
                )

        return Response(
            {'valid': True, 'email': user.email},
            status=status.HTTP_200_OK
        )


class AdminDashboardView(AdminRequiredMixin, View):
    """GET /admin/dashboard/ — Admin portal dashboard with statistics and financial reports."""
    template_name = 'wallet/admin_dashboard.html'

    def get(self, request):
        from datetime import datetime, timedelta
        from django.db.models import Sum, Count, Avg, Q
        from django.db.models.functions import TruncDate, TruncMonth, TruncYear

        # Date filters
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)

        selected_period = request.GET.get('period', 'today')

        # Set date range based on selected period
        if selected_period == 'today':
            start_date = today
            end_date = today + timedelta(days=1)
            prev_start = today - timedelta(days=1)
            prev_end = today
        elif selected_period == 'week':
            start_date = week_start
            end_date = today + timedelta(days=1)
            prev_start = week_start - timedelta(days=7)
            prev_end = week_start
        elif selected_period == 'month':
            start_date = month_start
            end_date = today + timedelta(days=1)
            if month_start.month == 1:
                prev_start = month_start.replace(year=month_start.year - 1, month=12)
            else:
                prev_start = month_start.replace(month=month_start.month - 1)
            prev_end = month_start
        elif selected_period == 'year':
            start_date = year_start
            end_date = today + timedelta(days=1)
            prev_start = year_start.replace(year=year_start.year - 1)
            prev_end = year_start
        else:
            start_date = today
            end_date = today + timedelta(days=1)
            prev_start = today - timedelta(days=1)
            prev_end = today

        # ─── USER STATISTICS ───
        total_users = User.objects.count()
        new_users_period = User.objects.filter(date_joined__date__gte=start_date, date_joined__date__lt=end_date).count()
        new_users_prev = User.objects.filter(date_joined__date__gte=prev_start, date_joined__date__lt=prev_end).count()
        active_users = User.objects.filter(status='active').count()
        verified_users = IdentityVerification.objects.filter(verification_status='verified').count()
        pending_verifications = IdentityVerification.objects.filter(verification_status='pending').count()

        # ─── WALLET STATISTICS ───
        total_wallets = Wallet.objects.count()
        active_wallets = Wallet.objects.filter(status='active').count()
        frozen_wallets = Wallet.objects.filter(status='frozen').count()
        total_balance = Wallet.objects.aggregate(total=Sum('balance'))['total'] or Decimal('0')
        avg_wallet_balance = Wallet.objects.filter(status='active').aggregate(avg=Avg('balance'))['avg'] or Decimal('0')

        # ─── TRANSACTION STATISTICS (Period) ───
        period_transactions = Transaction.objects.filter(created_at__date__gte=start_date, created_at__date__lt=end_date)
        total_transactions_period = period_transactions.count()
        total_volume_period = period_transactions.aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Previous period comparison
        prev_transactions = Transaction.objects.filter(created_at__date__gte=prev_start, created_at__date__lt=prev_end)
        prev_transaction_count = prev_transactions.count()
        prev_volume = prev_transactions.aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Calculate percentage changes
        transaction_change = self._calc_percentage_change(total_transactions_period, prev_transaction_count)
        volume_change = self._calc_percentage_change(total_volume_period, prev_volume)

        # ─── TRANSACTION BREAKDOWN ───
        transfers = period_transactions.filter(transaction_type='transfer').aggregate(
            count=Count('id'), total=Sum('amount')
        )
        topups = period_transactions.filter(transaction_type='topup').aggregate(
            count=Count('id'), total=Sum('amount')
        )
        withdrawals = period_transactions.filter(transaction_type='withdrawal').aggregate(
            count=Count('id'), total=Sum('amount')
        )
        bill_payments = period_transactions.filter(transaction_type='bill_payment').aggregate(
            count=Count('id'), total=Sum('amount')
        )

        # ─── STATUS BREAKDOWN ───
        completed_transactions = period_transactions.filter(status='completed').count()
        pending_transactions = period_transactions.filter(status='pending').count()
        failed_transactions = period_transactions.filter(status='failed').count()

        # ─── REVENUE CALCULATION (Example: 1% fee on transfers) ───
        transfer_fees = (transfers['total'] or Decimal('0')) * Decimal('0.01')
        total_revenue = transfer_fees

        # ─── RECENT ACTIVITY ───
        recent_transactions = Transaction.objects.select_related('wallet', 'wallet__user').order_by('-created_at')[:10]
        recent_users = User.objects.order_by('-date_joined')[:5]
        recent_transfers = Transfer.objects.select_related(
            'transaction', 'sender_wallet__user', 'receiver_wallet__user'
        ).order_by('-created_at')[:10]

        # ─── CHART DATA (Last 30 days) ───
        chart_start = today - timedelta(days=29)
        daily_data = Transaction.objects.filter(
            created_at__date__gte=chart_start
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id'),
            volume=Sum('amount')
        ).order_by('date')

        # Format chart data for JavaScript
        chart_labels = []
        chart_counts = []
        chart_volumes = []

        for i in range(30):
            date = chart_start + timedelta(days=i)
            chart_labels.append(date.strftime('%m/%d'))
            day_data = next((d for d in daily_data if d['date'] == date), None)
            chart_counts.append(day_data['count'] if day_data else 0)
            chart_volumes.append(float(day_data['volume'] or 0) if day_data else 0)

        # ─── TOP USERS BY TRANSACTION VOLUME ───
        top_users = Wallet.objects.annotate(
            total_volume=Sum('transactions__amount')
        ).select_related('user').order_by('-total_volume')[:10]

        # ─── CURRENCY DISTRIBUTION ───
        currency_distribution = Wallet.objects.values('currency').annotate(
            count=Count('id'),
            total_balance=Sum('balance')
        ).order_by('-count')

        context = {
            'active_page': 'admin_dashboard',
            'selected_period': selected_period,

            # User stats
            'total_users': total_users,
            'new_users_period': new_users_period,
            'new_users_prev': new_users_prev,
            'active_users': active_users,
            'verified_users': verified_users,
            'pending_verifications': pending_verifications,
            'user_change': self._calc_percentage_change(new_users_period, new_users_prev),

            # Wallet stats
            'total_wallets': total_wallets,
            'active_wallets': active_wallets,
            'frozen_wallets': frozen_wallets,
            'total_balance': total_balance,
            'avg_wallet_balance': avg_wallet_balance,

            # Transaction stats
            'total_transactions_period': total_transactions_period,
            'total_volume_period': total_volume_period,
            'transaction_change': transaction_change,
            'volume_change': volume_change,

            # Breakdown
            'transfers_count': transfers['count'] or 0,
            'transfers_volume': transfers['total'] or Decimal('0'),
            'topups_count': topups['count'] or 0,
            'topups_volume': topups['total'] or Decimal('0'),
            'withdrawals_count': withdrawals['count'] or 0,
            'withdrawals_volume': withdrawals['total'] or Decimal('0'),
            'bill_payments_count': bill_payments['count'] or 0,
            'bill_payments_volume': bill_payments['total'] or Decimal('0'),

            # Status
            'completed_transactions': completed_transactions,
            'pending_transactions': pending_transactions,
            'failed_transactions': failed_transactions,

            # Revenue
            'total_revenue': total_revenue,

            # Recent activity
            'recent_transactions': recent_transactions,
            'recent_users': recent_users,
            'recent_transfers': recent_transfers,

            # Chart data
            'chart_labels': chart_labels,
            'chart_counts': chart_counts,
            'chart_volumes': chart_volumes,

            # Top users
            'top_users': top_users,

            # Currency
            'currency_distribution': currency_distribution,
        }

        return render(request, self.template_name, context)

    def _calc_percentage_change(self, current, previous):
        """Calculate percentage change between two values."""
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100, 1)
