"""
Email utility module using Resend API for sending emails.
"""
import resend
import secrets
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def get_resend_client():
    """Initialize Resend with API key."""
    api_key = getattr(settings, 'RESEND_API_KEY', None)
    if not api_key:
        raise ImproperlyConfigured("RESEND_API_KEY must be set in settings")
    resend.api_key = api_key
    return resend


def generate_reset_token(length=32):
    """Generate a secure password reset token."""
    return secrets.token_urlsafe(length)


def send_email(to_email, subject, html_content, text_content=None):
    """
    Send an email using Resend API.

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email body
        text_content: Plain text email body (optional)

    Returns:
        dict: Response from Resend API
    """
    try:
        r = get_resend_client()
    except ImproperlyConfigured as e:
        return {"success": False, "error": f"Configuration error: {str(e)}"}

    from_email = getattr(settings, 'RESEND_FROM_EMAIL', 'onboarding@resend.dev')

    # Validate from email
    if not from_email:
        return {"success": False, "error": "RESEND_FROM_EMAIL not configured. Please set a from email address."}

    params = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "html": html_content,
    }

    if text_content:
        params["text"] = text_content

    try:
        response = r.Emails.send(params)
        return {"success": True, "data": response}
    except Exception as e:
        error_msg = str(e)
        # Check for common Resend errors
        if "401" in error_msg or "Unauthorized" in error_msg:
            return {"success": False, "error": "Invalid Resend API key. Please check your RESEND_API_KEY setting."}
        elif "403" in error_msg or "not verified" in error_msg.lower():
            return {"success": False, "error": "Sender email not verified with Resend. Please verify your domain or use onboarding@resend.dev for testing."}
        elif "400" in error_msg:
            return {"success": False, "error": f"Bad request: {error_msg}"}
        else:
            return {"success": False, "error": f"Email sending failed: {error_msg}"}


def send_password_reset_email(user, reset_url):
    """
    Send password reset email to user.

    Args:
        user: User instance
        reset_url: Full URL to reset password
    """
    subject = "Password Reset Request"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px; }}
            .container {{ max-width: 500px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
            .header {{ text-align: center; color: #333; margin-bottom: 30px; }}
            .button {{ display: inline-block; background: #dc3545; color: white;
                      padding: 15px 30px; text-decoration: none; border-radius: 5px;
                      margin: 20px 0; }}
            .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
            .warning {{ background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .link {{ color: #007bff; word-break: break-all; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Password Reset</h1>
                <p>Hello {user.full_name or user.email},</p>
                <p>You requested a password reset. Click the button below to set a new password:</p>
            </div>
            <div style="text-align: center;">
                <a href="{reset_url}" class="button">Reset Password</a>
            </div>
            <p style="text-align: center;">Or copy and paste this link:</p>
            <p class="link" style="text-align: center;">{reset_url}</p>
            <div class="warning">
                <strong>Security Notice:</strong> If you didn't request this reset, please ignore this email.
                Your account remains secure.
            </div>
            <div class="footer">
                <p>This link will expire in 1 hour.</p>
                <p>&copy; E-Wallet App</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_content = f"""
    Password Reset
    
    Hello {user.full_name or user.email},
    
    You requested a password reset. Visit the following link to set a new password:
    
    {reset_url}
    
    This link will expire in 1 hour.
    
    If you didn't request this reset, please ignore this email. Your account remains secure.
    
    E-Wallet App
    """

    return send_email(user.email, subject, html_content, text_content)


def send_password_reset_confirmation(user):
    """
    Send password reset confirmation email.

    Args:
        user: User instance
    """
    subject = "Password Reset Successful"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px; }}
            .container {{ max-width: 500px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
            .header {{ text-align: center; color: #333; margin-bottom: 30px; }}
            .success {{ color: #28a745; font-size: 18px; text-align: center; margin: 20px 0; }}
            .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Password Reset Successful</h1>
                <p>Hello {user.full_name or user.email},</p>
            </div>
            <div class="success">
                <p>Your password has been successfully reset.</p>
                <p>If you did not perform this action, please contact support immediately.</p>
            </div>
            <div class="footer">
                <p>&copy; E-Wallet App</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_content = f"""
    Password Reset Successful
    
    Hello {user.full_name or user.email},
    
    Your password has been successfully reset.
    
    If you did not perform this action, please contact support immediately.
    
    E-Wallet App
    """

    return send_email(user.email, subject, html_content, text_content)
