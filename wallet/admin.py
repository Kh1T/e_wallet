from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.conf import settings

from .models import IdentityVerification, Notification


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
