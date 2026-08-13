"""
QR Code utilities for wallet transfers.
"""
import qrcode
import qrcode.image.svg
import json
import base64
from io import BytesIO
from decimal import Decimal


def generate_wallet_qr_data(wallet_number, amount=None, currency='KHR', description=''):
    """
    Generate QR code data for wallet transfer.
    
    Format: JSON with wallet info
    {
        "type": "wallet_transfer",
        "wallet_number": "W12345678",
        "amount": "1000.00",  # Optional
        "currency": "KHR",
        "description": "Payment for..."  # Optional
    }
    """
    data = {
        'type': 'wallet_transfer',
        'wallet_number': wallet_number,
        'currency': currency,
    }
    if amount is not None:
        data['amount'] = str(Decimal(str(amount)))
    if description:
        data['description'] = description
    
    return json.dumps(data, separators=(',', ':'))


def parse_wallet_qr_data(qr_data):
    """
    Parse QR code data and return wallet transfer info.
    Supports multiple formats:
    - wallet_transfer: {"type": "wallet_transfer", "wallet_number": "...", ...}
    - NEXUSPAY_RECEIVE: {"type": "NEXUSPAY_RECEIVE", "wallet": "...", ...}
    - Plain wallet number: "W12345678"
    
    Returns:
        dict: Parsed data or None if invalid
    """
    try:
        data = json.loads(qr_data)
        qr_type = data.get('type')
        
        # Format 1: wallet_transfer (send money form)
        if qr_type == 'wallet_transfer':
            return {
                'wallet_number': data.get('wallet_number'),
                'amount': Decimal(data.get('amount', '0')) if data.get('amount') else None,
                'currency': data.get('currency', 'KHR'),
                'description': data.get('description', ''),
            }
        
        # Format 2: NEXUSPAY_RECEIVE (receive QR popup)
        if qr_type == 'NEXUSPAY_RECEIVE':
            return {
                'wallet_number': data.get('wallet'),
                'amount': Decimal(data.get('amount', '0')) if data.get('amount') else None,
                'currency': data.get('currency', 'KHR'),
                'description': f"Payment to {data.get('receiver', '')}",
            }
        
        # Unknown type
        return None
        
    except (json.JSONDecodeError, ValueError):
        # Try parsing as plain wallet number (fallback)
        qr_data = qr_data.strip()
        if qr_data.startswith('W') and len(qr_data) >= 8:
            return {
                'wallet_number': qr_data,
                'amount': None,
                'currency': 'KHR',
                'description': '',
            }
        return None


def generate_qr_image(qr_data, size=10, border=2):
    """
    Generate QR code image as base64 data URL.
    
    Args:
        qr_data: The data to encode in the QR code
        size: Box size for each module
        border: Border width in modules
    
    Returns:
        str: Base64 encoded PNG data URL
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=size,
        border=border,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_base64}"


def generate_qr_svg(qr_data, size=10, border=2):
    """
    Generate QR code as SVG string.
    
    Args:
        qr_data: The data to encode in the QR code
        size: Box size for each module
        border: Border width in modules
    
    Returns:
        str: SVG XML string
    """
    factory = qrcode.image.svg.SvgImage
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=size,
        border=border,
        image_factory=factory,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    img = qr.make_image()
    buffer = BytesIO()
    img.save(buffer)
    buffer.seek(0)
    
    return buffer.getvalue().decode()
