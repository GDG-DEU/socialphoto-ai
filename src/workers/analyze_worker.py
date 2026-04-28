import json
import asyncio
import logging
import signal
from redis.asyncio import ConnectionError
from src.services.redis_client import redis_client
from src.services.notification_service import notification_service
import httpx
import os


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
                temp_image_url = await redis_client.hget(job_key, "temp_image_url")
                theme_title = await redis_client.hget(job_key, "theme_title") or "Genel Tema"

                if not temp_image_url:
                    raise Exception(f"Job {job_id} için temp_image_url bulunamadı!")

                # --- AI WORK (Topic Match & Aesthetic Analysis) ---
                logger.info(f"Processing Topic Match & Analysis for Job {job_id}")
                logger.info(f"Vision Prompt: 'Bu fotoğraf {theme_title} ile ilgili mi?'")
                
                await asyncio.sleep(2) # Simulate Vision AI processing time
                
                # TODO: Integrate real Vision LLM (e.g. OpenAI GPT-4o or LLaVA)
                # For now, we simulate a successful match.
                topic_match = True 
                
                score = 8.42
                tags = ["sunset", "beach", "warm colors", theme_title]

                result_data = {
                    "topic_match": topic_match,
                    "aesthetic_score": score,
                    "suggested_tags": tags
                }

                await redis_client.hset(
                    job_key,
                    mapping={
                        "status": "completed",
                        "aesthetic_score": score,
                        "suggested_tags": json.dumps(tags),
                        "topic_match": int(topic_match)
                    }
                )

                payload = {
                    "job_id": job_id,
                    "post_id": job_id,
                    "status": "completed",
                    "result": result_data
                }

                webhook_url = await redis_client.hget(job_key, "webhook_url")
                if webhook_url:
                    api_key = os.getenv("X-API-Key", "tpCPZBaFflXj-LnzUO3kXwuWmlvN6kfTLJjgCz1yvX4")
                    try:
                        async with httpx.AsyncClient() as client:
                            await client.post(
                                str(webhook_url), 
                                json=payload, 
                                headers={"x-api-key": api_key, "Content-Type": "application/json"}
                            )
                        logger.info(f"Webhook sent to {webhook_url} for job {job_id}")
                    except Exception as e:
                        logger.error(f"Failed to send webhook: {e}")

                await notification_service.notify_job_completion(payload)

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

                payload = {
                    "job_id": job_id,
                    "post_id": job_id,
                    "status": "failed",
                    "error": str(e)
                }

                webhook_url = await redis_client.hget(job_key, "webhook_url")
                if webhook_url:
                    api_key = os.getenv("X-API-Key", "tpCPZBaFflXj-LnzUO3kXwuWmlvN6kfTLJjgCz1yvX4")
                    try:
                        async with httpx.AsyncClient() as client:
                            await client.post(
                                str(webhook_url), 
                                json=payload, 
                                headers={"x-api-key": api_key, "Content-Type": "application/json"}
                            )
                    except Exception as webhook_err:
                        logger.error(f"Failed to send webhook: {webhook_err}")

                await notification_service.notify_job_completion(payload)

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