"""
Context processors for the wallet app.
"""
from .models import Notification


def notification_counts(request):
    """
    Add notification counts by type to the template context.
    """
    if not request.user.is_authenticated:
        return {}

    # Get unread counts by notification type
    unread_notifications = Notification.objects.filter(user=request.user, is_read=False)

    counts = {
        'unread_count': unread_notifications.count(),
        'unread_transfer_count': unread_notifications.filter(notification_type='transfer').count(),
        'unread_bill_payment_count': unread_notifications.filter(notification_type='bill_payment').count(),
        'unread_topup_count': unread_notifications.filter(notification_type='topup').count(),
        'unread_withdrawal_count': unread_notifications.filter(notification_type='withdrawal').count(),
        'unread_security_count': unread_notifications.filter(notification_type='security').count(),
        'unread_kyc_count': unread_notifications.filter(notification_type='kyc').count(),
        'unread_wallet_count': unread_notifications.filter(notification_type='wallet').count(),
        'unread_system_count': unread_notifications.filter(notification_type='system').count(),
    }

    return counts
