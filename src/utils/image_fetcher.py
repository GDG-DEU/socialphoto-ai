import logging
from io import BytesIO
from PIL import Image
import httpx
import cloudinary
import cloudinary.utils

from src.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
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
    