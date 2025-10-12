import math
import uuid

import requests
from django.core.files.base import ContentFile


def download_image_from_url(url, upload_to="product_images"):
    """Download image from URL and return a Django File object"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # Extract filename from URL or generate one
        filename = url.split("/")[-1]
        if not filename or "." not in filename:
            filename = f"image_{uuid.uuid4().hex[:8]}.jpg"

        # Create a Django File object
        file_content = ContentFile(response.content)
        return file_content, filename

    except Exception as e:
        print(f"Error downloading image from {url}: {e}")
        return None, None


def safe_value(val, default=None):
    """Convert NaN to None or default value"""
    if isinstance(val, float) and math.isnan(val):
        return default
    return val
