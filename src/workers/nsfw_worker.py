import json
import asyncio
import logging
import signal
from redis.asyncio import ConnectionError
from src.services.redis_client import redis_client
from src.services.notification_service import notification_service
from src.services.nsfw_service import NSFWService

nsfw_service = NSFWService()

NSFW_JOB_PREFIX = "nsfw_job:"
shutdown_event = asyncio.Event()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def signal_handler(sig, frame):
    logger.info(f"Received signal {sig}, shutting down gracefully...")
    shutdown_event.set()

async def run_worker():
    logger.info("NSFW Analyze worker started, waiting for jobs in 'analyze_queue'...")
    retry_delay = 1
    max_retry_delay = 30

    while not shutdown_event.is_set():
        try:
            result = await redis_client.blpop("analyze_queue", timeout=1)
            if result is None:
                continue

            _, job_id = result
            retry_delay = 1
            job_key = f"{NSFW_JOB_PREFIX}{job_id}"

            await redis_client.hset(job_key, "status", "processing")

            try:
                image_path = await redis_client.hget(job_key, "file_path")

                if not image_path:
                    raise Exception(f"Job {job_id} için file_path bulunamadı!")

                # --- AI ANALİZİ ---
                logger.info(f"Processing Job {job_id}: Analyzing file {image_path}")

                with open(image_path, "rb") as f:
                    image_bytes = f.read()

                analysis_result = nsfw_service.predict(image_bytes)
                nsfw_score = analysis_result.get("nsfw", 0)

                # 1. Redis durumunu güncelle
                await redis_client.hset(
                    job_key,
                    mapping={
                        "status": "completed",
                        "nsfw_score": str(round(nsfw_score, 4))
                    }
                )

                # 2. Backend'e bildirimi gönder
                await notification_service.notify_job_completion({
                    "job_id": job_id,
                    "status": "completed",
                    "nsfw_score": nsfw_score,
                    "file_path": image_path
                })

                # 3. Temizlik ve Log
                await redis_client.expire(job_key, 1800)
                logger.info(f"Job {job_id} successfully analyzed. Score: {nsfw_score:.4f}")

            except Exception as e:
                logger.error(f"Error processing job {job_id}: {str(e)}", exc_info=True)
                await redis_client.hset(
                    job_key,
                    mapping={
                        "status": "failed",
                        "error": str(e)
                    }
                )
                await redis_client.expire(job_key, 1800)

                await notification_service.notify_job_completion({
                    "job_id": job_id,
                    "status": "failed",
                    "error": str(e)
                })

        except ConnectionError as e:
            logger.error(f"Redis connection error: {e}. Retrying in {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_retry_delay)

        except Exception as e:
            logger.error(f"Unexpected error in worker: {str(e)}", exc_info=True)
            await asyncio.sleep(5)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        asyncio.run(run_worker())
    finally:
        logger.info("Worker shutdown complete")