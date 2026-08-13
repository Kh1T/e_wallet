"""
Cloudinary utility functions for image uploads.
"""
import cloudinary.uploader
import cloudinary.api
from cloudinary.utils import cloudinary_url
import logging

logger = logging.getLogger(__name__)


def upload_kyc_image(image_file, folder='kyc', public_id=None):
    """
    Upload an image to Cloudinary for KYC verification.
    
    Args:
        image_file: The image file to upload (can be InMemoryUploadedFile, File, or bytes)
        folder: The folder in Cloudinary to store the image (default: 'kyc')
        public_id: Optional custom public ID for the image
    
    Returns:
        dict: Contains 'url', 'public_id', 'secure_url' on success, or None on failure
    """
    try:
        upload_options = {
            'folder': folder,
            'resource_type': 'image',
            'quality': 'auto:good',  # Automatic quality optimization
            'fetch_format': 'auto',   # Automatic format optimization
        }
        
        if public_id:
            upload_options['public_id'] = public_id
            upload_options['overwrite'] = True
        
        # Upload the image
        result = cloudinary.uploader.upload(image_file, **upload_options)
        
        return {
            'url': result.get('url'),
            'secure_url': result.get('secure_url'),
            'public_id': result.get('public_id'),
            'format': result.get('format'),
            'width': result.get('width'),
            'height': result.get('height'),
            'bytes': result.get('bytes'),
        }
    except Exception as e:
        logger.error(f"Cloudinary upload failed: {str(e)}")
        return None


def upload_kyc_id_document(image_file, user_id):
    """
    Upload ID document to Cloudinary.
    
    Args:
        image_file: The ID document image file
        user_id: The user's ID for organizing the folder structure
    
    Returns:
        dict: Upload result or None on failure
    """
    folder = f'kyc/user_{user_id}/id_documents'
    public_id = f'id_doc_{user_id}'
    return upload_kyc_image(image_file, folder=folder, public_id=public_id)


def upload_kyc_selfie(image_file, user_id):
    """
    Upload selfie image to Cloudinary.
    
    Args:
        image_file: The selfie image file
        user_id: The user's ID for organizing the folder structure
    
    Returns:
        dict: Upload result or None on failure
    """
    folder = f'kyc/user_{user_id}/selfies'
    public_id = f'selfie_{user_id}'
    return upload_kyc_image(image_file, folder=folder, public_id=public_id)


def delete_image(public_id):
    """
    Delete an image from Cloudinary.
    
    Args:
        public_id: The public ID of the image to delete
    
    Returns:
        bool: True if deleted successfully, False otherwise
    """
    try:
        result = cloudinary.uploader.destroy(public_id)
        return result.get('result') == 'ok'
    except Exception as e:
        logger.error(f"Cloudinary delete failed: {str(e)}")
        return False


def get_image_url(public_id, width=None, height=None, crop='fill'):
    """
    Get the URL for a Cloudinary image with optional transformations.
    
    Args:
        public_id: The public ID of the image
        width: Optional width for resizing
        height: Optional height for resizing
        crop: Crop mode (default: 'fill')
    
    Returns:
        str: The transformed image URL
    """
    try:
        options = {'secure': True}
        if width:
            options['width'] = width
        if height:
            options['height'] = height
        if width or height:
            options['crop'] = crop
        
        url, _ = cloudinary_url(public_id, **options)
        return url
    except Exception as e:
        logger.error(f"Cloudinary URL generation failed: {str(e)}")
        return None


def is_cloudinary_url(url):
    """
    Check if a URL is a Cloudinary URL.
    
    Args:
        url: The URL to check
    
    Returns:
        bool: True if it's a Cloudinary URL, False otherwise
    """
    if not url:
        return False
    return 'res.cloudinary.com' in url or 'cloudinary.com' in url
