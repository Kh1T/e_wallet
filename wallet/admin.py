from django.contrib import admin
from django.utils import timezone

from .models import IdentityVerification, Notification


def approve_kyc(modeladmin, request, queryset):
    updated = 0
    for verification in queryset:
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
            updated += 1
    modeladmin.message_user(request, f'{updated} KYC submission(s) approved.')


approve_kyc.short_description = 'Approve selected KYC submissions'


def reject_kyc(modeladmin, request, queryset):
    """This action will prompt for rejection reason individually."""
    updated = 0
    for verification in queryset:
        if verification.verification_status != 'rejected':
            verification.verification_status = 'rejected'
            verification.verified_at = None
            # Note: In bulk reject, reason will be empty. Use individual change form to add reason.
            verification.save(update_fields=['verification_status', 'verified_at'])
            Notification.objects.create(
                user=verification.user,
                title='KYC Rejected',
                message='Your identity verification has been rejected. Please check the rejection reason and resubmit valid documents.',
            )
            updated += 1
    modeladmin.message_user(request, f'{updated} KYC submission(s) rejected. Note: Add rejection reasons individually for better user feedback.')


reject_kyc.short_description = 'Reject selected KYC submissions (bulk)'


@admin.register(IdentityVerification)
class IdentityVerificationAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'national_id', 'verification_status', 'created_at', 'verified_at'
    )
    list_filter = ('verification_status', 'created_at', 'verified_at')
    search_fields = ('user__email', 'user__full_name', 'national_id')
    actions = (approve_kyc, reject_kyc)
    readonly_fields = ('created_at', 'verified_at')
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'national_id', 'date_of_birth', 'address', 'nationality')
        }),
        ('Documents', {
            'fields': ('id_document', 'selfie_image'),
            'description': 'Uploaded ID document and selfie for verification'
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
