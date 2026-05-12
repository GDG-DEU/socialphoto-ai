import os
import json
import asyncio
import logging
import signal
from urllib.parse import urlparse
from redis.asyncio import ConnectionError
from src.config import get_settings
from src.services.redis_client import redis_client
from src.services.notification_service import notification_service
from src.services.analyze_service import AnalyzeService
from src.services.providers.gemini_provider import GeminiProvider
from src.services.providers.openai_provider import OpenAIProvider


JOB_PREFIX = "analyze_job:"
shutdown_event = asyncio.Event()

log_level_str = get_settings().log_level.upper()
log_level = getattr(logging, log_level_str, logging.INFO)
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Suppress noisy HTTP libraries when in DEBUG mode
if logging.getLogger().getEffectiveLevel() == logging.DEBUG:
    for logger_name in ["httpx", "httpcore", "openai", "urllib3"]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def _get_webhook_host(webhook_url: str | None) -> str | None:
    if not webhook_url:
        return None

    parsed_url = urlparse(webhook_url)
    return parsed_url.netloc or None


def signal_handler(sig, frame):
    logger.info(f"Received signal {sig}, shutting down gracefully...")
    shutdown_event.set()


async def run_worker():
    gemini_provider = GeminiProvider() # MAIN PROVIDER
    openai_provider = OpenAIProvider() # FALLBACK PROVIDER
    analyze_service = AnalyzeService(providers=[gemini_provider, openai_provider]) #priority sequence

    logger.info("Analyze worker started, waiting for jobs...")
    retry_delay = 1
    max_retry_delay = 30

    while not shutdown_event.is_set():
        try:
            result = await redis_client.blpop("analyze_queue", timeout=1)
            if result is None:
                continue
            _, job_id = result

            retry_delay = 1  # Reset retry delay on successful connection
            job_key = f"{JOB_PREFIX}{job_id}"

            await redis_client.hset(job_key, "status", "processing")

            try:
                cloudinary_public_id = await redis_client.hget(job_key, "cloudinary_public_id")
                post_id = await redis_client.hget(job_key, "post_id")
                webhook_url = await redis_client.hget(job_key, "webhook_url")
                language = await redis_client.hget(job_key, "language") or "en"

                if not cloudinary_public_id:
                    raise ValueError(f"Job {job_id}: cloudinary_public_id not found in Redis")

                # --- AI ANALYSIS ---
                logger.info(f"Processing job {job_id}: analyzing image '{cloudinary_public_id}'")

                result = await analyze_service.analyze(str(cloudinary_public_id), language=language)

                await redis_client.hset(
                    job_key,
                    mapping={
                        "status": "completed",
                        "result_json": json.dumps(result)
                    }
                )

                # BACKENDE MUTLAKA BU FORMATTA NOTİF LOADI ATTIĞINIZDAN EMİN OLUN.
                notification_payload = {
                    "post_id": post_id,
                    "status": "completed",
                    "result": result
                }

                if webhook_url:
                     notification_payload["webhook_url"] = webhook_url

                webhook_host = _get_webhook_host(webhook_url)
                logger.info(
                    "Sending job completion notification",
                    extra={
                        "job_id": job_id,
                        "status": "completed",
                        "webhook_host": webhook_host,
                    },
                )
                await notification_service.notify_job_completion(notification_payload)

                logger.info(f"Job {job_id} completed successfully.")

                await redis_client.expire(job_key, 1800) # 30 dakika

            except Exception as e:
                logger.error(f"Error processing job {job_id}: {str(e)}", exc_info=True)
                await redis_client.hset(
                    job_key,
                    mapping={
                        "status": "failed",
                        "error": str(e)
                    }
                )
                await redis_client.expire(job_key, 1800) # 30 dakika

                failure_payload = {
                    "post_id": job_id,
                    "status": "failed",
                    "error": str(e)
                }

                if 'webhook_url' in locals() and webhook_url:
                     failure_payload["webhook_url"] = webhook_url

                webhook_host = _get_webhook_host(webhook_url if 'webhook_url' in locals() else None)
                logger.info(
                    "Sending job failure notification",
                    extra={
                        "job_id": job_id,
                        "status": "failed",
                        "webhook_host": webhook_host,
                    },
                )
                await notification_service.notify_job_completion(failure_payload)

        except ConnectionError as e:
            # Redis connection lost - retry with exponential backoff
            logger.error(f"Redis connection error: {e}. Retrying in {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay *2, max_retry_delay)

        except Exception as e:
            logger.error(f"Unexpected error in worker: {str(e)}", exc_info=True)
            await asyncio.sleep(5)

if __name__ == "__main__":
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        asyncio.run(run_worker())
    finally:
        logger.info("Worker shutdown complete")