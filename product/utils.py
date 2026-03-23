import io
import math
import uuid
import zipfile

import requests
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile


def extract_images_from_zip(zip_file):
    """
    Extract images from a ZIP file and return a dictionary mapping filenames to file objects.
    """
    images = {}
    if not zip_file:
        return images

    try:
        with zipfile.ZipFile(zip_file) as z:
            for filename in z.namelist():
                # Skip directories
                if filename.endswith("/") or "__MACOSX" in filename:
                    continue

                # Get the actual filename without path
                name = filename.split("/")[-1]
                if not name:
                    continue

                # Read file content
                file_content = z.read(filename)

                # Create an InMemoryUploadedFile
                image_io = io.BytesIO(file_content)
                file_size = len(file_content)

                # Determine content type (basic check)
                content_type = "image/jpeg"
                if name.lower().endswith(".png"):
                    content_type = "image/png"
                elif name.lower().endswith(".webp"):
                    content_type = "image/webp"
                elif name.lower().endswith(".gif"):
                    content_type = "image/gif"

                uploaded_file = InMemoryUploadedFile(
                    image_io, None, name, content_type, file_size, None
                )
                images[name] = uploaded_file
    except Exception as e:
        print(f"Error extracting ZIP: {e}")

    return images


def process_image_field(image_name, images_from_zip):
    """
    Check if image_name exists in images_from_zip and return the file object.
    """
    if not image_name or not isinstance(image_name, str):
        return None

    # Clean image name (strip path if any)
    clean_name = image_name.split("/")[-1].split("\\")[-1].strip()

    return images_from_zip.get(clean_name)


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
