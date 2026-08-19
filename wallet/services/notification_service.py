"""
Notification Service Layer

Centralizes all notification creation logic for the e-wallet application.
Provides methods to create notifications for various transaction types,
security events, and system notifications.
"""

from decimal import Decimal
from django.utils import timezone
from ..models import Notification, Transaction, Wallet


class NotificationService:
    """
    Service class for creating and managing user notifications.
    
    This class provides a centralized way to create notifications for various
    events in the e-wallet system, including transactions, security events,
    and system notifications.
    """

    # ═══════════════════════════════════════════════════════════
    #  Transaction Notifications
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def notify_transfer_sent(sender_user, receiver_user, amount, currency, transaction):
        """
        Notify sender that they have sent money.
        
        Args:
            sender_user: The user who sent the money
            receiver_user: The user who received the money
            amount: Decimal amount sent
            currency: Currency code (e.g., 'KHR', 'USD')
            transaction: The Transaction instance
        """
        Notification.objects.create(
            user=sender_user,
            transaction=transaction,
            notification_type='transfer',
            title='Money Sent',
            message=f'You sent {amount} {currency} to {receiver_user.full_name}.',
        )

    @staticmethod
    def notify_transfer_received(sender_user, receiver_user, amount, currency, transaction):
        """
        Notify receiver that they have received money.
        
        Args:
            sender_user: The user who sent the money
            receiver_user: The user who received the money
            amount: Decimal amount received
            currency: Currency code (e.g., 'KHR', 'USD')
            transaction: The Transaction instance
        """
        Notification.objects.create(
            user=receiver_user,
            transaction=transaction,
            notification_type='transfer',
            title='Money Received',
            message=f'You received {amount} {currency} from {sender_user.full_name}.',
        )

    @staticmethod
    def notify_topup_completed(user, amount, currency, transaction, payment_method):
        """
        Notify user that their wallet has been topped up.
        
        Args:
            user: The user whose wallet was topped up
            amount: Decimal amount added
            currency: Currency code (e.g., 'KHR', 'USD')
            transaction: The Transaction instance
            payment_method: The payment method used (e.g., 'bank', 'card', 'cash')
        """
        Notification.objects.create(
            user=user,
            transaction=transaction,
            notification_type='topup',
            title='Wallet Topped Up',
            message=f'Your wallet has been credited with {amount} {currency} via {payment_method}.',
        )

    @staticmethod
    def notify_withdrawal_completed(user, amount, currency, transaction, bank_name, account_number):
        """
        Notify user that their withdrawal has been processed.
        
        Args:
            user: The user who withdrew money
            amount: Decimal amount withdrawn
            currency: Currency code (e.g., 'KHR', 'USD')
            transaction: The Transaction instance
            bank_name: Name of the bank
            account_number: Masked account number
        """
        masked_account = account_number[-4:] if len(account_number) > 4 else account_number
        Notification.objects.create(
            user=user,
            transaction=transaction,
            notification_type='withdrawal',
            title='Withdrawal Processed',
            message=f'Your withdrawal of {amount} {currency} to {bank_name} (•••{masked_account}) has been processed.',
        )

    @staticmethod
    def notify_withdrawal_initiated(user, amount, currency, transaction, bank_name, account_number):
        """
        Notify user that their withdrawal request has been initiated.
        
        Args:
            user: The user who initiated the withdrawal
            amount: Decimal amount requested
            currency: Currency code (e.g., 'KHR', 'USD')
            transaction: The Transaction instance
            bank_name: Name of the bank
            account_number: Bank account number
        """
        masked_account = account_number[-4:] if len(account_number) > 4 else account_number
        Notification.objects.create(
            user=user,
            transaction=transaction,
            notification_type='withdrawal',
            title='Withdrawal Initiated',
            message=f'Your withdrawal request of {amount} {currency} to {bank_name} (•••{masked_account}) is being processed.',
        )

    @staticmethod
    def notify_bill_payment_completed(user, amount, currency, transaction, bill_type, account_reference):
        """
        Notify user that their bill payment has been completed.
        
        Args:
            user: The user who paid the bill
            amount: Decimal amount paid
            currency: Currency code (e.g., 'KHR', 'USD')
            transaction: The Transaction instance
            bill_type: Type of bill (e.g., 'electricity', 'water', 'internet')
            account_reference: Account number for the bill
        """
        Notification.objects.create(
            user=user,
            transaction=transaction,
            notification_type='bill_payment',
            title='Bill Payment Successful',
            message=f'Your {bill_type} bill payment of {amount} {currency} for account {account_reference} was successful.',
        )

    @staticmethod
    def notify_merchant_payment_completed(user, amount, currency, transaction, merchant_name):
        """
        Notify user that their payment to a merchant has been completed.
        
        Args:
            user: The user who made the payment
            amount: Decimal amount paid
            currency: Currency code (e.g., 'KHR', 'USD')
            transaction: The Transaction instance
            merchant_name: Name of the merchant
        """
        Notification.objects.create(
            user=user,
            transaction=transaction,
            notification_type='transfer',
            title='Payment Successful',
            message=f'Your payment of {amount} {currency} to {merchant_name} was successful.',
        )

    # ═══════════════════════════════════════════════════════════
    #  Security Notifications
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def notify_login(user, ip_address=None, device_info=None):
        """
        Notify user of a successful login.
        
        Args:
            user: The user who logged in
            ip_address: IP address of the login
            device_info: Device/browser information
        """
        location_info = f" from IP {ip_address}" if ip_address else ""
        device = f" on {device_info}" if device_info else ""
        
        Notification.objects.create(
            user=user,
            notification_type='security',
            title='New Login Detected',
            message=f'A new login to your account was detected{location_info}{device}. If this was not you, please change your password immediately.',
        )

    @staticmethod
    def notify_password_changed(user):
        """
        Notify user that their password has been changed.
        
        Args:
            user: The user whose password was changed
        """
        Notification.objects.create(
            user=user,
            notification_type='security',
            title='Password Changed',
            message='Your password has been changed successfully. If you did not make this change, please contact support immediately.',
        )

    @staticmethod
    def notify_pin_changed(user):
        """
        Notify user that their PIN has been changed.
        
        Args:
            user: The user whose PIN was changed
        """
        Notification.objects.create(
            user=user,
            notification_type='security',
            title='PIN Changed',
            message='Your wallet PIN has been changed successfully.',
        )

    @staticmethod
    def notify_2fa_enabled(user):
        """
        Notify user that two-factor authentication has been enabled.
        
        Args:
            user: The user who enabled 2FA
        """
        Notification.objects.create(
            user=user,
            notification_type='security',
            title='Two-Factor Authentication Enabled',
            message='Two-factor authentication has been enabled for your account. This adds an extra layer of security.',
        )

    @staticmethod
    def notify_2fa_disabled(user):
        """
        Notify user that two-factor authentication has been disabled.
        
        Args:
            user: The user who disabled 2FA
        """
        Notification.objects.create(
            user=user,
            notification_type='security',
            title='Two-Factor Authentication Disabled',
            message='Two-factor authentication has been disabled for your account. Consider re-enabling it for better security.',
        )

    @staticmethod
    def notify_suspicious_activity(user, activity_type, details=None):
        """
        Notify user of suspicious activity on their account.
        
        Args:
            user: The user whose account had suspicious activity
            activity_type: Type of suspicious activity (e.g., 'multiple_failed_logins', 'large_transfer')
            details: Additional details about the activity
        """
        detail_msg = f" Details: {details}" if details else ""
        Notification.objects.create(
            user=user,
            notification_type='security',
            title='Suspicious Activity Detected',
            message=f'We detected {activity_type} on your account.{detail_msg} Please review your account activity and contact support if you did not authorize this.',
        )

    # ═══════════════════════════════════════════════════════════
    #  Wallet Status Notifications
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def notify_wallet_frozen(user, wallet_number):
        """
        Notify user that their wallet has been frozen.
        
        Args:
            user: The user whose wallet was frozen
            wallet_number: The wallet number that was frozen
        """
        Notification.objects.create(
            user=user,
            notification_type='wallet',
            title='Wallet Frozen',
            message=f'Your wallet {wallet_number} has been frozen. You cannot perform transactions until it is unfrozen. Contact support for assistance.',
        )

    @staticmethod
    def notify_wallet_unfrozen(user, wallet_number):
        """
        Notify user that their wallet has been unfrozen.
        
        Args:
            user: The user whose wallet was unfrozen
            wallet_number: The wallet number that was unfrozen
        """
        Notification.objects.create(
            user=user,
            notification_type='wallet',
            title='Wallet Unfrozen',
            message=f'Your wallet {wallet_number} has been unfrozen. You can now perform transactions normally.',
        )

    @staticmethod
    def notify_wallet_closed(user, wallet_number):
        """
        Notify user that their wallet has been closed.
        
        Args:
            user: The user whose wallet was closed
            wallet_number: The wallet number that was closed
        """
        Notification.objects.create(
            user=user,
            notification_type='wallet',
            title='Wallet Closed',
            message=f'Your wallet {wallet_number} has been closed. This action is irreversible.',
        )

    @staticmethod
    def notify_wallet_created(user, wallet_number, currency):
        """
        Notify user that a new wallet has been created.
        
        Args:
            user: The user who created the wallet
            wallet_number: The new wallet number
            currency: Currency of the wallet
        """
        Notification.objects.create(
            user=user,
            notification_type='wallet',
            title='Wallet Created',
            message=f'Your new {currency} wallet ({wallet_number}) has been created successfully.',
        )

    # ═══════════════════════════════════════════════════════════
    #  KYC/Verification Notifications
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def notify_kyc_verified(user):
        """
        Notify user that their KYC has been verified.
        
        Args:
            user: The user whose KYC was verified
        """
        Notification.objects.create(
            user=user,
            notification_type='kyc',
            title='KYC Verified',
            message='Your identity verification has been approved. You can now send money and use all wallet features.',
        )

    @staticmethod
    def notify_kyc_rejected(user, rejection_reason):
        """
        Notify user that their KYC has been rejected.
        
        Args:
            user: The user whose KYC was rejected
            rejection_reason: The reason for rejection
        """
        Notification.objects.create(
            user=user,
            notification_type='kyc',
            title='KYC Rejected',
            message=f'Your identity verification has been rejected. Reason: {rejection_reason}',
        )

    @staticmethod
    def notify_kyc_submitted(user):
        """
        Notify user that their KYC documents have been submitted.
        
        Args:
            user: The user who submitted KYC
        """
        Notification.objects.create(
            user=user,
            notification_type='kyc',
            title='KYC Submitted',
            message='Your identity verification documents have been submitted and are pending review.',
        )

    # ═══════════════════════════════════════════════════════════
    #  System Notifications
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def notify_transaction_failed(user, transaction_type, amount, currency, reason):
        """
        Notify user that a transaction failed.
        
        Args:
            user: The user whose transaction failed
            transaction_type: Type of transaction (e.g., 'transfer', 'withdrawal')
            amount: Decimal amount
            currency: Currency code
            reason: Reason for failure
        """
        Notification.objects.create(
            user=user,
            notification_type='system',
            title='Transaction Failed',
            message=f'Your {transaction_type} of {amount} {currency} failed. Reason: {reason}',
        )

    @staticmethod
    def notify_low_balance(user, wallet, threshold=Decimal('10000')):
        """
        Notify user that their wallet balance is low.
        
        Args:
            user: The user with low balance
            wallet: The wallet with low balance
            threshold: The threshold below which the notification is triggered
        """
        Notification.objects.create(
            user=user,
            notification_type='system',
            title='Low Balance Alert',
            message=f'Your wallet {wallet.wallet_number} balance is running low ({wallet.balance} {wallet.currency}). Consider topping up.',
        )

    @staticmethod
    def notify_promotional(user, title, message):
        """
        Send a promotional notification to a user.
        
        Args:
            user: The user to notify
            title: Notification title
            message: Notification message
        """
        Notification.objects.create(
            user=user,
            notification_type='system',
            title=title,
            message=message,
        )

    # ═══════════════════════════════════════════════════════════
    #  Utility Methods
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def mark_as_read(notification_id):
        """
        Mark a notification as read.
        
        Args:
            notification_id: ID of the notification to mark as read
            
        Returns:
            bool: True if successful, False if notification not found
        """
        try:
            notification = Notification.objects.get(id=notification_id)
            notification.is_read = True
            notification.save(update_fields=['is_read'])
            return True
        except Notification.DoesNotExist:
            return False

    @staticmethod
    def mark_all_as_read(user):
        """
        Mark all notifications for a user as read.
        
        Args:
            user: The user whose notifications should be marked as read
            
        Returns:
            int: Number of notifications marked as read
        """
        return Notification.objects.filter(user=user, is_read=False).update(is_read=True)

    @staticmethod
    def get_unread_count(user):
        """
        Get the count of unread notifications for a user.
        
        Args:
            user: The user to get the count for
            
        Returns:
            int: Number of unread notifications
        """
        return Notification.objects.filter(user=user, is_read=False).count()

    @staticmethod
    def delete_old_notifications(user, days=30):
        """
        Delete notifications older than a specified number of days.
        
        Args:
            user: The user whose old notifications should be deleted
            days: Number of days after which notifications are deleted
            
        Returns:
            int: Number of notifications deleted
        """
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=days)
        return Notification.objects.filter(user=user, created_at__lt=cutoff_date).delete()[0]
