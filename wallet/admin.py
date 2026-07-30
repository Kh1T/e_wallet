from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.conf import settings
from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.urls import path
from datetime import datetime, timedelta
from decimal import Decimal

from .models import (
    IdentityVerification, Notification, Transaction, Transfer, Wallet,
    User, Merchant, Biller, Topup, Withdrawal, BillPayment,
    Security, TransactionLimit, AuditLog
)


def approve_kyc(modeladmin, request, queryset):
    updated = 0
    for verification in queryset:
        if verification.verification_status != 'verified':
            verification.verification_status = 'verified'
            verification.verified_at = timezone.now()
            verification.rejection_reason = None
            verification.save(update_fields=['verification_status', 'verified_at', 'rejection_reason'])
            Notification.objects.create(
                user=verification.user,
                title='KYC Verified',
                message='Your identity verification has been approved. You can now send money and use all wallet features.',
            )
            updated += 1
    modeladmin.message_user(request, f'{updated} KYC submission(s) approved.')


approve_kyc.short_description = 'Approve selected KYC submissions'


def reject_kyc(modeladmin, request, queryset):
    updated = 0
    for verification in queryset:
        if verification.verification_status != 'rejected':
            verification.verification_status = 'rejected'
            verification.verified_at = None
            verification.save(update_fields=['verification_status', 'verified_at'])
            Notification.objects.create(
                user=verification.user,
                title='KYC Rejected',
                message='Your identity verification has been rejected. Please check the rejection reason and resubmit valid documents.',
            )
            updated += 1
    modeladmin.message_user(request, f'{updated} KYC submission(s) rejected. Note: Add rejection reasons individually for better user feedback.')


reject_kyc.short_description = 'Reject selected KYC submissions (bulk)'


def mark_completed(modeladmin, request, queryset):
    updated = queryset.filter(status='pending').update(status='completed')
    modeladmin.message_user(request, f'{updated} transaction(s) marked as completed.')


mark_completed.short_description = 'Mark selected transactions as completed'


def mark_failed(modeladmin, request, queryset):
    updated = queryset.filter(status='pending').update(status='failed')
    modeladmin.message_user(request, f'{updated} transaction(s) marked as failed.')


mark_failed.short_description = 'Mark selected transactions as failed'


def refund_transaction(modeladmin, request, queryset):
    """Refund selected transactions (reverse the transfer)."""
    refunded = 0
    for transaction in queryset.filter(transaction_type='transfer', status='completed'):
        try:
            transfer = Transfer.objects.get(transaction=transaction)
            from decimal import Decimal
            from django.db import transaction as db_transaction
            
            with db_transaction.atomic():
                # Reverse the transfer
                sender_wallet = transfer.sender_wallet
                receiver_wallet = transfer.receiver_wallet
                amount = transaction.amount
                
                sender_wallet.balance += amount
                receiver_wallet.balance -= amount
                sender_wallet.save()
                receiver_wallet.save()
                
                transaction.status = 'refunded'
                transaction.save()
                
                # Create notification
                Notification.objects.create(
                    user=sender_wallet.user,
                    title='Transaction Refunded',
                    message=f'Your transfer of {amount} {sender_wallet.currency} has been refunded.',
                )
                refunded += 1
        except Transfer.DoesNotExist:
            continue
    modeladmin.message_user(request, f'{refunded} transaction(s) refunded.')


refund_transaction.short_description = 'Refund selected transfer transactions'


