import json
import asyncio
import logging
import signal
from redis.asyncio import ConnectionError
from src.services.redis_client import redis_client
from src.services.notification_service import notification_service


JOB_PREFIX = "analyze_job:"
shutdown_event = asyncio.Event()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def signal_handler(sig, frame):
    logger.info(f"Received signal {sig}, shutting down gracefully...")
    shutdown_event.set()


async def run_worker():
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
                webhook_url = await redis_client.hget(job_key, "webhook_url")

                # --- FAKE AI WORK ---
                logger.info("--- FAKE AI WORK ---")
                logger.info(f"Processing job: {job_id}")
                await asyncio.sleep(3)
                score = 8.42
                tags = ["sunset", "beach", "warm colors"]

                await redis_client.hset(
                    job_key,
                    mapping={
                        "status": "completed",
                        "aesthetic_score": score,
                        "suggested_tags": json.dumps(tags)
                    }
                )
                #BACKENDE MUTLAKA BU FORMATTA NOTİF LOADI ATTIĞINIZDAN EMİN OLUN.
                notification_payload = {
                    "post_id": job_id,
                    "status": "completed",
                    "result": {
                        "aesthetic_score": score,
                        "suggested_tags": tags
                    }
                }
                     
                if webhook_url:
                     notification_payload["webhook_url"] = webhook_url

                logger.info(f"Sending webhook payload: {json.dumps(notification_payload)}")
                await notification_service.notify_job_completion(notification_payload)

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