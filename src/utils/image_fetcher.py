import logging
import os
from io import BytesIO
from PIL import Image
import httpx
import cloudinary
import cloudinary.utils

logger = logging.getLogger(__name__)

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)

async def fetch_cloudinary_image(public_id: str, transformations: dict = None) -> Image.Image:
    """Fetches a private Cloudinary image by its public_id.

    Generates a time-limited signed URL via the Cloudinary SDK, then downloads
    the image over HTTPS.  Requires the following env vars to be set:
        CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET
    """
    try:
        signed_url, options = cloudinary.utils.cloudinary_url(
            public_id,
            resource_type="image",
            type="upload",
            sign_url=True,
            **(transformations or {})
        )
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(signed_url)
            response.raise_for_status()
            return Image.open(BytesIO(response.content))
        
    except Exception as e:
        logger.error(f"Error fetching Cloudinary image: {e}")
        raise

async def fetch_image_from_url(url: str) -> Image.Image:
    """Fetches an image from a public URL over HTTPS."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            response.raise_for_status()
            return Image.open(BytesIO(response.content))
    except Exception as e:
        logger.error(f"Error fetching image from URL {url}: {e}")
        raise
    