@admin.register(IdentityVerification)
class IdentityVerificationAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'national_id', 'verification_status', 'id_document_preview', 'selfie_preview', 'created_at'
    )
    list_filter = ('verification_status', 'created_at', 'verified_at')
    search_fields = ('user__email', 'user__full_name', 'national_id')
    actions = (approve_kyc, reject_kyc)
    readonly_fields = ('created_at', 'verified_at', 'id_document_image', 'selfie_image_display')
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'national_id', 'date_of_birth', 'address', 'nationality')
        }),
        ('Documents', {
            'fields': ('id_document_image', 'selfie_image_display'),
            'description': 'Click on images to view full size in new tab'
        }),
        ('Verification Status', {
            'fields': ('verification_status', 'verified_at', 'rejection_reason'),
            'description': 'Set status to verified/rejected. Add rejection reason when rejecting.'
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def id_document_preview(self, obj):
        if obj.id_document:
            return format_html(
                '<a href="{0}" target="_blank"><img src="{0}" style="max-height: 50px; max-width: 100px; border-radius: 4px;" /></a>',
                f'{settings.MEDIA_URL}{obj.id_document}'
            )
        return '—'
    id_document_preview.short_description = 'ID Document'

    def selfie_preview(self, obj):
        if obj.selfie_image:
            return format_html(
                '<a href="{0}" target="_blank"><img src="{0}" style="max-height: 50px; max-width: 100px; border-radius: 4px;" /></a>',
                f'{settings.MEDIA_URL}{obj.selfie_image}'
            )
        return '—'
    selfie_preview.short_description = 'Selfie'

    def id_document_image(self, obj):
        if obj.id_document:
            return format_html(
                '<a href="{0}" target="_blank"><img src="{0}" style="max-height: 300px; max-width: 100%; border-radius: 8px; border: 1px solid #ddd;" /><br><small>Click to view full size</small></a>',
                f'{settings.MEDIA_URL}{obj.id_document}'
            )
        return 'No ID document uploaded'
    id_document_image.short_description = 'ID Document Preview'

    def selfie_image_display(self, obj):
        if obj.selfie_image:
            return format_html(
                '<a href="{0}" target="_blank"><img src="{0}" style="max-height: 300px; max-width: 100%; border-radius: 8px; border: 1px solid #ddd;" /><br><small>Click to view full size</small></a>',
                f'{settings.MEDIA_URL}{obj.selfie_image}'
            )
        return 'No selfie uploaded'
    selfie_image_display.short_description = 'Selfie Preview'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'reference', 'transaction_type', 'wallet_owner', 'amount_formatted',
        'status_badge', 'created_at', 'description_preview'
    )
    list_filter = (
        'transaction_type', 'status', 'created_at',
        ('wallet__user', admin.RelatedOnlyFieldListFilter),
    )
    search_fields = (
        'reference', 'wallet__wallet_number', 'wallet__user__email',
        'wallet__user__full_name', 'description'
    )
    readonly_fields = ('created_at', 'reference')
    actions = [mark_completed, mark_failed, refund_transaction]
    date_hierarchy = 'created_at'
    list_per_page = 50

    fieldsets = (
        ('Transaction Details', {
            'fields': ('reference', 'transaction_type', 'amount', 'currency_display', 'status')
        }),
        ('Wallet Information', {
            'fields': ('wallet', 'wallet_owner_display'),
        }),
        ('Related Entities', {
            'fields': ('merchant', 'biller'),
            'classes': ('collapse',)
        }),
        ('Additional Info', {
            'fields': ('description', 'created_at'),
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('wallet', 'wallet__user', 'merchant', 'biller')

    def wallet_owner(self, obj):
        if obj.wallet and obj.wallet.user:
            return format_html(
                '<strong>{0}</strong><br><small>{1}</small>',
                obj.wallet.user.full_name,
                obj.wallet.user.email
            )
        return '—'
    wallet_owner.short_description = 'Wallet Owner'

    def wallet_owner_display(self, obj):
        if obj.wallet and obj.wallet.user:
            return f"{obj.wallet.user.full_name} ({obj.wallet.user.email})"
        return '—'
    wallet_owner_display.short_description = 'Wallet Owner'

    def amount_formatted(self, obj):
        currency = obj.wallet.currency if obj.wallet else 'N/A'
        return format_html(
            '<span style="font-weight: bold;">{0} {1}</span>',
            obj.amount,
            currency
        )
    amount_formatted.short_description = 'Amount'

    def currency_display(self, obj):
        return obj.wallet.currency if obj.wallet else 'N/A'
    currency_display.short_description = 'Currency'

    def status_badge(self, obj):
        colors = {
            'completed': 'green',
            'pending': 'orange',
            'failed': 'red',
            'refunded': 'blue',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {0}; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px;">{1}</span>',
            color,
            obj.status.upper()
        )
    status_badge.short_description = 'Status'

    def description_preview(self, obj):
        if obj.description:
            return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
        return '—'
    description_preview.short_description = 'Description'

    def changelist_view(self, request, extra_context=None):
        # Add summary statistics
        response = super().changelist_view(request, extra_context=extra_context)
        try:
            qs = response.context_data['cl'].queryset
        except (AttributeError, KeyError):
            return response

        # Calculate totals
        totals = qs.aggregate(
            total_amount=Sum('amount')
        )

        # Count by status
        status_counts = {}
        for status_val in ['completed', 'pending', 'failed', 'refunded']:
            status_counts[status_val] = qs.filter(status=status_val).count()

        response.context_data['total_amount'] = totals['total_amount'] or 0
        response.context_data['status_counts'] = status_counts
        return response


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'transaction_reference', 'sender_info', 'receiver_info',
        'amount_formatted', 'created_at'
    )
    list_filter = (
        'created_at',
        ('sender_wallet__user', admin.RelatedOnlyFieldListFilter),
        ('receiver_wallet__user', admin.RelatedOnlyFieldListFilter),
    )
    search_fields = (
        'transaction__reference',
        'sender_wallet__wallet_number',
        'receiver_wallet__wallet_number',
        'sender_wallet__user__email',
        'receiver_wallet__user__email',
    )
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Transfer Details', {
            'fields': ('transaction', 'created_at')
        }),
        ('Sender Information', {
            'fields': ('sender_wallet', 'sender_details'),
        }),
        ('Receiver Information', {
            'fields': ('receiver_wallet', 'receiver_details'),
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'transaction', 'transaction__wallet',
            'sender_wallet', 'sender_wallet__user',
            'receiver_wallet', 'receiver_wallet__user'
        )

    def transaction_reference(self, obj):
        if obj.transaction:
            return format_html(
                '<a href="/admin/wallet/transaction/{0}/change/">{1}</a>',
                obj.transaction.id,
                obj.transaction.reference
            )
        return '—'
    transaction_reference.short_description = 'Transaction Reference'

    def sender_info(self, obj):
        if obj.sender_wallet and obj.sender_wallet.user:
            return format_html(
                '<strong>{0}</strong><br><small>{1}</small>',
                obj.sender_wallet.user.full_name,
                obj.sender_wallet.wallet_number
            )
        return '—'
    sender_info.short_description = 'Sender'

    def receiver_info(self, obj):
        if obj.receiver_wallet and obj.receiver_wallet.user:
            return format_html(
                '<strong>{0}</strong><br><small>{1}</small>',
                obj.receiver_wallet.user.full_name,
                obj.receiver_wallet.wallet_number
            )
        return '—'
    receiver_info.short_description = 'Receiver'

    def sender_details(self, obj):
        if obj.sender_wallet and obj.sender_wallet.user:
            return f"{obj.sender_wallet.user.full_name} ({obj.sender_wallet.user.email}) - {obj.sender_wallet.wallet_number}"
        return '—'
    sender_details.short_description = 'Sender Details'

    def receiver_details(self, obj):
        if obj.receiver_wallet and obj.receiver_wallet.user:
            return f"{obj.receiver_wallet.user.full_name} ({obj.receiver_wallet.user.email}) - {obj.receiver_wallet.wallet_number}"
        return '—'
    receiver_details.short_description = 'Receiver Details'

    def amount_formatted(self, obj):
        if obj.transaction:
            currency = obj.sender_wallet.currency if obj.sender_wallet else 'N/A'
            return format_html(
                '<span style="font-weight: bold; color: green;">{0} {1}</span>',
                obj.transaction.amount,
                currency
            )
        return '—'
    amount_formatted.short_description = 'Amount'


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = (
        'wallet_number', 'owner_info', 'balance_formatted',
        'currency', 'status_badge', 'created_at'
    )
    list_filter = ('currency', 'status', 'created_at')
    search_fields = ('wallet_number', 'user__email', 'user__full_name')
    readonly_fields = ('created_at',)
    actions = ['freeze_wallets', 'unfreeze_wallets']

    fieldsets = (
        ('Wallet Information', {
            'fields': ('wallet_number', 'user', 'balance', 'currency', 'status')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

    def owner_info(self, obj):
        if obj.user:
            return format_html(
                '<strong>{0}</strong><br><small>{1}</small>',
                obj.user.full_name,
                obj.user.email
            )
        return '—'
    owner_info.short_description = 'Owner'

    def balance_formatted(self, obj):
        return format_html(
            '<span style="font-weight: bold;">{0}</span>',
            obj.balance
        )
    balance_formatted.short_description = 'Balance'

    def status_badge(self, obj):
        colors = {
            'active': 'green',
            'frozen': 'orange',
            'closed': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {0}; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px;">{1}</span>',
            color,
            obj.status.upper()
        )
    status_badge.short_description = 'Status'

    def freeze_wallets(self, request, queryset):
        updated = queryset.filter(status='active').update(status='frozen')
        self.message_user(request, f'{updated} wallet(s) frozen.')
    freeze_wallets.short_description = 'Freeze selected wallets'

    def unfreeze_wallets(self, request, queryset):
        updated = queryset.filter(status='frozen').update(status='active')
        self.message_user(request, f'{updated} wallet(s) unfrozen.')
    unfreeze_wallets.short_description = 'Unfreeze selected wallets'


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'full_name', 'email', 'phone', 'role', 'status_badge', 'date_joined')
    list_filter = ('role', 'status', 'date_joined', 'is_staff')
    search_fields = ('username', 'email', 'full_name', 'phone')
    readonly_fields = ('date_joined', 'last_login')

    def status_badge(self, obj):
        colors = {
            'active': 'green',
            'inactive': 'gray',
            'suspended': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {0}; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px;">{1}</span>',
            color,
            obj.status.upper()
        )
    status_badge.short_description = 'Status'


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action_preview', 'user_info', 'ip_address', 'created_at')
    list_filter = ('created_at', ('user', admin.RelatedOnlyFieldListFilter))
    search_fields = ('action', 'user__email', 'ip_address')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

    def action_preview(self, obj):
        return obj.action[:60] + '...' if len(obj.action) > 60 else obj.action
    action_preview.short_description = 'Action'

    def user_info(self, obj):
        if obj.user:
            return f"{obj.user.full_name} ({obj.user.email})"
        return 'System'
    user_info.short_description = 'User'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title_preview', 'user_info', 'is_read_badge', 'created_at')
    list_filter = ('is_read', 'created_at', ('user', admin.RelatedOnlyFieldListFilter))
    search_fields = ('title', 'message', 'user__email')
    readonly_fields = ('created_at',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

    def title_preview(self, obj):
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
    title_preview.short_description = 'Title'

    def user_info(self, obj):
        if obj.user:
            return f"{obj.user.full_name} ({obj.user.email})"
        return '—'
    user_info.short_description = 'User'

    def is_read_badge(self, obj):
        if obj.is_read:
            return format_html(
                '<span style="background-color: green; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px;">READ</span>'
            )
        return format_html(
            '<span style="background-color: orange; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px;">UNREAD</span>'
        )
    is_read_badge.short_description = 'Status'


# Register remaining models with basic admin
@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = ('merchant_name', 'email', 'phone', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('merchant_name', 'email', 'phone')


@admin.register(Biller)
class BillerAdmin(admin.ModelAdmin):
    list_display = ('biller_name', 'category', 'account_number', 'wallet_balance', 'user_info', 'status', 'created_at')
    list_filter = ('category', 'status', 'created_at')
    search_fields = ('biller_name', 'account_number')
    raw_id_fields = ('user',)

    def wallet_balance(self, obj):
        """Display biller's wallet balance."""
        if obj.user:
            wallet = obj.user.wallets.first()
            if wallet:
                return f"{wallet.balance} {wallet.currency}"
        return "—"
    wallet_balance.short_description = 'Wallet Balance'

    def user_info(self, obj):
        """Display linked user info."""
        if obj.user:
            return f"{obj.user.full_name} ({obj.user.email})"
        return "—"
    user_info.short_description = 'Linked User'


@admin.register(Topup)
class TopupAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'payment_method', 'provider', 'created_at')
    list_filter = ('payment_method', 'created_at')
    search_fields = ('transaction__reference', 'provider')


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'bank_name', 'account_number', 'created_at')
    list_filter = ('bank_name', 'created_at')
    search_fields = ('transaction__reference', 'account_number', 'bank_name')


@admin.register(BillPayment)
class BillPaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'bill_type', 'account_reference', 'created_at')
    list_filter = ('bill_type', 'created_at')
    search_fields = ('transaction__reference', 'account_reference')


@admin.register(Security)
class SecurityAdmin(admin.ModelAdmin):
    list_display = ('user_info', 'otp_enabled', 'two_factor_enabled', 'biometric_enabled', 'updated_at')
    list_filter = ('otp_enabled', 'two_factor_enabled', 'biometric_enabled')
    search_fields = ('user__email', 'user__full_name')

    def user_info(self, obj):
        return f"{obj.user.full_name} ({obj.user.email})"
    user_info.short_description = 'User'


@admin.register(TransactionLimit)
class TransactionLimitAdmin(admin.ModelAdmin):
    list_display = ('user_info', 'daily_limit', 'monthly_limit', 'yearly_limit', 'updated_at')
    search_fields = ('user__email', 'user__full_name')

    def user_info(self, obj):
        return f"{obj.user.full_name} ({obj.user.email})"
    user_info.short_description = 'User'


# ─────────────────────────────────────────────
#  CUSTOM ADMIN DASHBOARD
# ─────────────────────────────────────────────
from django.template.response import TemplateResponse


class DashboardAdminSite(admin.AdminSite):
    """Custom Admin Site with Dashboard."""
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_view(self.dashboard_view), name='admin_dashboard'),
        ]
        return custom_urls + urls
    
    def index(self, request, extra_context=None):
        """Override index to redirect to dashboard."""
        return self.dashboard_view(request)
    
    def dashboard_view(self, request):
        """Admin Dashboard with Statistics and Financial Reports."""
        # Date ranges
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)
        
        # ─── USER STATISTICS ───
        total_users = User.objects.count()
        new_users_today = User.objects.filter(date_joined__date=today).count()
        new_users_week = User.objects.filter(date_joined__date__gte=week_start).count()
        new_users_month = User.objects.filter(date_joined__date__gte=month_start).count()
        active_users = User.objects.filter(status='active').count()
        verified_users = IdentityVerification.objects.filter(verification_status='verified').count()
        pending_verifications = IdentityVerification.objects.filter(verification_status='pending').count()
        
        # ─── WALLET STATISTICS ───
        total_wallets = Wallet.objects.count()
        active_wallets = Wallet.objects.filter(status='active').count()
        frozen_wallets = Wallet.objects.filter(status='frozen').count()
        total_balance = Wallet.objects.aggregate(total=Sum('balance'))['total'] or Decimal('0')
        avg_wallet_balance = Wallet.objects.filter(status='active').aggregate(avg=Avg('balance'))['avg'] or Decimal('0')
        
        # ─── TRANSACTION STATISTICS (Today) ───
        today_transactions = Transaction.objects.filter(created_at__date=today)
        today_count = today_transactions.count()
        today_volume = today_transactions.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # ─── TRANSACTION STATISTICS (This Month) ───
        month_transactions = Transaction.objects.filter(created_at__date__gte=month_start)
        month_count = month_transactions.count()
        month_volume = month_transactions.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # ─── TRANSACTION BREAKDOWN ───
        transfers = month_transactions.filter(transaction_type='transfer').aggregate(
            count=Count('id'), total=Sum('amount')
        )
        topups = month_transactions.filter(transaction_type='topup').aggregate(
            count=Count('id'), total=Sum('amount')
        )
        withdrawals = month_transactions.filter(transaction_type='withdrawal').aggregate(
            count=Count('id'), total=Sum('amount')
        )
        bill_payments = month_transactions.filter(transaction_type='bill_payment').aggregate(
            count=Count('id'), total=Sum('amount')
        )
        
        # ─── STATUS BREAKDOWN ───
        completed_transactions = month_transactions.filter(status='completed').count()
        pending_transactions = month_transactions.filter(status='pending').count()
        failed_transactions = month_transactions.filter(status='failed').count()
        
        # ─── RECENT ACTIVITY ───
        recent_transactions = Transaction.objects.select_related('wallet', 'wallet__user').order_by('-created_at')[:10]
        recent_transfers = Transfer.objects.select_related(
            'transaction', 'sender_wallet__user', 'receiver_wallet__user'
        ).order_by('-created_at')[:10]
        
        # ─── DAILY CHART DATA (Last 30 days) ───
        chart_start = today - timedelta(days=29)
        daily_data = Transaction.objects.filter(
            created_at__date__gte=chart_start
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id'),
            volume=Sum('amount')
        ).order_by('date')
        
        # Format chart data
        chart_labels = []
        chart_counts = []
        chart_volumes = []
        
        for i in range(30):
            date = chart_start + timedelta(days=i)
            chart_labels.append(date.strftime('%m/%d'))
            day_data = next((d for d in daily_data if d['date'] == date), None)
            chart_counts.append(day_data['count'] if day_data else 0)
            chart_volumes.append(float(day_data['volume'] or 0) if day_data else 0)
        
        # ─── TOP USERS ───
        top_users = Wallet.objects.annotate(
            total_volume=Sum('transactions__amount')
        ).select_related('user').order_by('-total_volume')[:10]
        
        # ─── CURRENCY DISTRIBUTION ───
        currency_distribution = Wallet.objects.values('currency').annotate(
            count=Count('id'),
            total_balance=Sum('balance')
        ).order_by('-count')
        
        context = {
            'title': 'Dashboard',
            'total_users': total_users,
            'new_users_today': new_users_today,
            'new_users_week': new_users_week,
            'new_users_month': new_users_month,
            'active_users': active_users,
            'verified_users': verified_users,
            'pending_verifications': pending_verifications,
            
            'total_wallets': total_wallets,
            'active_wallets': active_wallets,
            'frozen_wallets': frozen_wallets,
            'total_balance': total_balance,
            'avg_wallet_balance': avg_wallet_balance,
            
            'today_count': today_count,
            'today_volume': today_volume,
            'month_count': month_count,
            'month_volume': month_volume,
            
            'transfers_count': transfers['count'] or 0,
            'transfers_volume': transfers['total'] or Decimal('0'),
            'topups_count': topups['count'] or 0,
            'topups_volume': topups['total'] or Decimal('0'),
            'withdrawals_count': withdrawals['count'] or 0,
            'withdrawals_volume': withdrawals['total'] or Decimal('0'),
            'bill_payments_count': bill_payments['count'] or 0,
            'bill_payments_volume': bill_payments['total'] or Decimal('0'),
            
            'completed_transactions': completed_transactions,
            'pending_transactions': pending_transactions,
            'failed_transactions': failed_transactions,
            
            'recent_transactions': recent_transactions,
            'recent_transfers': recent_transfers,
            
            'chart_labels': chart_labels,
            'chart_counts': chart_counts,
            'chart_volumes': chart_volumes,
            
            'top_users': top_users,
            'currency_distribution': currency_distribution,
            
            'has_permission': self.has_permission(request),
            'site_title': self.site_title,
            'site_header': self.site_header,
        }
        
        return TemplateResponse(request, 'admin/dashboard.html', context)


# Create custom admin site
custom_admin_site = DashboardAdminSite(name='admin')

# Re-register all models with custom admin
for model, admin_class in admin.site._registry.copy().items():
    custom_admin_site.register(model, admin_class.__class__)
