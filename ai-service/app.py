from fastapi import FastAPI, HTTPException
from schemas import AnalyzeRequest, AnalyzeJobResponse, AnalyzeJobStatusResponse
from redis_client import redis_client
from src.services.notification_service import notification_service
import json
import logging
import uuid
from contextlib import asynccontextmanager


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Test Redis connection
    try:
        await redis_client.ping()
        logger.info("Redis connected successfully")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise
    
    yield
    
    # Shutdown: Close Redis connection
    await redis_client.close()
    logger.info("Redis connection closed")

app = FastAPI(title="AI Service", version="1.0.0", lifespan=lifespan)

# Combine FastAPI and Socket.IO into one ASGI app
combined_app = notification_service.get_asgi_app(app)


# This endpoint has been implemented for manual testing purposes. Originally, jobs are enqueued by backend service.
@app.post("/analyze", response_model=AnalyzeJobResponse, status_code=202)
async def analyze_image(req: AnalyzeRequest):
    try:
        job_id = str(uuid.uuid4())
        job_key = f"analyze_job:{job_id}"

        # job metadata
        await redis_client.hset(
            job_key,
            mapping={
                "job_id": job_id,
                "post_id": req.post_id,
                "image_url": str(req.image_url),
                "status": "queued"
            }
        )
        await redis_client.expire(job_key, 86400)  # 24 saatlik TTL

        # enqueue job to analyze_queue list
        await redis_client.rpush("analyze_queue", job_id)

        return {"job_id": job_id, "status": "queued"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analyze/{job_id}", response_model=AnalyzeJobStatusResponse)
async def get_analyze_job_status(job_id: str):
    job_key = f"analyze_job:{job_id}"
    job_data = await redis_client.hgetall(job_key)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")

    status = job_data.get("status", "queued")
    error = job_data.get("error")
    result = None
    if status == "completed":
        score = job_data.get("aesthetic_score")
        tags = job_data.get("suggested_tags")
        result = {
            "aesthetic_score": float(score) if score else None,
            "suggested_tags": json.loads(tags) if tags else []
        }
    return {
        "job_id": job_id,
        "status": status,
        "result": result,
        "error": error
    }